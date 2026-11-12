"""Story 3.2 : Dijkstra et les trois fonctions de coût, vérifiés contre networkx."""

import random
from pathlib import Path

import networkx as nx
import pytest

from zc.chargement import charger_zone
from zc.chemins import dijkstra, plus_court_chemin
from zc.modele import Arete
from zc.navigation import Arc, construire, graphe_de_la_zone

ZONE = Path(__file__).resolve().parent.parent / "donnees" / "zone.json"


def graphe_aleatoire(hasard: random.Random) -> tuple[list[str], list[Arete]]:
    """Graphe aléatoire : sens uniques, arêtes non PMR, arêtes parallèles et taux
    d'occupation variés, pour exercer tous les cas."""
    nombre = hasard.randint(2, 15)
    identifiants = []
    for i in range(nombre):
        identifiants.append(f"N{i}")
    aretes = []
    for _ in range(hasard.randint(1, 3 * nombre)):
        source, cible = hasard.sample(identifiants, 2)
        aretes.append(Arete(
            source=source, cible=cible, capacite_max=2.0,
            longueur=round(hasard.uniform(1, 50), 1),
            statut="libre",
            sens=hasard.choice(["bidirectionnel", "unique"]),
            pmr=hasard.random() < 0.8,
            taux=hasard.random(),
        ))
    return identifiants, aretes


def vers_networkx(graphe: dict[str, list[Arc]]) -> nx.DiGraph:
    """Même graphe pour networkx. Entre deux nœuds, on garde l'arc le moins cher
    (un DiGraph ne garde qu'un arc par paire)."""
    g = nx.DiGraph()
    for noeud in graphe:
        g.add_node(noeud)
    for noeud in graphe:
        for arc in graphe[noeud]:
            if not g.has_edge(arc.depart, arc.arrivee) or \
                    arc.poids < g[arc.depart][arc.arrivee]["poids"]:
                g.add_edge(arc.depart, arc.arrivee, poids=arc.poids)
    return g


def verifier_contre_networkx(graphe: dict[str, list[Arc]]) -> None:
    g = vers_networkx(graphe)
    for depart in graphe:
        distances, _ = dijkstra(graphe, depart)
        attendues = nx.single_source_dijkstra_path_length(g, depart, weight="poids")
        assert sorted(distances) == sorted(attendues), depart
        for noeud in attendues:
            assert distances[noeud] == pytest.approx(attendues[noeud]), (depart, noeud)


def cout_du_chemin(graphe: dict[str, list[Arc]], chemin: list[str]) -> float:
    """Coût d'un chemin, en vérifiant au passage que chaque pas est un arc existant."""
    total = 0.0
    for i in range(len(chemin) - 1):
        poids_possibles = []
        for arc in graphe[chemin[i]]:
            if arc.arrivee == chemin[i + 1]:
                poids_possibles.append(arc.poids)
        assert poids_possibles, f"pas d'arc {chemin[i]} → {chemin[i + 1]}"
        total += min(poids_possibles)
    return total


# --- contre networkx -------------------------------------------------------------------

@pytest.mark.parametrize("critere", ["court", "encombre", "pmr"])
def test_50_graphes_aleatoires(critere: str) -> None:
    hasard = random.Random(2026)
    for _ in range(50):
        identifiants, aretes = graphe_aleatoire(hasard)
        graphe = construire(identifiants, aretes, set(), critere, beta=2.0)
        verifier_contre_networkx(graphe)


@pytest.mark.parametrize("critere", ["court", "encombre", "pmr"])
def test_zone_reelle(critere: str) -> None:
    zone = charger_zone(ZONE)
    hasard = random.Random(7)
    for c in zone.centres:
        for a in c.centre.aretes:
            a.taux = hasard.random()
    for a in zone.connexions:
        a.taux = hasard.random()
    verifier_contre_networkx(graphe_de_la_zone(zone, critere, beta=3.0))


# --- chemin reconstruit ----------------------------------------------------------------

def test_chemin_reconstruit_coherent_avec_la_distance() -> None:
    hasard = random.Random(11)
    for _ in range(50):
        identifiants, aretes = graphe_aleatoire(hasard)
        graphe = construire(identifiants, aretes, set(), "encombre", beta=2.0)
        depart, arrivee = identifiants[0], identifiants[-1]
        resultat = plus_court_chemin(graphe, depart, arrivee)
        if resultat is None:
            assert not nx.has_path(vers_networkx(graphe), depart, arrivee)
            continue
        cout, chemin = resultat
        assert chemin[0] == depart and chemin[-1] == arrivee
        assert cout_du_chemin(graphe, chemin) == pytest.approx(cout)


def test_chemin_vers_soi_meme() -> None:
    graphe = construire(["A"], [], set(), "court")
    assert plus_court_chemin(graphe, "A", "A") == (0.0, ["A"])


# --- β = 0 et chemins impossibles ------------------------------------------------------

def test_beta_nul_redonne_le_plus_court_chemin() -> None:
    zone = charger_zone(ZONE)
    for c in zone.centres:
        for a in c.centre.aretes:
            a.taux = 0.9
    court = graphe_de_la_zone(zone, "court")
    encombre = graphe_de_la_zone(zone, "encombre", beta=0.0)
    for depart in ["P1", "T1", "Q1"]:
        assert dijkstra(court, depart)[0] == dijkstra(encombre, depart)[0]


def test_destination_inaccessible() -> None:
    a = Arete(source="A", cible="B", capacite_max=2.0, longueur=5.0, statut="libre",
              sens="unique", pmr=True)
    graphe = construire(["A", "B", "C"], [a], set(), "court")
    assert plus_court_chemin(graphe, "B", "A") is None  # sens interdit
    assert plus_court_chemin(graphe, "A", "C") is None  # aucun arc vers C
    assert plus_court_chemin(graphe, "A", "B") == (5.0, ["A", "B"])


def test_extremite_bloquee() -> None:
    a = Arete(source="A", cible="B", capacite_max=2.0, longueur=5.0, statut="libre",
              sens="bidirectionnel", pmr=True)
    graphe = construire(["A", "B"], [a], {"B"}, "court")
    assert plus_court_chemin(graphe, "A", "B") is None
    assert plus_court_chemin(graphe, "B", "A") is None


def test_le_moins_encombre_evite_la_foule() -> None:
    # Deux routes de A à C : directe (10 m, bondée) ou par B (15 m, vide).
    directe = Arete(source="A", cible="C", capacite_max=2.0, longueur=10.0,
                    statut="libre", sens="bidirectionnel", pmr=True, taux=1.0)
    ab = Arete(source="A", cible="B", capacite_max=2.0, longueur=7.5, statut="libre",
               sens="bidirectionnel", pmr=True)
    bc = Arete(source="B", cible="C", capacite_max=2.0, longueur=7.5, statut="libre",
               sens="bidirectionnel", pmr=True)
    aretes = [directe, ab, bc]
    court = plus_court_chemin(construire(["A", "B", "C"], aretes, set(), "court"), "A", "C")
    encombre = plus_court_chemin(construire(["A", "B", "C"], aretes, set(), "encombre",
                                            beta=1.0), "A", "C")
    assert court == (10.0, ["A", "C"])
    assert encombre == (15.0, ["A", "B", "C"])  # 10 × (1 + 1 × 1) = 20 > 15
