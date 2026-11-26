"""
Simulation : les visiteurs (agents) se déplacent dans le réseau, pas de temps par pas
de temps.

Un agent est toujours dans l'un de ces trois états :
- « noeud » : il est dans un nœud ;
- « arete » : il marche sur une arête ;
- « attente » : il attend qu'il y ait de la place dans le nœud suivant.

Deux règles de la consigne sont respectées à chaque pas :
- un nœud ne contient jamais plus de personnes que sa capacité (o_v ≤ c_v) ;
- une arête ne laisse pas entrer plus de c_e · Δt personnes par pas (φ_e ≤ c_e · Δt).
"""

import random
from dataclasses import dataclass

# Durée d'un pas de temps, en secondes (Δt, PLAN.md § 4.1).
DUREE_DU_PAS = 1


@dataclass
class Agent:
    """Un visiteur.

    `chemin` est la liste des nœuds qu'il lui reste à atteindre. Le premier est le
    nœud suivant. Quand la liste est vide, il est arrivé.
    `noeud` est le nœud où il est, ou celui qu'il vient de quitter s'il est sur une
    arête. Il vaut "" tant que l'agent n'est entré dans aucun nœud.
    """

    pmr: bool  # vrai pour une personne en fauteuil roulant
    chemin: list
    noeud: str = ""
    etat: str = "attente"  # « noeud », « arete » ou « attente »
    position: float = 0  # mètres parcourus sur l'arête


@dataclass
class Simulation:
    """Tout ce que la simulation garde d'un pas à l'autre."""

    hasard: random.Random  # tout le hasard vient de là : même graine, même simulation
    vitesse_valide: float  # en mètres par seconde
    vitesse_pmr: float
    noeuds: dict  # identifiant → nœud
    aretes: dict  # (départ, arrivée) → arête
    agents: list


def creer_simulation(reseau, vitesse_valide, vitesse_pmr, graine):
    """Prépare une simulation sur le réseau, sans aucun agent."""
    # Les nœuds, rangés par identifiant.
    noeuds = {}
    for station_placee in reseau.stations:
        for noeud in station_placee.station.noeuds:
            noeuds[noeud.id] = noeud

    # Toutes les arêtes : celles des stations, puis les tunnels.
    toutes_les_aretes = []
    for station_placee in reseau.stations:
        for arete in station_placee.station.aretes:
            toutes_les_aretes.append(arete)
    for tunnel in reseau.connexions:
        toutes_les_aretes.append(tunnel)

    # Les arêtes, rangées par (départ, arrivée). Une arête bidirectionnelle est
    # rangée deux fois, une fois dans chaque sens.
    aretes = {}
    for arete in toutes_les_aretes:
        aretes[(arete.source, arete.cible)] = arete
        if arete.sens == "bidirectionnel":
            aretes[(arete.cible, arete.source)] = arete

    return Simulation(
        hasard=random.Random(graine),
        vitesse_valide=vitesse_valide,
        vitesse_pmr=vitesse_pmr,
        noeuds=noeuds,
        aretes=aretes,
        agents=[],
    )


def pas(simulation):
    """Joue un pas de temps (PLAN.md § 4.2), en trois étapes.

    Complexité : O(A), A agents (chaque étape parcourt les agents une fois).
    """
    # On mélange les agents : quand la place manque dans un nœud ou sur une arête,
    # ceux qui sont en tête de liste passent les premiers. C'est donc le hasard qui
    # décide qui passe.
    simulation.hasard.shuffle(simulation.agents)

    # 1. Chaque agent sur une arête avance de v · Δt.
    for agent in simulation.agents:
        if agent.etat == "arete":
            if agent.pmr:
                vitesse = simulation.vitesse_pmr
            else:
                vitesse = simulation.vitesse_valide
            agent.position = agent.position + vitesse * DUREE_DU_PAS

            # Au bout de l'arête, il attend d'entrer dans le nœud suivant.
            arete = simulation.aretes[(agent.noeud, agent.chemin[0])]
            if agent.position >= arete.longueur:
                agent.etat = "attente"

    # 2. Chaque agent en attente entre dans le nœud suivant, s'il y a de la place.
    # Sinon, il réessaiera au pas suivant.
    for agent in simulation.agents:
        if agent.etat == "attente":
            suivant = simulation.noeuds[agent.chemin[0]]
            if suivant.occupation < suivant.capacite_max:
                suivant.occupation = suivant.occupation + 1
                agent.noeud = agent.chemin.pop(0)
                agent.etat = "noeud"

    # 3. Chaque agent dans un nœud prend l'arête suivante, s'il y a de la place.
    # Un agent arrivé au bout de son chemin reste dans son nœud.
    # `entrees` compte les personnes entrées sur chaque arête pendant ce pas (φ_e).
    # Les deux sens d'une arête comptent ensemble : on range ses entrées sous
    # (source, cible), quel que soit le sens de passage.
    entrees = {}
    for agent in simulation.agents:
        if agent.etat == "noeud" and len(agent.chemin) > 0:
            arete = simulation.aretes[(agent.noeud, agent.chemin[0])]
            cle = (arete.source, arete.cible)
            if cle not in entrees:
                entrees[cle] = 0

            # Une entrée de plus ne doit pas dépasser c_e · Δt. Sinon, l'arête est
            # pleine pour ce pas, et l'agent réessaiera au pas suivant.
            if entrees[cle] + 1 <= arete.capacite_max * DUREE_DU_PAS:
                entrees[cle] = entrees[cle] + 1
                depart = simulation.noeuds[agent.noeud]
                depart.occupation = depart.occupation - 1
                agent.etat = "arete"
                agent.position = 0
