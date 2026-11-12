"""Story 2.1 : chaque valeur physique est sourcée, et le chargement refuse les autres."""

import json
from pathlib import Path

import pytest

from zc.chargement import charger_parametres
from zc.modele import ErreurFormat
from zc.parametres import CLES, depuis_dict

FICHIER = Path(__file__).resolve().parent.parent / "donnees" / "parametres.json"


def valide() -> dict:
    donnees = {}
    for cle in CLES:
        donnees[cle] = {"valeur": 1.0, "unite": "u", "source": "Organisme, Titre",
                        "annee": 2000}
    return donnees


def test_fichier_du_projet_charge_avec_ses_valeurs() -> None:
    p = charger_parametres(FICHIER)
    assert p.vitesse_marche == 1.34
    assert p.vitesse_pmr == 0.69
    assert p.debit_specifique_max == 1.316
    assert p.densite_max == 5.4
    # Une personne en fauteuil manuel va moins vite qu'un piéton.
    assert p.vitesse_pmr < p.vitesse_marche


def test_chaque_valeur_du_projet_porte_source_et_annee() -> None:
    donnees = json.loads(FICHIER.read_text(encoding="utf-8"))
    for cle in donnees:
        assert donnees[cle]["source"].strip(), cle
        assert donnees[cle]["annee"] > 1900, cle


def test_chaque_source_figure_dans_le_rapport() -> None:
    sources = (FICHIER.parent.parent / "rapport" / "sources.md").read_text(encoding="utf-8")
    for cle in CLES:
        assert f"`{cle}`" in sources, f"{cle} absent de rapport/sources.md"


def test_dictionnaire_valide_accepte() -> None:
    assert depuis_dict(valide()).densite_max == 1.0


@pytest.mark.parametrize("source", [None, ""])
def test_source_absente_ou_vide_refusee(source: object) -> None:
    donnees = valide()
    donnees["vitesse_pmr"]["source"] = source
    with pytest.raises(ErreurFormat, match="vitesse_pmr.*source"):
        depuis_dict(donnees)


def test_cle_source_supprimee_refusee() -> None:
    donnees = valide()
    del donnees["densite_max"]["source"]
    with pytest.raises(ErreurFormat, match="densite_max.*source"):
        depuis_dict(donnees)


def test_annee_absente_refusee() -> None:
    donnees = valide()
    del donnees["vitesse_marche"]["annee"]
    with pytest.raises(ErreurFormat, match="vitesse_marche.*année"):
        depuis_dict(donnees)


@pytest.mark.parametrize("valeur", [0, -1.0])
def test_valeur_nulle_ou_negative_refusee(valeur: float) -> None:
    donnees = valide()
    donnees["vitesse_marche"]["valeur"] = valeur
    with pytest.raises(ErreurFormat, match="vitesse_marche.*positive"):
        depuis_dict(donnees)


def test_parametre_manquant_refuse() -> None:
    donnees = valide()
    del donnees["debit_specifique_max"]
    with pytest.raises(ErreurFormat, match="debit_specifique_max.*manquant"):
        depuis_dict(donnees)


def test_erreur_de_validation_porte_le_chemin(tmp_path: Path) -> None:
    donnees = valide()
    donnees["densite_max"]["source"] = ""
    fichier = tmp_path / "parametres.json"
    fichier.write_text(json.dumps(donnees), encoding="utf-8")
    with pytest.raises(ErreurFormat, match="parametres.json.*densite_max.*source"):
        charger_parametres(fichier)


def test_fichier_absent_ou_non_json(tmp_path: Path) -> None:
    with pytest.raises(ErreurFormat, match="illisible"):
        charger_parametres(tmp_path / "absent.json")
    casse = tmp_path / "casse.json"
    casse.write_text("{ pas du json", encoding="utf-8")
    with pytest.raises(ErreurFormat, match="JSON"):
        charger_parametres(casse)
