"""Story 3.4 : distances d'évacuation, par un Dijkstra multi-sources sur le graphe inversé."""

import random
from pathlib import Path

import pytest

from tests.test_chemins import graphe_aleatoire
from zc.chargement import charger_zone
from zc.chemins import chemin_d_evacuation, dijkstra, distances_d_evacuation, inverser
from zc.modele import Arete
from zc.navigation import Arc, construire, graphe_du_centre

ZONE = Path(__file__).resolve().parent.parent / "donnees" / "zone.json"


def minimum_sortie_par_sortie(graphe: dict[str, list[Arc]],
                              sorties: list[str]) -> dict[str, float]:
    """Méthode lente de référence : depuis chaque nœud, un Dijkstra, puis la sortie la
    plus proche."""
    resultat = {}
    for noeud in graphe:
        distances, _ = dijkstra(graphe, noeud)
        meilleure = None
        for s in sorties:
            if s in distances and (meilleure is None or distances[s] < meilleure):
                meilleure = distances[s]
        if meilleure is not None:
            resultat[noeud] = meilleure
    return resultat


def verifier(graphe: dict[str, list[Arc]], sorties: list[str]) -> None:
    distances, suivants = distances_d_evacuation(graphe, sorties)
    attendues = minimum_sortie_par_sortie(graphe, [s for s in sorties if s in graphe])
    assert sorted(distances) == sorted(attendues)
    for noeud in attendues:
        assert distances[noeud] == pytest.approx(attendues[noeud]), noeud
        # Le chemin suivi mène bien à une sortie, pour le coût annoncé.
        chemin = chemin_d_evacuation(suivants, sorties, noeud)
        cout = 0.0
        for i in range(len(chemin) - 1):
            poids = []
            for arc in graphe[chemin[i]]:
                if arc.arrivee == chemin[i + 1]:
                    poids.append(arc.poids)
            assert poids, f"pas d'arc {chemin[i]} → {chemin[i + 1]}"
            cout += min(poids)
        assert cout == pytest.approx(distances[noeud])


def test_graphes_aleatoires() -> None:
    hasard = random.Random(34)
    for _ in range(50):
        identifiants, aretes = graphe_aleatoire(hasard)
        sorties = hasard.sample(identifiants, hasard.randint(1, min(3, len(identifiants))))
        graphe = construire(identifiants, aretes, set(), "encombre", beta=2.0)
        verifier(graphe, sorties)


@pytest.mark.parametrize("critere", ["court", "encombre", "pmr"])
def test_centres_reels(critere: str) -> None:
    zone = charger_zone(ZONE)
    for c in zone.centres:
        sorties = []
        for n in c.centre.noeuds:
            if n.type == "sortie":
                sorties.append(n.id)
        verifier(graphe_du_centre(c.centre, critere, beta=2.0), sorties)


def test_sortie_bloquee_ignoree_et_noeud_piege() -> None:
    # A – S1 (sortie) et B – S2 (sortie), B relié à A ; S1 bloquée.
    aretes = []
    for source, cible, longueur in [("A", "S1", 5.0), ("A", "B", 3.0), ("B", "S2", 4.0)]:
        aretes.append(Arete(source=source, cible=cible, capacite_max=2.0, longueur=longueur,
                            statut="libre", sens="bidirectionnel", pmr=True))
    aretes.append(Arete(source="P", cible="A", capacite_max=2.0, longueur=1.0,
                        statut="libre", sens="unique", pmr=True))  # sens unique P → A
    aretes.append(Arete(source="Q", cible="Q2", capacite_max=2.0, longueur=1.0,
                        statut="libre", sens="bidirectionnel", pmr=True))  # Q et Q2 isolés
    graphe = construire(["A", "B", "S1", "S2", "P", "Q", "Q2"], aretes, {"S1"}, "court")
    distances, suivants = distances_d_evacuation(graphe, ["S1", "S2"])
    assert distances["A"] == 7.0  # A → B → S2, puisque S1 est bloquée
    assert chemin_d_evacuation(suivants, ["S1", "S2"], "A") == ["A", "B", "S2"]
    assert distances["P"] == 8.0
    assert "Q" not in distances and "Q2" not in distances  # piégés : aucune sortie


def test_inverser_conserve_les_poids_et_retourne_les_arcs() -> None:
    a = Arete(source="X", cible="Y", capacite_max=2.0, longueur=6.0, statut="libre",
              sens="unique", pmr=True)
    inverse = inverser(construire(["X", "Y"], [a], set(), "court"))
    assert inverse["X"] == []
    assert len(inverse["Y"]) == 1
    assert inverse["Y"][0].arrivee == "X" and inverse["Y"][0].poids == 6.0
