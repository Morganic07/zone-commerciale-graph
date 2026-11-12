"""Demande : arrivée des visiteurs et déroulement de leur visite (PLAN.md § 4.2).

Un visiteur arrive par une source (parking, station, quartier), choisit un centre puis
1 à 3 de ses magasins, reste dans chacun un temps tiré au hasard, puis revient à sa
source et repart. Une part réglable des visiteurs est PMR : leurs trajets n'empruntent
que des arêtes praticables en fauteuil.

Les trajets sont calculés par Dijkstra (`zc/chemins.py`) : critère « moins encombré »
pour les visiteurs valides, « pmr » pour les autres. Un trajet est recalculé quand la
destination change (magasin suivant, retour) ou quand il n'est plus praticable (un nœud
ou une arête est devenu bloqué). Tout le hasard passe par le générateur de la
simulation : même graine, même journée.
"""

from dataclasses import dataclass

from zc.chemins import plus_court_chemin
from zc.navigation import Arc, graphe_de_la_zone
from zc.simulation import DANS_NOEUD, PARTI, Agent, Simulation


@dataclass
class ParametresDemande:
    """Réglages d'une journée de visites."""

    arrivees_par_minute: dict[str, float]  # pour chaque source, visiteurs par minute
    part_pmr: float  # entre 0 et 1
    visite_min: float  # durée minimale dans un magasin, en secondes
    visite_max: float  # durée maximale dans un magasin, en secondes
    beta: float = 1.0  # sensibilité à la foule du critère « moins encombré »


@dataclass
class Visite:
    """Ce qu'un visiteur a prévu de faire."""

    source: str  # d'où il vient, et où il reviendra
    programme: list[str]  # magasins qu'il lui reste à visiter (le premier : en cours)
    fin_visite: float | None = None  # instant où il quittera le magasin où il est


def trajet_praticable(graphe: dict[str, list[Arc]], depart: str,
                      itineraire: list[str]) -> bool:
    """Chaque pas du trajet correspond-il encore à un arc du graphe de navigation ?
    (Un nœud ou une arête bloqués n'y figurent plus.)"""
    precedent = depart
    for noeud in itineraire:
        if precedent not in graphe:
            return False
        existe = False
        for arc in graphe[precedent]:
            if arc.arrivee == noeud:
                existe = True
        if not existe:
            return False
        precedent = noeud
    return True


