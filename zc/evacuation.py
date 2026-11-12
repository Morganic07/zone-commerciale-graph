"""Évacuation d'un centre en feu (PLAN.md § 5.4).

À chaque pas : l'incendie avance (fumée et détection), puis, une fois l'alarme donnée,
chaque personne présente dans un nœud du centre se dirige vers la sortie la plus proche.
Les chemins sont recalculés à chaque pas, sur le graphe des statuts connus (un nœud ou un
couloir connu comme bloqué n'y figure plus), avec le critère « pmr » pour les PMR.

- L'alarme est donnée à la première détection (un nœud connu comme enfumé ou bloqué).
- Un agent qui atteint une sortie non bloquée est sauvé : il quitte la simulation.
- Un agent dans un nœud sans aucun chemin vers une sortie ouverte est piégé.
- L'incendie est limité au centre : on ne fait pas entrer de nouveaux visiteurs.

Choix de modèle, à discuter dans le rapport : un nœud connu comme bloqué est retiré du
graphe avec tous ses couloirs (consigne § 3.4). Une personne qui s'y trouve quand il se
bloque n'a donc plus de chemin : elle est piégée. Dans le scénario de test, c'est le cas
de tous les piégés. Une alternative serait de laisser sortir les occupants d'un nœud
bloqué par un couloir vers un nœud non bloqué ; elle réduirait le nombre de piégés.

Indicateurs : temps d'évacuation, courbe des personnes encore dans le centre, nombre de
sauvés et de piégés, charge de chaque sortie.
"""

from zc.chemins import chemin_d_evacuation, distances_d_evacuation
from zc.incendie import Incendie
from zc.modele import CentreZone
from zc.navigation import Arc, construire
from zc.simulation import DANS_NOEUD, PARTI, SAUVE, Agent, Simulation

MODES = ["local", "global"]


