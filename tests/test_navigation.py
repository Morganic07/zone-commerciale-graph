"""Story 3.1 : graphe de navigation (sens, filtre PMR, blocages, poids selon le critère)."""

from pathlib import Path

import pytest

from zc.chargement import charger_centre, charger_zone
from zc.modele import Arete
from zc.navigation import Arc, construire, graphe_de_la_zone, graphe_du_centre

ZONE = Path(__file__).resolve().parent.parent / "donnees" / "zone.json"
EXEMPLE = Path(__file__).resolve().parent / "donnees" / "exemple_consigne.json"


def arete(source: str, cible: str, sens: str = "bidirectionnel", pmr: bool = True,
          statut: str = "libre", longueur: float = 10.0, taux: float = 0.0) -> Arete:
    return Arete(source=source, cible=cible, capacite_max=2.0, longueur=longueur,
                 statut=statut, sens=sens, pmr=pmr, taux=taux)


def arrivees(graphe: dict[str, list[Arc]], depart: str) -> list[str]:
    resultat = []
    for arc in graphe[depart]:
        resultat.append(arc.arrivee)
    return sorted(resultat)


def nombre_d_arcs(graphe: dict[str, list[Arc]]) -> int:
    total = 0
    for depart in graphe:
        total += len(graphe[depart])
    return total


# --- sens ------------------------------------------------------------------------------

def test_arete_bidirectionnelle_donne_deux_arcs() -> None:
    g = construire(["A", "B"], [arete("A", "B")], set(), "court")
    assert arrivees(g, "A") == ["B"]
    assert arrivees(g, "B") == ["A"]
    assert nombre_d_arcs(g) == 2


def test_arete_a_sens_unique_donne_un_seul_arc() -> None:
    g = construire(["A", "B"], [arete("A", "B", sens="unique")], set(), "court")
    assert arrivees(g, "A") == ["B"]
    assert arrivees(g, "B") == []
    assert nombre_d_arcs(g) == 1


# --- filtre PMR ------------------------------------------------------------------------

def test_vue_pmr_sans_arete_non_pmr() -> None:
    aretes = [arete("A", "B", pmr=False), arete("B", "C")]
    g = construire(["A", "B", "C"], aretes, set(), "pmr")
    assert arrivees(g, "A") == []
    assert arrivees(g, "B") == ["C"]
    # Les autres critères gardent l'arête non PMR.
    assert arrivees(construire(["A", "B", "C"], aretes, set(), "court"), "A") == ["B"]


# --- blocages --------------------------------------------------------------------------

def test_noeud_bloque_retire_avec_ses_arcs() -> None:
    aretes = [arete("A", "B"), arete("B", "C"), arete("A", "C")]
    g = construire(["A", "B", "C"], aretes, {"B"}, "court")
    assert "B" not in g
    assert arrivees(g, "A") == ["C"]
    assert arrivees(g, "C") == ["A"]


def test_arete_bloquee_retiree() -> None:
    aretes = [arete("A", "B", statut="bloqué"), arete("A", "C", statut="enfumé")]
    g = construire(["A", "B", "C"], aretes, set(), "court")
    assert arrivees(g, "A") == ["C"]  # enfumée mais pas bloquée : elle reste


# --- poids -----------------------------------------------------------------------------

def test_poids_selon_le_critere() -> None:
    a = arete("A", "B", longueur=20.0, taux=0.5)
    assert construire(["A", "B"], [a], set(), "court")["A"][0].poids == 20.0
    assert construire(["A", "B"], [a], set(), "pmr")["A"][0].poids == 20.0
    # Longueur pénalisée : 20 × (1 + 2 × 0,5) = 40.
    assert construire(["A", "B"], [a], set(), "encombre", beta=2.0)["A"][0].poids == 40.0
    # β = 0 : on retrouve le plus court chemin.
    assert construire(["A", "B"], [a], set(), "encombre", beta=0.0)["A"][0].poids == 20.0


def test_critere_inconnu_refuse() -> None:
    with pytest.raises(ValueError, match="critère"):
        construire(["A"], [], set(), "rapide")


def test_beta_negatif_refuse() -> None:
    with pytest.raises(ValueError, match="β"):
        construire(["A", "B"], [arete("A", "B", taux=0.9)], set(), "encombre", beta=-2.0)


# --- un seul centre --------------------------------------------------------------------

def test_graphe_du_centre() -> None:
    centre = charger_centre(EXEMPLE)  # S1 – C1 – E1, deux arêtes bidirectionnelles
    g = graphe_du_centre(centre, "court")
    assert sorted(g) == ["C1", "E1", "S1"]
    assert arrivees(g, "C1") == ["E1", "S1"]
    assert nombre_d_arcs(g) == 4

    centre.noeud("C1").statut = "bloqué"
    g = graphe_du_centre(centre, "court")
    assert sorted(g) == ["E1", "S1"]
    assert nombre_d_arcs(g) == 0


# --- sur la zone réelle ----------------------------------------------------------------

def test_zone_complete() -> None:
    zone = charger_zone(ZONE)
    g = graphe_de_la_zone(zone, "court")

    # Un nœud par nœud de centre et par source.
    attendus = len(zone.sources)
    aretes = list(zone.connexions)
    for c in zone.centres:
        attendus += len(c.centre.noeuds)
        aretes += c.centre.aretes
    assert len(g) == attendus

    # Deux arcs par arête bidirectionnelle, un par arête à sens unique.
    arcs = 0
    for a in aretes:
        if a.sens == "bidirectionnel":
            arcs += 2
        else:
            arcs += 1
    assert nombre_d_arcs(g) == arcs

    # Vue PMR : aucun arc ne vient d'une arête non PMR.
    pmr = graphe_de_la_zone(zone, "pmr")
    for depart in pmr:
        for arc in pmr[depart]:
            assert arc.arete.pmr


def test_zone_avec_un_noeud_bloque() -> None:
    zone = charger_zone(ZONE)
    sortie = zone.centres[0].centre.noeuds[0]
    sortie.statut = "bloqué"
    g = graphe_de_la_zone(zone, "court")
    assert sortie.id not in g
    for depart in g:
        for arc in g[depart]:
            assert arc.arrivee != sortie.id
