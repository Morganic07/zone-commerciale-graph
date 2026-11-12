"""Story 3.5 : connexité, points d'articulation, composantes fortement connexes, graphe
réduit et tri topologique, comparés à networkx sur 50 graphes aléatoires."""

import random

import networkx as nx

from zc.connexite import (
    composantes_connexes,
    composantes_fortement_connexes,
    graphe_reduit,
    points_d_articulation,
    tri_topologique,
)


def aleatoire_non_oriente(hasard: random.Random) -> tuple[dict[str, list[str]], nx.Graph]:
    """Graphe non orienté aléatoire, souvent peu dense pour avoir plusieurs composantes
    et des points d'articulation. Renvoie notre liste d'adjacence et le graphe networkx."""
    nombre = hasard.randint(1, 20)
    graphe: dict[str, list[str]] = {}
    g = nx.Graph()
    for i in range(nombre):
        graphe[f"N{i}"] = []
        g.add_node(f"N{i}")
    for _ in range(hasard.randint(0, 2 * nombre)):
        u = f"N{hasard.randrange(nombre)}"
        v = f"N{hasard.randrange(nombre)}"
        if u == v:
            continue
        graphe[u].append(v)
        graphe[v].append(u)
        g.add_edge(u, v)
    return graphe, g


def aleatoire_oriente(hasard: random.Random) -> tuple[dict[str, list[str]], nx.DiGraph]:
    nombre = hasard.randint(1, 20)
    graphe: dict[str, list[str]] = {}
    g = nx.DiGraph()
    for i in range(nombre):
        graphe[f"N{i}"] = []
        g.add_node(f"N{i}")
    for _ in range(hasard.randint(0, 3 * nombre)):
        u = f"N{hasard.randrange(nombre)}"
        v = f"N{hasard.randrange(nombre)}"
        graphe[u].append(v)  # les boucles u → u sont permises en orienté
        g.add_edge(u, v)
    return graphe, g


def en_ensembles(composantes: list[set[str]]) -> set[frozenset[str]]:
    resultat = set()
    for c in composantes:
        resultat.add(frozenset(c))
    return resultat


def test_composantes_connexes() -> None:
    hasard = random.Random(35)
    for _ in range(50):
        graphe, g = aleatoire_non_oriente(hasard)
        attendues = en_ensembles(list(nx.connected_components(g)))
        assert en_ensembles(composantes_connexes(graphe)) == attendues


def test_points_d_articulation() -> None:
    hasard = random.Random(36)
    for _ in range(50):
        graphe, g = aleatoire_non_oriente(hasard)
        assert points_d_articulation(graphe) == set(nx.articulation_points(g))


def test_composantes_fortement_connexes() -> None:
    hasard = random.Random(37)
    for _ in range(50):
        graphe, g = aleatoire_oriente(hasard)
        attendues = en_ensembles(list(nx.strongly_connected_components(g)))
        assert en_ensembles(composantes_fortement_connexes(graphe)) == attendues


def test_graphe_reduit_et_tri_topologique() -> None:
    hasard = random.Random(38)
    for _ in range(50):
        graphe, g = aleatoire_oriente(hasard)
        composantes = composantes_fortement_connexes(graphe)
        reduit = graphe_reduit(graphe, composantes)

        # Même graphe réduit que networkx, en désignant chaque sommet par sa composante.
        condensation = nx.condensation(g)
        membres = nx.get_node_attributes(condensation, "members")
        attendus = set()
        for i, j in condensation.edges():
            attendus.add((frozenset(membres[i]), frozenset(membres[j])))
        obtenus = set()
        for i in reduit:
            for j in reduit[i]:
                obtenus.add((frozenset(composantes[i]), frozenset(composantes[j])))
        assert obtenus == attendus

        # Le graphe réduit est sans circuit : le tri topologique existe et le respecte.
        ordre = tri_topologique(reduit)
        assert ordre is not None and sorted(ordre) == sorted(reduit)
        position = {}
        for rang in range(len(ordre)):
            position[ordre[rang]] = rang
        for i in reduit:
            for j in reduit[i]:
                assert position[i] < position[j]


def test_tri_topologique_detecte_un_circuit() -> None:
    assert tri_topologique({0: {1}, 1: {2}, 2: {0}}) is None
    assert tri_topologique({0: {1}, 1: set(), 2: {1}}) in ([0, 2, 1], [2, 0, 1])


def test_exemple_du_cours() -> None:
    # Chapitre 4 : 8 sommets A à H ; composantes {B, C, E, F, G}, {A}, {D}, {H}.
    graphe = {"A": ["B", "E"], "B": ["C", "E"], "C": ["F", "G"], "D": ["G", "H"],
              "E": ["F"], "F": ["B"], "G": ["F"], "H": ["G"]}
    attendues = {frozenset("BCEFG"), frozenset("A"), frozenset("D"), frozenset("H")}
    assert en_ensembles(composantes_fortement_connexes(graphe)) == attendues
