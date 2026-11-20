"""Story 2.1 : chaque valeur physique a une source datée ou une hypothèse expliquée."""

import json
from pathlib import Path
from typing import Any

import pytest

from moteur.chargement import charger_parametres
from moteur.modele import ErreurFormat

FICHIER_PARAMETRES = Path(__file__).resolve().parent.parent / "donnees" / "parametres.json"


def ecrire(dossier: Path, parametre: dict[str, Any]) -> Path:
    """Écrit un fichier de paramètres qui ne contient que `parametre`, sous le nom « essai »."""
    chemin = dossier / "parametres.json"
    chemin.write_text(json.dumps({"essai": parametre}), encoding="utf-8")
    return chemin


def parametre(source: str, annee: int | None, hypothese: str) -> dict[str, Any]:
    return {
        "description": "paramètre d'essai",
        "valeur": 1.0,
        "unite": "m/s",
        "source": source,
        "annee": annee,
        "hypothese": hypothese,
    }


def test_le_fichier_du_projet_se_charge() -> None:
    valeurs = charger_parametres(FICHIER_PARAMETRES)
    attendus = {"vitesse_valide", "vitesse_pmr", "debit_par_metre", "surface_par_personne"}
    assert set(valeurs) == attendus
    for nom in valeurs:
        assert valeurs[nom] > 0, nom


def test_source_avec_annee_acceptee(tmp_path: Path) -> None:
    chemin = ecrire(tmp_path, parametre("Weidmann, ETH Zürich", 1993, ""))
    assert charger_parametres(chemin) == {"essai": 1.0}


def test_hypothese_seule_acceptee(tmp_path: Path) -> None:
    chemin = ecrire(tmp_path, parametre("", None, "moitié de la vitesse valide"))
    assert charger_parametres(chemin) == {"essai": 1.0}


@pytest.mark.parametrize(
    "source, annee, hypothese",
    [
        ("", None, ""),  # ni source ni hypothèse
        ("Weidmann, ETH Zürich", None, ""),  # source sans année
        ("", 1993, ""),  # année sans source
        ("   ", 1993, "  "),  # que des espaces
    ],
)
def test_valeur_non_justifiee_refusee(
    tmp_path: Path, source: str, annee: int | None, hypothese: str
) -> None:
    chemin = ecrire(tmp_path, parametre(source, annee, hypothese))
    with pytest.raises(ErreurFormat, match="essai"):
        charger_parametres(chemin)


def test_valeur_manquante_refusee(tmp_path: Path) -> None:
    donnee = parametre("Weidmann, ETH Zürich", 1993, "")
    donnee["valeur"] = None
    chemin = ecrire(tmp_path, donnee)
    with pytest.raises(ErreurFormat, match="essai"):
        charger_parametres(chemin)
