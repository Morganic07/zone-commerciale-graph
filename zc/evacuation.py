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
from zc.navigation import graphe_du_centre
from zc.simulation import DANS_NOEUD, PARTI, SAUVE, Agent, Simulation


class Evacuation:
    """Fait avancer ensemble l'incendie, l'évacuation et la simulation."""

    def __init__(self, sim: Simulation, centre: CentreZone, incendie: Incendie) -> None:
        self.sim = sim
        self.centre = centre
        self.incendie = incendie
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
        for n in self.centre.centre.noeuds:
            if n.statut == "enfumé" or n.statut == "bloqué":
                return True
        return False

    def guider(self) -> None:
        """Chaque agent présent dans un nœud du centre reçoit le chemin vers la sortie
        ouverte la plus proche ; sans chemin, il est piégé."""
        valides = graphe_du_centre(self.centre.centre, "court")
        pmr = graphe_du_centre(self.centre.centre, "pmr")
        distances_valides, suivants_valides = distances_d_evacuation(valides, self.sorties)
        distances_pmr, suivants_pmr = distances_d_evacuation(pmr, self.sorties)
        for agent in self.sim.agents:
            if agent.etat != DANS_NOEUD or not self.dans_le_centre(agent):
                continue
            distances, suivants = distances_valides, suivants_valides
            if agent.pmr:
                distances, suivants = distances_pmr, suivants_pmr
            if agent.position not in distances:
                self.pieges.add(agent.id)  # plus aucun chemin vers une sortie ouverte
                agent.itineraire = []
                continue
            self.pieges.discard(agent.id)
            chemin = chemin_d_evacuation(suivants, self.sorties, agent.position)
            agent.itineraire = chemin[1:]

    def sauver_aux_sorties(self) -> None:
        """Les agents arrivés dans une sortie non bloquée sont sauvés."""
        for agent in self.sim.agents:
            if agent.etat != DANS_NOEUD or agent.position not in self.charge:
                continue
            if self.sim.noeuds[agent.position].statut == "bloqué":
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
