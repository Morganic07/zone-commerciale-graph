"""Graphe de navigation : la carte des déplacements possibles dans le réseau.

Les fichiers décrivent des arêtes. Les algorithmes de chemin (Dijkstra) ont besoin d'autre
chose : pour chaque nœud, la liste des nœuds où l'on peut aller, avec le coût du trajet.
Ce module construit cette liste, en tenant compte du sens des arêtes, du fauteuil
roulant (PMR) et des éléments bloqués.
"""

from epic2_donnees.moteur.modele import Arete, Reseau


def cout(arete: Arete, beta: float, taux: dict[tuple[str, str], float]) -> float:
    """Coût d'un passage par l'arête : longueur × (1 + β·τ).

    τ est le taux d'occupation de l'arête (0 si elle n'est pas dans `taux`). Avec β = 0,
    le coût est la longueur : c'est le critère « plus court chemin ». Avec β > 0, une arête
    encombrée coûte plus cher : c'est le critère « moins encombré ».
    """
    cle = (arete.source, arete.cible)
    tau = 0.0
    if cle in taux:
        tau = taux[cle]
    return arete.longueur * (1 + beta * tau)


def graphe_de_navigation(
    reseau: Reseau, pmr: bool, beta: float, taux: dict[tuple[str, str], float]
) -> dict[str, list[tuple[str, float]]]:
    """Renvoie, pour chaque nœud, la liste des (voisin, coût) où l'on peut aller.

    - Une arête « bidirectionnel » donne deux arcs (aller et retour), une arête « unique »
      un seul, de `source` vers `cible`.
    - Si `pmr` est vrai, les arêtes non praticables en fauteuil sont retirées.
    - Les nœuds et les arêtes de statut « bloqué » sont retirés.
    - Les arêtes des stations et les tunnels entre stations forment un seul graphe.

    Complexité : O(V + E), V nœuds et E arêtes (chacun est parcouru une fois).
    """
    voisins: dict[str, list[tuple[str, float]]] = {}

    # Les nœuds praticables, tous stations confondues. Un nœud bloqué n'y est pas.
    for station_du_reseau in reseau.stations:
        for noeud in station_du_reseau.station.noeuds:
            if noeud.statut != "bloqué":
                voisins[noeud.id] = []
    for source in reseau.sources:
        voisins[source.id] = []

    # Toutes les arêtes : celles des stations, puis les tunnels.
    aretes = []
    for station_du_reseau in reseau.stations:
        for arete in station_du_reseau.station.aretes:
            aretes.append(arete)
    for tunnel in reseau.connexions:
        aretes.append(tunnel)

    for arete in aretes:
        # Une arête bloquée, ou interdite aux fauteuils pour un trajet PMR, ne donne aucun arc.
        if arete.statut == "bloqué":
            continue
        if pmr and not arete.pmr:
            continue
        # Une arête qui touche un nœud bloqué ne mène nulle part.
        if arete.source not in voisins or arete.cible not in voisins:
            continue

        valeur = cout(arete, beta, taux)
        voisins[arete.source].append((arete.cible, valeur))
        if arete.sens == "bidirectionnel":
            voisins[arete.cible].append((arete.source, valeur))

    return voisins
