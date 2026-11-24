"""
Chemins : l'algorithme de Dijkstra et une fonction par critère d'itinéraire.

- plus_court_chemin : le coût d'une arête est sa longueur ;
- chemin_le_moins_encombre : le coût est longueur × (1 + β·τ), une arête chargée coûte
  plus cher ;
- chemin_pmr : le coût est la longueur, sans les arêtes interdites aux fauteuils.

Les trois font la même chose : construire le graphe de navigation (navigation.py),
puis y lancer Dijkstra.
"""

from epic4_algorithmes.moteur.navigation import graphe_de_navigation


def dijkstra(graphe, depart, arrivee):
    """Cherche le chemin le moins coûteux de `depart` à `arrivee` dans le graphe.

    `graphe` donne, pour chaque nœud, la liste des (voisin, coût) où l'on peut aller.
    Renvoie (liste des nœuds du chemin, coût total), ou ([], None) s'il n'y a aucun chemin.

    Principe : à chaque tour, on prend le nœud le plus proche du départ parmi ceux qu'on
    n'a pas encore traités ; sa distance est alors définitive, et on regarde ses voisins.

    Complexité : O(V² + E), V nœuds et E arcs (à chaque tour, on parcourt la liste des
    nœuds à traiter pour trouver le plus proche).
    """
    # Un nœud bloqué n'est pas dans le graphe : on ne peut pas partir de lui.
    if depart not in graphe:
        return [], None

    distances = {}  # nœud → coût du meilleur chemin trouvé depuis le départ
    precedents = {}  # nœud → le nœud d'où l'on arrive sur ce meilleur chemin
    a_traiter = []  # nœuds déjà atteints, mais pas encore traités

    distances[depart] = 0
    a_traiter.append(depart)

    while len(a_traiter) > 0:
        # Le nœud à traiter le plus proche du départ.
        noeud = a_traiter[0]
        for candidat in a_traiter:
            if distances[candidat] < distances[noeud]:
                noeud = candidat
        a_traiter.remove(noeud)

        # L'arrivée est traitée : sa distance ne peut plus diminuer, on a fini.
        if noeud == arrivee:
            break

        for voisin, cout in graphe[noeud]:
            nouvelle_distance = distances[noeud] + cout
            # Premier chemin trouvé vers ce voisin : on le note.
            if voisin not in distances:
                distances[voisin] = nouvelle_distance
                precedents[voisin] = noeud
                a_traiter.append(voisin)
            # Chemin plus court que celui qu'on connaissait : on le remplace.
            elif nouvelle_distance < distances[voisin]:
                distances[voisin] = nouvelle_distance
                precedents[voisin] = noeud

    # On n'a jamais atteint l'arrivée : aucun chemin n'y mène.
    if arrivee not in distances:
        return [], None

    # On remonte de l'arrivée jusqu'au départ grâce aux précédents,
    # puis on remet le chemin à l'endroit.
    chemin = [arrivee]
    noeud = arrivee
    while noeud != depart:
        noeud = precedents[noeud]
        chemin.append(noeud)
    chemin.reverse()

    return chemin, distances[arrivee]


def plus_court_chemin(reseau, depart, arrivee):
    """Critère « plus court » : le coût d'une arête est sa longueur.
    Complexité : celle de Dijkstra."""
    # β = 0 : l'encombrement ne compte pas.
    graphe = graphe_de_navigation(reseau, False, 0, {})
    return dijkstra(graphe, depart, arrivee)


def chemin_le_moins_encombre(reseau, depart, arrivee, beta, taux):
    """Critère « moins encombré » : le coût d'une arête est longueur × (1 + β·τ), où τ est
    son taux d'occupation, donné dans `taux`. Complexité : celle de Dijkstra."""
    graphe = graphe_de_navigation(reseau, False, beta, taux)
    return dijkstra(graphe, depart, arrivee)


def chemin_pmr(reseau, depart, arrivee):
    """Critère « PMR » : le coût d'une arête est sa longueur, et les arêtes interdites
    aux fauteuils roulants sont retirées. Complexité : celle de Dijkstra."""
    graphe = graphe_de_navigation(reseau, True, 0, {})
    return dijkstra(graphe, depart, arrivee)