class Demande:
    """Fait arriver les visiteurs et dérouler leurs visites dans une simulation."""

    def __init__(self, sim: Simulation, parametres: ParametresDemande) -> None:
        self.sim = sim
        self.parametres = parametres
        self.visites: dict[int, Visite] = {}
        self.crees = 0
        self.repartis = 0

        # Pour chaque centre, la liste de ses magasins.
        self.magasins: dict[str, list[str]] = {}
        for c in sim.zone.centres:
            self.magasins[c.id] = []
            for n in c.centre.noeuds:
                if n.type == "magasin":
                    self.magasins[c.id].append(n.id)

    def pas(self) -> None:
        """Un pas de la journée : visites en cours, nouvelles arrivées, puis déplacements."""
        # On refait les graphes à chaque pas, car les poids « moins encombré » dépendent
        # du taux τ des arêtes, mis à jour par la simulation au pas précédent.
        encombre = graphe_de_la_zone(self.sim.zone, "encombre", self.parametres.beta)
        pmr = graphe_de_la_zone(self.sim.zone, "pmr")
        self.faire_avancer_les_visites(encombre, pmr)
        self.faire_arriver(encombre, pmr)
        self.sim.pas()

    def trajet(self, agent_pmr: bool, depart: str, arrivee: str,
               encombre: dict[str, list[Arc]], pmr: dict[str, list[Arc]]) -> list[str] | None:
        """Nœuds à parcourir de `depart` à `arrivee` (sans `depart`), ou None."""
        graphe = encombre
        if agent_pmr:
            graphe = pmr
        resultat = plus_court_chemin(graphe, depart, arrivee)
        if resultat is None:
            return None
        return resultat[1][1:]

    def faire_arriver(self, encombre: dict[str, list[Arc]],
                      pmr: dict[str, list[Arc]]) -> None:
        """Nouveaux visiteurs : en moyenne `arrivees_par_minute` par source."""
        hasard = self.sim.hasard
        for source in sorted(self.parametres.arrivees_par_minute):
            attendu = self.parametres.arrivees_par_minute[source] * self.sim.dt / 60
            nombre = int(attendu)
            if hasard.random() < attendu - nombre:
                nombre += 1  # la partie décimale donne une arrivée de plus, au hasard
            for _ in range(nombre):
                centre = hasard.choice(sorted(self.magasins))
                combien = hasard.randint(1, min(3, len(self.magasins[centre])))
                programme = hasard.sample(self.magasins[centre], combien)
                est_pmr = hasard.random() < self.parametres.part_pmr
                chemin = self.trajet(est_pmr, source, programme[0], encombre, pmr)
                if chemin is None:
                    continue  # aucun chemin possible : le visiteur ne vient pas
                agent = self.sim.ajouter_agent(source, chemin, pmr=est_pmr)
                self.visites[agent.id] = Visite(source=source, programme=programme)
                self.crees += 1

    def faire_avancer_les_visites(self, encombre: dict[str, list[Arc]],
                                  pmr: dict[str, list[Arc]]) -> None:
        """Pour chaque visiteur arrivé au bout de son trajet : visiter, repartir vers le
        magasin suivant ou vers sa source, ou quitter la zone."""
        for agent in self.sim.agents:
            if agent.etat != DANS_NOEUD:
                continue  # sur une arête ou en attente : rien à décider
            if len(agent.itineraire) > 0:
                self.verifier_le_trajet(agent, encombre, pmr)
                continue
            visite = self.visites[agent.id]

            if len(visite.programme) == 0:
                # Revenu à sa source : il repart.
                self.sim.retirer(agent)
                self.repartis += 1
                continue

            if visite.fin_visite is None:
                # Il vient d'entrer dans le magasin : on tire la durée de la visite.
                duree = self.sim.hasard.uniform(self.parametres.visite_min,
                                                self.parametres.visite_max)
                visite.fin_visite = self.sim.temps + duree
                continue

            if self.sim.temps >= visite.fin_visite:
                self.partir_vers_la_suite(agent, visite, encombre, pmr)

    def verifier_le_trajet(self, agent: Agent, encombre: dict[str, list[Arc]],
                           pmr: dict[str, list[Arc]]) -> None:
        """Si le reste du trajet n'est plus praticable (un nœud ou une arête est devenu
        bloqué), l'agent recalcule son chemin vers la même destination. S'il n'y en a
        aucun, il garde l'ancien et réessaiera au pas suivant."""
        graphe = encombre
        if agent.pmr:
            graphe = pmr
        if trajet_praticable(graphe, agent.position, agent.itineraire):
            return
        destination = agent.itineraire[-1]
        chemin = self.trajet(agent.pmr, agent.position, destination, encombre, pmr)
        if chemin is not None:
            agent.itineraire = chemin

    def partir_vers_la_suite(self, agent: Agent, visite: Visite,
                             encombre: dict[str, list[Arc]],
                             pmr: dict[str, list[Arc]]) -> None:
        """Visite finie : direction le magasin suivant, ou la source s'il n'y en a plus."""
        if len(visite.programme) > 1:
            suite = visite.programme[1]
        else:
            suite = visite.source
        chemin = self.trajet(agent.pmr, agent.position, suite, encombre, pmr)
        if chemin is None:
            return  # pas de chemin pour l'instant : il réessaiera au pas suivant
        visite.programme.pop(0)
        visite.fin_visite = None
        agent.itineraire = chemin

    def presents(self) -> int:
        """Visiteurs encore dans la zone (partout sauf repartis)."""
        total = 0
        for agent in self.sim.agents:
            if agent.etat != PARTI:
                total += 1
        return total
