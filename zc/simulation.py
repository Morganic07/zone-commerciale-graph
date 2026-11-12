"""Simulation des déplacements, en temps discret (consigne § 2.5, PLAN.md § 4.2).

Chaque visiteur est un agent (extension ⋆ de la consigne) qui suit un itinéraire : la
liste des nœuds à traverser. Un agent est dans l'un de ces trois états :

- DANS_NOEUD : il occupe un nœud (il compte dans son occupation) ;
- SUR_ARETE  : il marche le long d'une arête, à sa vitesse (valide ou PMR) ;
- EN_ATTENTE : il est arrivé au bout de l'arête, mais le nœud suivant était plein ; il
  attend et réessaie au pas suivant.

Le modèle minimal imposé est respecté à chaque pas :
- un nœud v n'accepte que c_v − o_v nouvelles personnes, donc o_v ≤ c_v ;
- une arête e accepte au plus ⌊c_e × Δt⌋ entrées par pas, donc φ_e ≤ c_e × Δt.
  L'arrondi inférieur est prudent : une arête de 1,58 pers/s laisse entrer 1 personne
  par seconde, jamais 2.

Quand il y a plus de candidats que de places, on tire au sort qui passe, avec le
générateur `random.Random(graine)` de la simulation : même graine, même simulation.

Un agent qui entre dans un nœud intermédiaire (un carrefour) peut en repartir au même
pas : il le traverse sans s'arrêter, comme un piéton. La place du nœud est quand même
vérifiée à l'entrée.
"""

import random
from dataclasses import dataclass

from zc.modele import Arete, Noeud, Zone
from zc.parametres import ParametresPhysiques

DANS_NOEUD = "dans_noeud"
SUR_ARETE = "sur_arete"
EN_ATTENTE = "en_attente"


@dataclass
class Agent:
    """Un visiteur."""

    id: int
    pmr: bool
    position: str  # le nœud où il est, ou d'où il vient s'il est sur une arête
    itineraire: list[str]  # les nœuds qu'il lui reste à atteindre, dans l'ordre
    etat: str = DANS_NOEUD
    arete: int | None = None  # numéro de l'arête parcourue (dans Simulation.aretes)
    avancee: float = 0.0  # mètres déjà parcourus sur cette arête


