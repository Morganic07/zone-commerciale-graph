"""
Graphe de navigation : la carte des déplacements possibles dans le réseau.

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
    paire_de_noeuds = (arete.source, arete.cible)
    taux_de_l_arete = 0.0
    if paire_de_noeuds in taux:
        taux_de_l_arete = taux[paire_de_noeuds]
    return arete.longueur * (1 + beta * taux_de_l_arete)


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
    voisins_par_noeud: dict[str, list[tuple[str, float]]] = {}

    # Les nœuds praticables, tous stations confondues. Un nœud bloqué n'y est pas.
    for station_placee in reseau.stations:
        for noeud in station_placee.station.noeuds:
            if noeud.statut != "bloqué":
                voisins_par_noeud[noeud.id] = []
    for point_d_arrivee in reseau.sources:
        voisins_par_noeud[point_d_arrivee.id] = []

    # Toutes les arêtes : celles des stations, puis les tunnels.
    toutes_les_aretes = []
    for station_placee in reseau.stations:
        for arete in station_placee.station.aretes:
            toutes_les_aretes.append(arete)
    for tunnel in reseau.connexions:
        toutes_les_aretes.append(tunnel)

    for arete in toutes_les_aretes:
        # Une arête bloquée ne donne aucun arc.
        if arete.statut == "bloqué":
            continue

        # Pour un trajet en fauteuil, une arête non praticable ne donne aucun arc.
        interdite_au_fauteuil = pmr and not arete.pmr
        if interdite_au_fauteuil:
            continue

        # Une arête qui touche un nœud bloqué ne mène nulle part : le nœud bloqué
        # n'a pas été mis dans `voisins_par_noeud`.
        depart_bloque = arete.source not in voisins_par_noeud
        arrivee_bloquee = arete.cible not in voisins_par_noeud
        if depart_bloque or arrivee_bloquee:
            continue

        # L'arc aller, puis l'arc retour si l'arête se prend dans les deux sens.
        cout_du_passage = cout(arete, beta, taux)
        voisins_par_noeud[arete.source].append((arete.cible, cout_du_passage))
        if arete.sens == "bidirectionnel":
            voisins_par_noeud[arete.cible].append((arete.source, cout_du_passage))

    return voisins_par_noeud
