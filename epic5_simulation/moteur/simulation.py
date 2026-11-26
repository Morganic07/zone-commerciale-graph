"""
Simulation : les visiteurs (agents) se déplacent dans le réseau, seconde par seconde.

Un agent est toujours dans l'un de ces trois états :
- « noeud » : il est dans un nœud ;
- « arete » : il marche sur une arête ;
- « attente » : il attend qu'il y ait de la place dans le nœud suivant.

À chaque pas, deux règles de la consigne sont respectées :
- un nœud ne contient jamais plus de personnes que sa capacité (o_v ≤ c_v) ;
- une arête ne laisse pas entrer plus de c_e · Δt personnes par pas (φ_e ≤ c_e · Δt).
"""

import random
from dataclasses import dataclass

from epic4_algorithmes.moteur.chemins import chemin_pmr, plus_court_chemin

# Durée d'un pas de temps, en secondes (Δt, PLAN.md § 4.1).
DUREE_DU_PAS = 1




"""Un visiteur.

    `chemin` : les nœuds qu'il lui reste à atteindre ; le premier est le nœud suivant.
    Quand la liste est vide, il est arrivé.
    `noeud` : le nœud où il est, ou celui qu'il vient de quitter s'il est sur une arête
    ("" tant qu'il n'est entré dans aucun nœud).
"""
@dataclass
class Agent:

    pmr: bool  # vrai pour une personne en fauteuil roulant
    chemin: list
    noeud: str = ""
    etat: str = "attente"  # « noeud », « arete » ou « attente »
    position: float = 0  # mètres parcourus sur l'arête


@dataclass
class Simulation:
    """Tout ce que la simulation garde d'un pas à l'autre."""

    vitesse_valide: float  # en mètres par seconde
    vitesse_pmr: float
    noeuds: dict  # identifiant → nœud
    aretes: dict  # (départ, arrivée) → arête
    agents: list


def creer_simulation(reseau, vitesse_valide, vitesse_pmr):
    """Prépare une simulation sur le réseau, sans aucun agent."""
    noeuds = {}
    toutes_les_aretes = []
    for station_placee in reseau.stations:
        for noeud in station_placee.station.noeuds:
            noeuds[noeud.id] = noeud
        for arete in station_placee.station.aretes:
            toutes_les_aretes.append(arete)
    for tunnel in reseau.connexions:
        toutes_les_aretes.append(tunnel)

    # Chaque arête est rangée sous (départ, arrivée) et sous (arrivée, départ) : toutes
    # nos arêtes sont bidirectionnelles (PLAN.md § 2.2).
    aretes = {}
    for arete in toutes_les_aretes:
        aretes[(arete.source, arete.cible)] = arete
        aretes[(arete.cible, arete.source)] = arete

    return Simulation(
        vitesse_valide=vitesse_valide,
        vitesse_pmr=vitesse_pmr,
        noeuds=noeuds,
        aretes=aretes,
        agents=[],
    )


def ajouter_visiteurs(simulation, reseau, nombre, part_pmr):
    """Crée `nombre` visiteurs. Chacun part d'un sas tiré au sort vers un module tiré au
    sort, et il est en fauteuil avec la probabilité `part_pmr`.

    Son chemin, calculé une seule fois par Dijkstra, est la liste des nœuds du sas au
    module, par exemple ["A:A1", "A:A2", "A:A5", "A:A6"].
    """
    sas = []
    modules = []
    for identifiant in simulation.noeuds:
        type_du_noeud = simulation.noeuds[identifiant].type
        if type_du_noeud == "sortie":
            sas.append(identifiant)
        if type_du_noeud == "module" or type_du_noeud == "sanitaire":
            modules.append(identifiant)

    for numero in range(nombre):
        depart = random.choice(sas)
        arrivee = random.choice(modules)
        en_fauteuil = random.random() < part_pmr

        if en_fauteuil:
            chemin, cout = chemin_pmr(reseau, depart, arrivee)
        else:
            chemin, cout = plus_court_chemin(reseau, depart, arrivee)

        # Le visiteur attend devant son sas : il entrera s'il y a de la place.
        simulation.agents.append(Agent(pmr=en_fauteuil, chemin=chemin))


def pas(simulation):
    """Joue un pas de temps, en trois étapes (PLAN.md § 4.2).

    Complexité : O(A), A agents (chaque étape parcourt les agents une fois).
    """
    # On mélange les agents : quand la place manque, les premiers de la liste passent.
    # C'est donc le hasard qui décide qui passe.
    random.shuffle(simulation.agents)

    # 1. Chaque agent sur une arête avance de v · Δt. Au bout, il passe en attente.
    for agent in simulation.agents:
        if agent.etat == "arete":
            if agent.pmr:
                vitesse = simulation.vitesse_pmr
            else:
                vitesse = simulation.vitesse_valide
            agent.position = agent.position + vitesse * DUREE_DU_PAS

            arete = simulation.aretes[(agent.noeud, agent.chemin[0])]
            if agent.position >= arete.longueur:
                agent.etat = "attente"

    # 2. Chaque agent en attente entre dans le nœud suivant, s'il n'est pas plein.
    for agent in simulation.agents:
        if agent.etat == "attente":
            suivant = simulation.noeuds[agent.chemin[0]]
            if suivant.occupation < suivant.capacite_max:
                suivant.occupation = suivant.occupation + 1
                agent.noeud = agent.chemin.pop(0)
                agent.etat = "noeud"

    # 3. Chaque agent dans un nœud prend l'arête suivante, si elle a encore de la place
    # pour ce pas. Un agent arrivé au bout de son chemin reste dans son nœud.
    # `entrees` compte les entrées de ce pas sur chaque arête (φ_e). Les deux sens d'une
    # arête comptent ensemble, sous la même clé (source, cible).
    entrees = {}
    for agent in simulation.agents:
        if agent.etat == "noeud" and len(agent.chemin) > 0:
            arete = simulation.aretes[(agent.noeud, agent.chemin[0])]
            cle = (arete.source, arete.cible)
            if cle not in entrees:
                entrees[cle] = 0

            if entrees[cle] + 1 <= arete.capacite_max * DUREE_DU_PAS:
                entrees[cle] = entrees[cle] + 1
                depart = simulation.noeuds[agent.noeud]
                depart.occupation = depart.occupation - 1
                agent.etat = "arete"
                agent.position = 0
