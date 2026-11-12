"""Plus courts chemins dans le graphe de navigation : algorithme de Dijkstra.

Les trois itinéraires de la consigne (§ 1, question 2) utilisent le même algorithme ;
seul change le poids des arcs, fixé par le critère du graphe de navigation
(`zc/navigation.py`) :

- plus court chemin : poids = longueur ;
- moins encombré    : poids = longueur × (1 + β × τ) ;
- accessible PMR    : poids = longueur, sur le graphe sans arête non PMR.

Dijkstra exige des poids positifs ou nuls : c'est le cas, car les longueurs sont
positives (vérifié au chargement), τ ≥ 0 et β ≥ 0 (vérifié par la navigation).
"""

import heapq

from zc.navigation import Arc


def dijkstra(graphe: dict[str, list[Arc]],
             depart: str) -> tuple[dict[str, float], dict[str, str]]:
    """Distances depuis `depart` vers tous les nœuds accessibles.

    Renvoie deux dictionnaires :
    - `distances[n]` : coût du meilleur chemin de `depart` à `n` ;
    - `predecesseurs[n]` : le nœud juste avant `n` sur ce chemin.
    Un nœud inaccessible n'apparaît dans aucun des deux. `depart` doit être un nœud du
    graphe (pour un départ peut-être bloqué, passer par `plus_court_chemin`).

    Principe : on traite les nœuds par distance croissante. Le tas (file de priorité)
    donne à chaque tour le nœud non traité le plus proche ; sa distance est alors
    définitive, et on essaie d'améliorer celle de ses voisins.
    Complexité : O((V + E) log V) avec un tas binaire, pour V nœuds et E arcs.
    """
    distances = {depart: 0.0}
    predecesseurs: dict[str, str] = {}
    traites = set()
    tas = [(0.0, depart)]

    while len(tas) > 0:
        distance, noeud = heapq.heappop(tas)
        if noeud in traites:
            continue  # ancienne entrée du tas, le nœud a déjà été traité
        traites.add(noeud)

        for arc in graphe[noeud]:
            nouvelle_distance = distance + arc.poids
            voisin = arc.arrivee
            if voisin not in distances or nouvelle_distance < distances[voisin]:
                distances[voisin] = nouvelle_distance
                predecesseurs[voisin] = noeud
                heapq.heappush(tas, (nouvelle_distance, voisin))

    return distances, predecesseurs


def reconstruire_chemin(predecesseurs: dict[str, str], depart: str,
                        arrivee: str) -> list[str]:
    """Remonte les prédécesseurs depuis l'arrivée jusqu'au départ. Complexité O(V)."""
    chemin = [arrivee]
    while chemin[-1] != depart:
        chemin.append(predecesseurs[chemin[-1]])
    chemin.reverse()
    return chemin


def plus_court_chemin(graphe: dict[str, list[Arc]], depart: str,
                      arrivee: str) -> tuple[float, list[str]] | None:
    """Meilleur chemin de `depart` à `arrivee` selon les poids du graphe.

    Renvoie (coût, liste des nœuds du chemin), ou None s'il n'y a aucun chemin
    (arrivée inaccessible, ou départ / arrivée retirés du graphe car bloqués).
    Complexité : celle de Dijkstra, O((V + E) log V).
    """
    if depart not in graphe or arrivee not in graphe:
        return None
    distances, predecesseurs = dijkstra(graphe, depart)
    if arrivee not in distances:
        return None
    return distances[arrivee], reconstruire_chemin(predecesseurs, depart, arrivee)
