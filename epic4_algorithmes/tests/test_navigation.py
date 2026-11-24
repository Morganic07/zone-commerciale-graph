"""Story 4.1 : graphe de navigation (sens, filtre PMR, éléments bloqués, coût)."""

from pathlib import Path

import pytest

from epic2_donnees.moteur.chargement import charger_reseau
from epic2_donnees.moteur.modele import Arete, Noeud, Reseau, Station, StationDuReseau
from epic4_algorithmes.moteur.navigation import graphe_de_navigation

RACINE = Path(__file__).resolve().parent.parent.parent
RESEAU = RACINE / "epic2_donnees" / "donnees" / "reseau.json"


def noeud(identifiant: str, statut: str = "libre") -> Noeud:
    return Noeud(identifiant, "carrefour", 10, 0, True, 0, statut)


def arete(source: str, cible: str, sens: str = "bidirectionnel", pmr: bool = True,
          statut: str = "libre", longueur: float = 10.0) -> Arete:
    return Arete(source, cible, 1.0, longueur, statut, sens, pmr)


def reseau_de(noeuds: list[Noeud], aretes: list[Arete]) -> Reseau:
    """Un réseau d'une seule station, sans tunnel, pour les essais."""
    station = StationDuReseau(id="T", station=Station(noeuds, aretes), fichier="essai.json")
    return Reseau(stations=[station], sources=[], connexions=[])


def voisins_de(graphe: dict[str, list[tuple[str, float]]], identifiant: str) -> list[str]:
    resultat = []
    for voisin, _ in graphe[identifiant]:
        resultat.append(voisin)
    return resultat


def nombre_d_arcs(graphe: dict[str, list[tuple[str, float]]]) -> int:
    total = 0
    for identifiant in graphe:
        total = total + len(graphe[identifiant])
    return total


# --- sens ---------------------------------------------------------------------------------


def test_arete_bidirectionnelle_donne_deux_arcs() -> None:
    graphe = graphe_de_navigation(reseau_de([noeud("U"), noeud("V")], [arete("U", "V")]),
                                  False, 0.0, {})
    assert voisins_de(graphe, "U") == ["V"]
    assert voisins_de(graphe, "V") == ["U"]
    assert nombre_d_arcs(graphe) == 2


def test_arete_unique_donne_un_seul_arc() -> None:
    graphe = graphe_de_navigation(
        reseau_de([noeud("U"), noeud("V")], [arete("U", "V", sens="unique")]), False, 0.0, {}
    )
    assert voisins_de(graphe, "U") == ["V"]
    assert voisins_de(graphe, "V") == []
    assert nombre_d_arcs(graphe) == 1


# --- fauteuil roulant ---------------------------------------------------------------------


def test_vue_pmr_sans_arete_non_pmr() -> None:
    reseau = reseau_de([noeud("U"), noeud("V"), noeud("W")],
                       [arete("U", "V", pmr=False), arete("V", "W")])
    tous = graphe_de_navigation(reseau, False, 0.0, {})
    fauteuil = graphe_de_navigation(reseau, True, 0.0, {})
    assert "V" in voisins_de(tous, "U")
    assert voisins_de(fauteuil, "U") == []
    assert voisins_de(fauteuil, "V") == ["W"]


def test_reseau_complet_en_fauteuil() -> None:
    reseau = charger_reseau(RESEAU)
    graphe = graphe_de_navigation(reseau, True, 0.0, {})
    # Toutes les arêtes sont bidirectionnelles : deux arcs par arête praticable en fauteuil.
    praticables = 0
    non_pmr = []
    toutes = list(reseau.connexions)
    for station_du_reseau in reseau.stations:
        toutes = toutes + station_du_reseau.station.aretes
    for a in toutes:
        if a.pmr:
            praticables = praticables + 1
        else:
            non_pmr.append((a.source, a.cible))
    assert nombre_d_arcs(graphe) == 2 * praticables
    for depart, arrivee in non_pmr:
        assert arrivee not in voisins_de(graphe, depart)
        assert depart not in voisins_de(graphe, arrivee)


def test_les_tunnels_relient_les_stations() -> None:
    graphe = graphe_de_navigation(charger_reseau(RESEAU), False, 0.0, {})
    assert "B:B1" in voisins_de(graphe, "A:A12")
    assert "A:A12" in voisins_de(graphe, "B:B1")


# --- éléments bloqués ---------------------------------------------------------------------


def test_arete_bloquee_retiree() -> None:
    graphe = graphe_de_navigation(
        reseau_de([noeud("U"), noeud("V")], [arete("U", "V", statut="bloqué")]), False, 0.0, {}
    )
    assert nombre_d_arcs(graphe) == 0


def test_noeud_bloque_retire_avec_ses_aretes() -> None:
    reseau = reseau_de([noeud("U"), noeud("V", statut="bloqué"), noeud("W")],
                       [arete("U", "V"), arete("V", "W"), arete("U", "W")])
    graphe = graphe_de_navigation(reseau, False, 0.0, {})
    assert "V" not in graphe
    assert voisins_de(graphe, "U") == ["W"]
    assert voisins_de(graphe, "W") == ["U"]


def test_arete_enfumee_reste_praticable() -> None:
    # Seul « bloqué » retire un élément : une arête enfumée reste dans le graphe.
    graphe = graphe_de_navigation(
        reseau_de([noeud("U"), noeud("V")], [arete("U", "V", statut="enfumé")]), False, 0.0, {}
    )
    assert nombre_d_arcs(graphe) == 2


# --- coût ---------------------------------------------------------------------------------


def test_beta_nul_donne_la_longueur() -> None:
    reseau = reseau_de([noeud("U"), noeud("V")], [arete("U", "V", longueur=12.0)])
    graphe = graphe_de_navigation(reseau, False, 0.0, {("U", "V"): 0.9})
    assert graphe["U"] == [("V", 12.0)]


def test_moins_encombre_penalise_l_occupation() -> None:
    # longueur × (1 + β·τ) = 12 × (1 + 2 × 0,5) = 24, dans les deux sens.
    reseau = reseau_de([noeud("U"), noeud("V")], [arete("U", "V", longueur=12.0)])
    graphe = graphe_de_navigation(reseau, False, 2.0, {("U", "V"): 0.5})
    voisin_de_u, cout_aller = graphe["U"][0]
    voisin_de_v, cout_retour = graphe["V"][0]
    assert voisin_de_u == "V"
    assert voisin_de_v == "U"
    assert cout_aller == pytest.approx(24.0)
    assert cout_retour == pytest.approx(24.0)


def test_arete_absente_des_taux_compte_comme_vide() -> None:
    reseau = reseau_de([noeud("U"), noeud("V")], [arete("U", "V", longueur=12.0)])
    graphe = graphe_de_navigation(reseau, False, 2.0, {})
    assert graphe["U"] == [("V", 12.0)]