class Evacuation:
    """Fait avancer ensemble l'incendie, l'évacuation et la simulation.

    Ce que savent les occupants (`connaissance`, PLAN.md § 5.3) :
    - « local » : ils évacuent à l'alarme et suivent les statuts qu'elle a détectés
      (capteurs, retard δ sans capteur), plus ce qu'ils voient autour d'eux : un voisin
      dont la fumée réelle dépasse θ₂ est évité, même si l'alarme l'ignore encore ;
    - « global » : ils connaissent l'état réel de tout le bâtiment ; ils évacuent dès que
      la fumée réelle franchit θ₁ quelque part, et évitent tout nœud réellement bloqué.
    """

    def __init__(self, sim: Simulation, centre: CentreZone, incendie: Incendie,
                 connaissance: str = "local") -> None:
        if connaissance not in MODES:
            raise ValueError(f"connaissance « {connaissance} » inconnue, attendu parmi {MODES}")
        self.sim = sim
        self.centre = centre
        self.incendie = incendie
        self.connaissance = connaissance
        self.noeuds_du_centre = set()
        self.sorties = []
        for n in centre.centre.noeuds:
            self.noeuds_du_centre.add(n.id)
            if n.type == "sortie":
                self.sorties.append(n.id)
        self.alarme: float | None = None  # instant de l'alarme
        self.presents_au_declenchement: list[int] = []
        self.charge: dict[str, int] = {}
        for s in self.sorties:
            self.charge[s] = 0
        self.courbe: list[tuple[float, int]] = []  # (instant, personnes dans le centre)
        self.pieges: set[int] = set()

    def dans_le_centre(self, agent: Agent) -> bool:
        """L'agent est-il dans le centre (dans un nœud, ou sur un couloir du centre) ?"""
        if agent.etat == PARTI or agent.etat == SAUVE:
            return False
        if agent.position not in self.noeuds_du_centre:
            return False
        if agent.arete is not None:
            a = self.sim.aretes[agent.arete]
            # Sur une connexion de la zone (vers l'extérieur), il est déjà sorti.
            if a.source not in self.noeuds_du_centre or a.cible not in self.noeuds_du_centre:
                return False
        return True

    def pas(self) -> None:
        """Un pas : incendie, alarme, consignes d'évacuation, puis déplacements."""
        self.incendie.pas()
        if self.alarme is None and self.detection_en_cours():
            self.alarme = self.sim.temps
            for agent in self.sim.agents:
                if self.dans_le_centre(agent):
                    self.presents_au_declenchement.append(agent.id)
        if self.alarme is not None:
            self.guider()
        self.sim.pas()
        if self.alarme is not None:
            self.sauver_aux_sorties()
            restants = 0
            for agent in self.sim.agents:
                if self.dans_le_centre(agent):
                    restants += 1
            self.courbe.append((self.sim.temps, restants))

    def detection_en_cours(self) -> bool:
        """Le feu est-il connu des occupants ? En mode « local », quand l'alarme a détecté
        un nœud (avec le retard δ des nœuds sans capteur) ; en mode « global », dès que la
        fumée réelle franchit θ₁ quelque part."""
        for n in self.centre.centre.noeuds:
            if n.statut == "enfumé" or n.statut == "bloqué":
                return True
            if self.connaissance == "global" and n.niveau_fumee >= self.incendie.theta1:
                return True
        return False

    def reellement_bloque(self, noeud: str) -> bool:
        """La fumée réelle du nœud dépasse-t-elle θ₂ ?"""
        return self.sim.noeuds[noeud].niveau_fumee >= self.incendie.theta2

    def graphe(self, critere: str, bloques_en_plus: set[str]) -> dict[str, list[Arc]]:
        """Graphe de navigation du centre : sans les nœuds connus comme bloqués, ni ceux
        de `bloques_en_plus` (ceux que l'on sait bloqués autrement que par l'alarme)."""
        identifiants = []
        bloques = set(bloques_en_plus)
        for n in self.centre.centre.noeuds:
            identifiants.append(n.id)
            if n.statut == "bloqué":
                bloques.add(n.id)
        return construire(identifiants, self.centre.centre.aretes, bloques, critere)

    def guider(self) -> None:
        """Chaque agent présent dans un nœud du centre reçoit le chemin vers la sortie
        ouverte la plus proche, selon ce qu'il sait ; sans chemin, il est piégé."""
        connus = set()
        if self.connaissance == "global":
            for n in self.centre.centre.noeuds:
                if self.reellement_bloque(n.id):
                    connus.add(n.id)
        for agent in self.sim.agents:
            if agent.etat != DANS_NOEUD or not self.dans_le_centre(agent):
                continue
            bloques = set(connus)
            if self.connaissance == "local":
                # Ce qu'il voit : les voisins réellement bloqués.
                for voisin in self.incendie.voisins[agent.position]:
                    if self.reellement_bloque(voisin):
                        bloques.add(voisin)
            critere = "pmr" if agent.pmr else "court"
            distances, suivants = distances_d_evacuation(self.graphe(critere, bloques),
                                                         self.sorties)
            if agent.position not in distances:
                self.pieges.add(agent.id)  # plus aucun chemin vers une sortie ouverte
                agent.itineraire = []
                continue
            self.pieges.discard(agent.id)
            chemin = chemin_d_evacuation(suivants, self.sorties, agent.position)
            agent.itineraire = chemin[1:]

    def sauver_aux_sorties(self) -> None:
        """Les agents arrivés dans une sortie ouverte sont sauvés. Une sortie réellement
        bloquée (ou connue comme telle) ne sauve personne, que l'alarme le sache ou non."""
        for agent in self.sim.agents:
            if agent.etat != DANS_NOEUD or agent.position not in self.charge:
                continue
            if self.sim.noeuds[agent.position].statut == "bloqué":
                continue
            if self.reellement_bloque(agent.position):
                continue
            self.charge[agent.position] += 1
            self.sim.sauver(agent)

    # --- bilan ---------------------------------------------------------------------------

    def sauves(self) -> int:
        total = 0
        for agent_id in self.presents_au_declenchement:
            if self.sim.agents[agent_id].etat == SAUVE:
                total += 1
        return total

    def termine(self) -> bool:
        """Évacuation finie : chaque présent à l'alarme est sauvé ou piégé."""
        if self.alarme is None:
            return False
        for agent_id in self.presents_au_declenchement:
            if self.sim.agents[agent_id].etat != SAUVE and agent_id not in self.pieges:
                return False
        return True

    def temps_d_evacuation(self) -> float | None:
        """Durée entre l'alarme et la fin de l'évacuation, ou None si elle n'est pas finie."""
        if self.alarme is None or not self.termine():
            return None
        return self.sim.temps - self.alarme
