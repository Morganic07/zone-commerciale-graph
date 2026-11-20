"""Story 2.3 : chargement du réseau, préfixage, rattachement des tunnels, vue macro."""

from pathlib import Path

from moteur.chargement import charger_reseau
from moteur.modele import macro_noeud, vue_macro

RESEAU = Path(__file__).resolve().parent / "donnees" / "reseau_test.json"


def test_le_reseau_se_charge() -> None:
    reseau = charger_reseau(RESEAU)
    assert len(reseau.stations) == 2
    assert reseau.stations[1].id == "B"
    assert reseau.stations[1].x == 400
    assert len(reseau.sources) == 2
    assert reseau.sources[0].id == "P1"
    assert reseau.sources[0].type == "spatioport"
    assert len(reseau.connexions) == 3
    assert reseau.connexions[1].pmr is False


def test_noeuds_et_aretes_prefixes_par_station() -> None:
    reseau = charger_reseau(RESEAU)
    station_a = reseau.stations[0].station
    station_b = reseau.stations[1].station
    ids_a = []
    for noeud in station_a.noeuds:
        ids_a.append(noeud.id)
    assert ids_a == ["A:S1", "A:C1", "A:E1"]
    assert station_a.aretes[0].source == "A:S1"
    assert station_a.aretes[0].cible == "A:C1"
    # Même fichier de plan, mais des nœuds distincts, préfixés par B.
    assert station_b.noeuds[0].id == "B:S1"
    assert station_b.aretes[1].cible == "B:E1"


def test_tunnels_rattaches_aux_sorties() -> None:
    reseau = charger_reseau(RESEAU)
    sorties = []
    for station_du_reseau in reseau.stations:
        for noeud in station_du_reseau.station.noeuds:
            if noeud.type == "sortie":
                sorties.append(noeud.id)
    sources = []
    for source in reseau.sources:
        sources.append(source.id)
    for connexion in reseau.connexions:
        assert connexion.source in sorties or connexion.source in sources
        assert connexion.cible in sorties or connexion.cible in sources


def test_macro_noeud() -> None:
    assert macro_noeud("A:SAS1") == "A"
    assert macro_noeud("P1") == "P1"


def test_vue_macro_un_sommet_par_station_et_par_source() -> None:
    sommets, aretes = vue_macro(charger_reseau(RESEAU))
    assert sommets == ["A", "B", "P1", "H1"]
    assert aretes == [("P1", "A"), ("A", "B"), ("H1", "B")]
