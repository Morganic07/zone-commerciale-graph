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

from zc.modele import SEPARATEUR, Zone
from zc.navigation import Arc, graphe_de_la_zone


def dijkstra(graphe: dict[str, list[Arc]],
             depart: str) -> tuple[dict[str, float], dict[str, str]]:
    """Distances depuis `depart` vers tous les nœuds accessibles.

    Renvoie deux dictionnaires :
    - `distances[n]` : coût du meilleur chemin de `depart` à `n` ;
    - `predecesseurs[n]` : le nœud juste avant `n` sur ce chemin.
    Un nœud inaccessible n'apparaît dans aucun des deux. `depart` doit être un nœud du
    graphe (pour un départ peut-être bloqué, passer par `plus_court_chemin`).
    Complexité : O((V + E) log V), voir `dijkstra_plusieurs_departs`.
    """
    return dijkstra_plusieurs_departs(graphe, [depart])


def dijkstra_plusieurs_departs(graphe: dict[str, list[Arc]],
                               departs: list[str]) -> tuple[dict[str, float], dict[str, str]]:
    """Comme `dijkstra`, mais tous les nœuds de `departs` partent à distance 0 en même
    temps : `distances[n]` est le coût depuis le départ le plus proche de `n`.

    Principe : on traite les nœuds par distance croissante. Le tas (file de priorité)
    donne à chaque tour le nœud non traité le plus proche ; sa distance est alors
    définitive, et on essaie d'améliorer celle de ses voisins.
    Complexité : O((V + E) log V) avec un tas binaire, pour V nœuds et E arcs, quel
    que soit le nombre de départs.
    """
    distances = {}
    tas = []
    for depart in departs:
        distances[depart] = 0.0
        tas.append((0.0, depart))
    heapq.heapify(tas)
    predecesseurs: dict[str, str] = {}
    traites = set()

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


def inverser(graphe: dict[str, list[Arc]]) -> dict[str, list[Arc]]:
    """Graphe inversé : chaque arc u → v devient v → u, avec le même poids.
    Un chemin de n vers une sortie dans le graphe devient un chemin de la sortie vers n
    dans le graphe inversé. Complexité O(V + E)."""
    inverse: dict[str, list[Arc]] = {}
    for noeud in graphe:
        inverse[noeud] = []
    for noeud in graphe:
        for arc in graphe[noeud]:
            inverse[arc.arrivee].append(Arc(arc.arrivee, arc.depart, arc.poids, arc.arete))
    return inverse


def distances_d_evacuation(graphe: dict[str, list[Arc]],
                           sorties: list[str]) -> tuple[dict[str, float], dict[str, str]]:
    """Distance de chaque nœud à la sortie la plus proche, en un seul calcul.

    On lance Dijkstra depuis toutes les sorties à la fois sur le graphe inversé, au lieu
    d'un Dijkstra par nœud. Renvoie :
    - `distances[n]` : coût du meilleur chemin de `n` vers une sortie ;
    - `suivants[n]` : le nœud où aller depuis `n` pour suivre ce chemin.
    Un nœud sans aucun chemin vers une sortie (piégé) n'apparaît pas dans `distances`.
    Les sorties absentes du graphe (bloquées) sont ignorées.
    Complexité : O((V + E) log V), comme un seul Dijkstra.
    """
    sorties_ouvertes = []
    for s in sorties:
        if s in graphe:
            sorties_ouvertes.append(s)
    # Dans le graphe inversé, le prédécesseur de n est le nœud suivant vers la sortie.
    return dijkstra_plusieurs_departs(inverser(graphe), sorties_ouvertes)


def chemin_d_evacuation(suivants: dict[str, str], sorties: list[str],
                        noeud: str) -> list[str]:
    """Suit les `suivants` depuis `noeud` jusqu'à une sortie. Complexité O(V).
    `noeud` doit pouvoir évacuer, c'est-à-dire figurer dans les `distances` renvoyées
    par `distances_d_evacuation` ; un nœud piégé n'a pas de chemin à suivre."""
    chemin = [noeud]
    while chemin[-1] not in sorties:
        chemin.append(suivants[chemin[-1]])
    return chemin


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


def itineraire(zone: Zone, source: str, centre: str, critere: str, beta: float = 0.0,
               magasin: str | None = None) -> tuple[float, list[str]] | None:
    """Itinéraire d'une région (source) vers un centre commercial (consigne § 1, Q2).

    Sans `magasin`, l'itinéraire s'arrête à la sortie du centre la moins coûteuse à
    atteindre : c'est l'entrée du visiteur. Avec `magasin` (identifiant dans le centre,
    par exemple « M4 »), il continue jusqu'au magasin.
    `critere` : « court », « encombre » ou « pmr » (voir `zc/navigation.py`).
    Renvoie (coût, liste des nœuds), ou None s'il n'y a aucun chemin (sens interdits,
    passages bloqués). Une source, un centre ou un magasin inconnus lèvent ValueError :
    une faute de frappe ne doit pas passer pour un itinéraire impossible.
    Complexité : un seul Dijkstra, O((V + E) log V) sur le graphe de la zone.
    """
    ids_sources = []
    for s in zone.sources:
        ids_sources.append(s.id)
    if source not in ids_sources:
        raise ValueError(f"source « {source} » inconnue")

    sorties = []
    ids_noeuds = []
    for c in zone.centres:
        if c.id == centre:
            for n in c.centre.noeuds:
                ids_noeuds.append(n.id)
                if n.type == "sortie":
                    sorties.append(n.id)
    if len(sorties) == 0:
        raise ValueError(f"centre « {centre} » inconnu ou sans sortie")

    graphe = graphe_de_la_zone(zone, critere, beta)
    if magasin is not None:
        arrivee = centre + SEPARATEUR + magasin
        if arrivee not in ids_noeuds:
            raise ValueError(f"« {magasin} » n'existe pas dans le centre « {centre} »")
        return plus_court_chemin(graphe, source, arrivee)

    distances, predecesseurs = dijkstra(graphe, source)
    meilleure_sortie = None
    for sortie in sorties:
        if sortie in distances:
            if meilleure_sortie is None or distances[sortie] < distances[meilleure_sortie]:
                meilleure_sortie = sortie
    if meilleure_sortie is None:
        return None
    chemin = reconstruire_chemin(predecesseurs, source, meilleure_sortie)
    return distances[meilleure_sortie], chemin
