"""Connexité d'un graphe : composantes connexes, points d'articulation, composantes
fortement connexes, graphe réduit et tri topologique (cours, chapitres 1, 2 et 4).

Les graphes sont donnés par une liste d'adjacence : un dictionnaire qui associe à chaque
nœud la liste de ses voisins (non orienté : chaque arête apparaît dans les deux listes)
ou de ses successeurs (orienté). Ces fonctions servent au graphe des propriétés
(consigne § 4), mais marchent sur n'importe quel graphe.

Limite : les parcours en profondeur sont récursifs, comme dans le cours. Python limite
la profondeur de récursion à 1 000 appels par défaut : un graphe dont un chemin dépasse
environ 900 nœuds lèverait RecursionError (mesuré sur une chaîne). Les graphes du
projet en comptent quelques dizaines.
"""

from collections import deque

# --- composantes connexes (graphe non orienté) -----------------------------------------


def composantes_connexes(graphe: dict[str, list[str]]) -> list[set[str]]:
    """Composantes connexes, par parcours en largeur lancé depuis chaque nœud pas encore
    visité. Le graphe est connexe si et seulement s'il n'y a qu'une composante.
    Complexité O(V + E)."""
    composantes = []
    visites = set()
    for depart in graphe:
        if depart in visites:
            continue
        composante = {depart}
        visites.add(depart)
        file = deque([depart])
        while len(file) > 0:
            noeud = file.popleft()
            for voisin in graphe[noeud]:
                if voisin not in visites:
                    visites.add(voisin)
                    composante.add(voisin)
                    file.append(voisin)
        composantes.append(composante)
    return composantes


# --- points d'articulation (graphe non orienté) ----------------------------------------


def points_d_articulation(graphe: dict[str, list[str]]) -> set[str]:
    """Nœuds dont la suppression augmente le nombre de composantes connexes.

    Algorithme de Hopcroft et Tarjan : un parcours en profondeur numérote les nœuds
    (`indice`) et calcule pour chacun `bas`, le plus petit indice qu'on peut atteindre
    depuis son sous-arbre en remontant au plus une arête de retour.
    - La racine du parcours est un point d'articulation si elle a au moins deux enfants.
    - Un autre nœud u l'est s'il a un enfant v avec bas[v] ≥ indice[u] : le sous-arbre
      de v ne peut pas contourner u.
    Complexité O(V + E).
    """
    indice: dict[str, int] = {}
    bas: dict[str, int] = {}
    articulations: set[str] = set()
    for racine in graphe:
        if racine not in indice:
            _visiter_articulation(graphe, racine, None, indice, bas, articulations)
    return articulations


def _visiter_articulation(graphe: dict[str, list[str]], u: str, parent: str | None,
                          indice: dict[str, int], bas: dict[str, int],
                          articulations: set[str]) -> None:
    """Parcours en profondeur récursif depuis u (sous-fonction de points_d_articulation)."""
    indice[u] = len(indice)  # les nœuds sont numérotés dans l'ordre de visite
    bas[u] = indice[u]
    enfants = 0
    for v in graphe[u]:
        if v not in indice:
            enfants += 1
            _visiter_articulation(graphe, v, u, indice, bas, articulations)
            bas[u] = min(bas[u], bas[v])
            if parent is not None and bas[v] >= indice[u]:
                articulations.add(u)
        elif v != parent:
            bas[u] = min(bas[u], indice[v])  # arête de retour vers un ancêtre
    if parent is None and enfants >= 2:
        articulations.add(u)


# --- composantes fortement connexes (graphe orienté) -----------------------------------


def composantes_fortement_connexes(graphe: dict[str, list[str]]) -> list[set[str]]:
    """Composantes fortement connexes, par l'algorithme de Tarjan.

    Un seul parcours en profondeur. Chaque nœud reçoit un `indice` (ordre de visite) et
    est empilé ; `bas[u]` est le plus petit indice d'un nœud encore sur la pile qu'on
    peut atteindre depuis u. Quand l'exploration de u est finie et que bas[u] = indice[u],
    u est la racine d'une composante : on dépile jusqu'à u.
    Complexité O(V + E).
    """
    indice: dict[str, int] = {}
    bas: dict[str, int] = {}
    pile: list[str] = []
    sur_la_pile: set[str] = set()
    composantes: list[set[str]] = []
    for racine in graphe:
        if racine not in indice:
            _visiter_tarjan(graphe, racine, indice, bas, pile, sur_la_pile, composantes)
    return composantes


def _visiter_tarjan(graphe: dict[str, list[str]], u: str, indice: dict[str, int],
                    bas: dict[str, int], pile: list[str], sur_la_pile: set[str],
                    composantes: list[set[str]]) -> None:
    """Parcours en profondeur récursif depuis u (sous-fonction de Tarjan)."""
    indice[u] = len(indice)
    bas[u] = indice[u]
    pile.append(u)
    sur_la_pile.add(u)
    for v in graphe[u]:
        if v not in indice:
            _visiter_tarjan(graphe, v, indice, bas, pile, sur_la_pile, composantes)
            bas[u] = min(bas[u], bas[v])
        elif v in sur_la_pile:
            bas[u] = min(bas[u], indice[v])
    if bas[u] == indice[u]:
        composante = set()
        while True:
            w = pile.pop()
            sur_la_pile.remove(w)
            composante.add(w)
            if w == u:
                break
        composantes.append(composante)


# --- graphe réduit et tri topologique --------------------------------------------------


def graphe_reduit(graphe: dict[str, list[str]],
                  composantes: list[set[str]]) -> dict[int, set[int]]:
    """Graphe réduit (condensation) : un sommet par composante fortement connexe, numéroté
    par sa position dans `composantes`, et un arc i → j s'il existe un arc d'un nœud de i
    vers un nœud de j (i ≠ j). Il est toujours sans circuit. Complexité O(V + E)."""
    numero = {}
    for i in range(len(composantes)):
        for noeud in composantes[i]:
            numero[noeud] = i
    reduit: dict[int, set[int]] = {}
    for i in range(len(composantes)):
        reduit[i] = set()
    for u in graphe:
        for v in graphe[u]:
            if numero[u] != numero[v]:
                reduit[numero[u]].add(numero[v])
    return reduit


def tri_topologique(graphe: dict[int, set[int]]) -> list[int] | None:
    """Ordre des sommets où chaque arc va vers un sommet placé après (algorithme de Kahn :
    on retire une à une les sources). Renvoie None si le graphe a un circuit.
    Complexité O(V + E)."""
    degre_entrant = {}
    for u in graphe:
        degre_entrant[u] = 0
    for u in graphe:
        for v in graphe[u]:
            degre_entrant[v] += 1
    file: deque[int] = deque()
    for u in graphe:
        if degre_entrant[u] == 0:
            file.append(u)
    ordre = []
    while len(file) > 0:
        u = file.popleft()
        ordre.append(u)
        for v in graphe[u]:
            degre_entrant[v] -= 1
            if degre_entrant[v] == 0:
                file.append(v)
    if len(ordre) < len(graphe):
        return None  # il reste des sommets sur un circuit
    return ordre
