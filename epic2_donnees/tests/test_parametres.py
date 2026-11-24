"""Story 2.1 : le fichier des valeurs physiques se charge."""

from pathlib import Path

from epic2_donnees.moteur.chargement import charger_parametres

FICHIER_PARAMETRES = Path(__file__).resolve().parent.parent / "donnees" / "parametres.json"


def test_le_fichier_du_projet_se_charge() -> None:
    valeurs = charger_parametres(FICHIER_PARAMETRES)
    assert valeurs == {
        "vitesse_valide": 1.34,
        "vitesse_pmr": 0.67,
        "debit_par_metre": 1.37,
        "surface_par_personne": 0.25,
    }
