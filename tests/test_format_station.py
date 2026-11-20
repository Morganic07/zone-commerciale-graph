"""Story 2.2 : modèle et format JSON d'une station (consigne § 2.1 et § 2.3)."""

import json
from pathlib import Path
from typing import Any

from moteur.chargement import (
    charger_station,
    ecrire_station,
    lire_station,
    station_en_dictionnaire,
)

EXEMPLE = Path(__file__).resolve().parent / "donnees" / "exemple_consigne.json"


def exemple() -> dict[str, Any]:
    """L'exemple minimal imposé par la consigne (§ 2.3), relu à chaque appel."""
    with open(EXEMPLE, encoding="utf-8") as fichier:
        donnees: dict[str, Any] = json.load(fichier)
    return donnees


def test_exemple_de_la_consigne_se_charge() -> None:
    station = charger_station(EXEMPLE)
    assert len(station.noeuds) == 3
    assert station.noeuds[0].id == "S1"
    assert station.noeuds[0].occupation == 12
    assert station.noeuds[2].statut == "sortie"
    assert len(station.aretes) == 2
    assert station.aretes[0].source == "S1"
    assert station.aretes[0].cible == "C1"
    assert station.aretes[0].longueur == 8.0
    assert station.aretes[0].pmr is True


def test_exemple_se_reecrit_a_l_identique(tmp_path: Path) -> None:
    sortie = tmp_path / "station.json"
    ecrire_station(charger_station(EXEMPLE), sortie)
    with open(sortie, encoding="utf-8") as fichier:
        relu = json.load(fichier)
    assert relu == exemple()
    # Mêmes types : 0 reste un entier, 8.0 reste un flottant.
    assert type(relu["noeuds"][0]["niveau_fumee"]) is int
    assert type(relu["aretes"][0]["longueur"]) is float
    # Champs dans l'ordre du format imposé.
    assert list(relu["noeuds"][0]) == list(exemple()["noeuds"][0])
    assert list(relu["aretes"][0]) == list(exemple()["aretes"][0])


def test_champs_facultatifs_conserves_et_accents_preserves(tmp_path: Path) -> None:
    donnees = exemple()
    donnees["noeuds"][0]["x"] = 10
    donnees["noeuds"][0]["y"] = -2.5
    donnees["noeuds"][0]["nom"] = "Laboratoire Columbus"
    donnees["noeuds"][1]["statut"] = "enfumé"
    donnees["aretes"][0]["largeur"] = 1.8
    sortie = tmp_path / "station.json"
    ecrire_station(lire_station(donnees), sortie)
    texte = sortie.read_text(encoding="utf-8")
    assert "enfumé" in texte
    assert json.loads(texte) == donnees


def test_aucun_champ_facultatif_ajoute() -> None:
    assert station_en_dictionnaire(lire_station(exemple())) == exemple()