class Simulation:
    """État d'une simulation sur toute la zone, avancé pas à pas par `pas()`."""

    def __init__(self, zone: Zone, parametres: ParametresPhysiques, graine: int,
                 dt: float = 1.0) -> None:
        self.zone = zone
        self.parametres = parametres
        self.hasard = random.Random(graine)
        self.dt = dt
        self.temps = 0.0
        self.agents: list[Agent] = []

        # Les nœuds des centres, rangés par identifiant. La simulation part de centres
        # vides : toutes les personnes présentes sont des agents.
        self.noeuds: dict[str, Noeud] = {}
        for c in zone.centres:
            for n in c.centre.noeuds:
                n.occupation = 0
                self.noeuds[n.id] = n
        self.sources = set()
        for s in zone.sources:
            self.sources.add(s.id)

        # Toutes les arêtes (couloirs et connexions), et pour chaque paire (u, v) les
        # numéros des arêtes qui permettent d'aller de u à v.
        self.aretes: list[Arete] = []
        for c in zone.centres:
            for a in c.centre.aretes:
                self.aretes.append(a)
        for a in zone.connexions:
            self.aretes.append(a)
        self.aretes_vers: dict[tuple[str, str], list[int]] = {}
        for i in range(len(self.aretes)):
            a = self.aretes[i]
            # Avec c_e × Δt < 1, l'arrondi inférieur donnerait 0 entrée par pas : l'arête
            # serait infranchissable sans que rien ne le signale.
            if a.capacite_max * dt < 1:
                raise ValueError(f"arête {a.source} – {a.cible} : capacité {a.capacite_max} "
                                 f"pers/s, moins d'une personne par pas de {dt} s ; "
                                 "élargir le passage ou allonger le pas de temps")
            self.ajouter_sens(a.source, a.cible, i)
            if a.sens == "bidirectionnel":
                self.ajouter_sens(a.cible, a.source, i)

        # Nombre d'entrées sur chaque arête pendant le dernier pas (φ_e).
        self.flux = [0] * len(self.aretes)

    def ajouter_sens(self, depart: str, arrivee: str, i: int) -> None:
        """Note que l'arête numéro i permet d'aller de `depart` à `arrivee`."""
        if (depart, arrivee) not in self.aretes_vers:
            self.aretes_vers[(depart, arrivee)] = []
        self.aretes_vers[(depart, arrivee)].append(i)

    # --- agents -----------------------------------------------------------------------

    def ajouter_agent(self, depart: str, itineraire: list[str], pmr: bool = False) -> Agent:
        """Place un nouvel agent dans `depart` (une source, ou un nœud qui a de la place),
        avec la liste des nœuds à atteindre ensuite."""
        precedent = depart
        for noeud in itineraire:
            if (precedent, noeud) not in self.aretes_vers:
                raise ValueError(f"aucune arête de « {precedent} » vers « {noeud} »")
            precedent = noeud
        if depart not in self.sources:
            n = self.noeuds[depart]
            if n.occupation >= n.capacite_max:
                raise ValueError(f"« {depart} » est plein")
            n.occupation += 1
        agent = Agent(id=len(self.agents), pmr=pmr, position=depart,
                      itineraire=list(itineraire))
        self.agents.append(agent)
        return agent

    def vitesse(self, agent: Agent) -> float:
        if agent.pmr:
            return self.parametres.vitesse_pmr
        return self.parametres.vitesse_marche

    # --- un pas de temps ----------------------------------------------------------------

    def pas(self) -> None:
        """Avance la simulation de Δt secondes."""
        self.avancer_sur_les_aretes()
        self.entrer_dans_les_noeuds()
        self.entrer_sur_les_aretes()
        self.temps += self.dt

    def avancer_sur_les_aretes(self) -> None:
        """Les agents sur une arête marchent ; au bout, ils passent en attente."""
        for agent in self.agents:
            if agent.etat == SUR_ARETE and agent.arete is not None:
                agent.avancee += self.vitesse(agent) * self.dt
                longueur = self.aretes[agent.arete].longueur
                if agent.avancee >= longueur:
                    agent.avancee = longueur
                    agent.etat = EN_ATTENTE

    def entrer_dans_les_noeuds(self) -> None:
        """Les agents en attente entrent dans le nœud suivant s'il reste de la place.
        S'il y a trop de candidats, on tire au sort."""
        candidats: dict[str, list[Agent]] = {}
        for agent in self.agents:
            if agent.etat == EN_ATTENTE:
                noeud = agent.itineraire[0]
                if noeud not in candidats:
                    candidats[noeud] = []
                candidats[noeud].append(agent)

        for noeud in sorted(candidats):
            liste = candidats[noeud]
            self.hasard.shuffle(liste)
            if noeud in self.sources:
                places = len(liste)  # une source accueille tout le monde
            else:
                places = self.noeuds[noeud].capacite_max - self.noeuds[noeud].occupation
            for agent in liste[:places]:
                if noeud not in self.sources:
                    self.noeuds[noeud].occupation += 1
                agent.position = noeud
                agent.itineraire.pop(0)
                agent.etat = DANS_NOEUD
                agent.arete = None
                agent.avancee = 0.0

    def entrer_sur_les_aretes(self) -> None:
        """Les agents qui ont encore un trajet à faire quittent leur nœud et s'engagent
        sur l'arête suivante, dans la limite de ⌊c_e × Δt⌋ entrées par arête et par pas.
        S'il y a trop de candidats, on tire au sort."""
        candidats: dict[int, list[Agent]] = {}
        for agent in self.agents:
            if agent.etat == DANS_NOEUD and len(agent.itineraire) > 0:
                i = self.choisir_arete(agent.position, agent.itineraire[0])
                if i is not None:
                    if i not in candidats:
                        candidats[i] = []
                    candidats[i].append(agent)

        self.flux = [0] * len(self.aretes)
        for i in sorted(candidats):
            liste = candidats[i]
            self.hasard.shuffle(liste)
            limite = int(self.aretes[i].capacite_max * self.dt)  # arrondi inférieur
            for agent in liste[:limite]:
                if agent.position not in self.sources:
                    self.noeuds[agent.position].occupation -= 1
                agent.etat = SUR_ARETE
                agent.arete = i
                agent.avancee = 0.0
                self.flux[i] += 1

    def choisir_arete(self, depart: str, arrivee: str) -> int | None:
        """Une arête praticable de `depart` vers `arrivee` (la plus courte s'il y en a
        plusieurs), ou None si toutes sont bloquées."""
        meilleure = None
        for i in self.aretes_vers[(depart, arrivee)]:
            if self.aretes[i].statut == "bloqué":
                continue
            if meilleure is None or self.aretes[i].longueur < self.aretes[meilleure].longueur:
                meilleure = i
        return meilleure

    # --- lecture de l'état --------------------------------------------------------------

    def etat(self) -> tuple[list[tuple[int, str, str, int | None, float]], dict[str, int]]:
        """Photographie de l'état : agents (id, état, position, arête, avancée) et
        occupation de chaque nœud. Sert à comparer deux simulations."""
        agents = []
        for a in self.agents:
            agents.append((a.id, a.etat, a.position, a.arete, round(a.avancee, 6)))
        occupations = {}
        for identifiant in self.noeuds:
            occupations[identifiant] = self.noeuds[identifiant].occupation
        return agents, occupations
