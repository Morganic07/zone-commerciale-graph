"""Story 2.1 : chaque valeur physique est sourcée, et le chargement refuse les autres."""

import copy
import json
import math
from pathlib import Path
from typing import Any

import pytest

from zc.chargement import charger_parametres
from zc.parametres import UNITES, ErreurParametres, depuis_dict

FICHIER = Path(__file__).resolve().parent.parent / "donnees" / "parametres.json"


def valide() -> dict[str, Any]:
    return {
        cle: {"valeur": 1.0, "unite": unite, "source": "Organisme, Titre", "annee": 2000}
        for cle, unite in UNITES.items()
    }


def test_fichier_du_projet_charge_avec_ses_valeurs() -> None:
    p = charger_parametres(FICHIER)
    assert p.vitesse_marche == 1.34
    assert p.vitesse_pmr == 0.69
    assert p.debit_specifique_max == 1.316
    assert p.densite_max == 5.4
    # Cohérence physique : une personne en fauteuil manuel va moins vite qu'un piéton.
    assert p.vitesse_pmr < p.vitesse_marche


def test_chaque_valeur_du_projet_porte_source_et_annee() -> None:
    donnees = json.loads(FICHIER.read_text(encoding="utf-8"))
    for cle, entree in donnees.items():
        assert entree["source"].strip(), cle
        assert 1900 <= entree["annee"] <= 2100, cle


def test_chaque_source_figure_dans_le_rapport() -> None:
    sources = (FICHIER.parent.parent / "rapport" / "sources.md").read_text(encoding="utf-8")
    for cle in UNITES:
        assert f"`{cle}`" in sources, f"{cle} absent de rapport/sources.md"


def test_dictionnaire_valide_accepte() -> None:
    assert depuis_dict(valide()).densite_max == 1.0


@pytest.mark.parametrize("source", [None, "", "   ", 42])
def test_source_absente_ou_vide_refusee(source: object) -> None:
    donnees = valide()
    donnees["vitesse_pmr"]["source"] = source
    with pytest.raises(ErreurParametres, match="vitesse_pmr.*source"):
        depuis_dict(donnees)


def test_cle_source_supprimee_refusee() -> None:
    donnees = valide()
    del donnees["densite_max"]["source"]
    with pytest.raises(ErreurParametres, match="densite_max.*source"):
        depuis_dict(donnees)


@pytest.mark.parametrize("annee", [None, "1993", 1899, 2101, True, 1993.0])
def test_annee_absente_ou_invalide_refusee(annee: object) -> None:
    donnees = valide()
    donnees["vitesse_marche"]["annee"] = annee
    with pytest.raises(ErreurParametres, match="vitesse_marche.*année"):
        depuis_dict(donnees)


@pytest.mark.parametrize("valeur", [None, "1.34", True, 0, -1.0, math.nan, math.inf])
def test_valeur_non_positive_ou_non_numerique_refusee(valeur: object) -> None:
    donnees = valide()
    donnees["vitesse_marche"]["valeur"] = valeur
    with pytest.raises(ErreurParametres, match="vitesse_marche"):
        depuis_dict(donnees)


def test_unite_inattendue_refusee() -> None:
    donnees = valide()
    donnees["vitesse_marche"]["unite"] = "km/h"
    with pytest.raises(ErreurParametres, match="vitesse_marche.*m/s"):
        depuis_dict(donnees)


def test_parametre_manquant_refuse() -> None:
    donnees = valide()
    del donnees["debit_specifique_max"]
    with pytest.raises(ErreurParametres, match="manquants.*debit_specifique_max"):
        depuis_dict(donnees)


def test_parametre_inconnu_refuse() -> None:
    donnees = valide()
    donnees["vitese_marche"] = copy.deepcopy(donnees["vitesse_marche"])  # faute de frappe
    with pytest.raises(ErreurParametres, match="inconnus.*vitese_marche"):
        depuis_dict(donnees)


@pytest.mark.parametrize("donnees", [[], "texte", None, {"vitesse_marche": 1.34}])
def test_structure_invalide_refusee(donnees: object) -> None:
    with pytest.raises(ErreurParametres):
        depuis_dict(donnees)


def test_entree_qui_n_est_pas_un_objet_refusee() -> None:
    donnees = valide()
    donnees["vitesse_pmr"] = 0.69
    with pytest.raises(ErreurParametres, match="vitesse_pmr.*objet"):
        depuis_dict(donnees)


def test_erreur_de_validation_porte_le_chemin(tmp_path: Path) -> None:
    donnees = valide()
    donnees["densite_max"]["source"] = ""
    fichier = tmp_path / "parametres.json"
    fichier.write_text(json.dumps(donnees), encoding="utf-8")
    with pytest.raises(ErreurParametres, match="parametres.json.*densite_max.*source"):
        charger_parametres(fichier)


def test_fichier_absent_ou_non_json(tmp_path: Path) -> None:
    with pytest.raises(ErreurParametres, match="illisible"):
        charger_parametres(tmp_path / "absent.json")
    casse = tmp_path / "casse.json"
    casse.write_text("{ pas du json", encoding="utf-8")
    with pytest.raises(ErreurParametres, match="JSON"):
        charger_parametres(casse)
