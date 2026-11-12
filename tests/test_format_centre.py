"""Story 2.2 : modèle et format JSON d'un centre (consigne § 2.1 et § 2.3)."""

import json
from pathlib import Path

import pytest

from zc.chargement import charger_centre, ecrire_centre
from zc.format_centre import depuis_dict, vers_dict
from zc.modele import ErreurFormat

EXEMPLE = Path(__file__).resolve().parent / "donnees" / "exemple_consigne.json"


def exemple() -> dict:
    return json.loads(EXEMPLE.read_text(encoding="utf-8"))


def refuse(donnees: dict, motif: str) -> None:
    with pytest.raises(ErreurFormat, match=motif):
        depuis_dict(donnees)


# --- l'exemple de la consigne -----------------------------------------------------------

def test_exemple_de_la_consigne_se_charge() -> None:
    centre = charger_centre(EXEMPLE)
    assert [n.id for n in centre.noeuds] == ["S1", "C1", "E1"]
    assert centre.noeud("S1").taux_occupation() == pytest.approx(12 / 40)
    assert centre.noeud("E1").statut == "sortie"
    assert [(a.source, a.cible) for a in centre.aretes] == [("S1", "C1"), ("C1", "E1")]
    assert centre.aretes[0].longueur == 8.0 and centre.aretes[0].pmr is True


def test_exemple_se_reecrit_a_l_identique(tmp_path: Path) -> None:
    sortie = tmp_path / "centre.json"
    ecrire_centre(charger_centre(EXEMPLE), sortie)
    relu = json.loads(sortie.read_text(encoding="utf-8"))
    assert relu == exemple()
    # Mêmes types : 0 reste un entier, 8.0 reste un flottant.
    assert type(relu["noeuds"][0]["niveau_fumee"]) is int
    assert type(relu["aretes"][0]["longueur"]) is float
    # Champs dans l'ordre du format imposé.
    assert list(relu["noeuds"][0]) == list(exemple()["noeuds"][0])
    assert list(relu["aretes"][0]) == list(exemple()["aretes"][0])


def test_champs_facultatifs_conserves_et_accents_preserves(tmp_path: Path) -> None:
    donnees = exemple()
    donnees["noeuds"][0].update({"x": 10, "y": -2.5, "nom": "Librairie"})
    donnees["noeuds"][1]["statut"] = "enfumé"
    donnees["aretes"][0]["largeur"] = 1.8
    sortie = tmp_path / "centre.json"
    ecrire_centre(depuis_dict(donnees), sortie)
    assert "enfumé" in sortie.read_text(encoding="utf-8")
    assert json.loads(sortie.read_text(encoding="utf-8")) == donnees


def test_vers_dict_n_ajoute_pas_de_champ_facultatif_absent() -> None:
    assert vers_dict(depuis_dict(exemple())) == exemple()


# --- une règle de validation par test ---------------------------------------------------

def test_identifiants_uniques() -> None:
    donnees = exemple()
    donnees["noeuds"][1]["id"] = "S1"
    refuse(donnees, "double.*S1")


@pytest.mark.parametrize("champ", ["source", "cible"])
def test_extremites_existantes(champ: str) -> None:
    donnees = exemple()
    donnees["aretes"][0][champ] = "X9"
    refuse(donnees, "extrémité « X9 » inexistante")


def test_type_dans_son_ensemble() -> None:
    donnees = exemple()
    donnees["noeuds"][0]["type"] = "restaurant"
    refuse(donnees, "type.*restaurant")


def test_statut_noeud_dans_son_ensemble() -> None:
    donnees = exemple()
    donnees["noeuds"][0]["statut"] = "fermé"
    refuse(donnees, "statut.*fermé")


def test_statut_arete_dans_son_ensemble() -> None:
    donnees = exemple()
    donnees["aretes"][0]["statut"] = "sortie"  # statut de nœud, pas d'arête
    refuse(donnees, "statut.*sortie")


def test_sens_dans_son_ensemble() -> None:
    donnees = exemple()
    donnees["aretes"][0]["sens"] = "double"
    refuse(donnees, "sens.*double")


@pytest.mark.parametrize("occupation", [41, -1])
def test_occupation_entre_zero_et_capacite(occupation: int) -> None:
    donnees = exemple()
    donnees["noeuds"][0]["occupation"] = occupation
    refuse(donnees, "occupation")


def test_occupation_egale_a_la_capacite_acceptee() -> None:
    donnees = exemple()
    donnees["noeuds"][0]["occupation"] = 40
    assert depuis_dict(donnees).noeud("S1").taux_occupation() == 1.0


@pytest.mark.parametrize("fumee", [-0.1, 100.5])
def test_niveau_fumee_dans_0_100(fumee: float) -> None:
    donnees = exemple()
    donnees["noeuds"][0]["niveau_fumee"] = fumee
    refuse(donnees, "niveau_fumee")


@pytest.mark.parametrize("fumee", [0, 100, 37.5])
def test_niveau_fumee_bornes_acceptees(fumee: float) -> None:
    donnees = exemple()
    donnees["noeuds"][0]["niveau_fumee"] = fumee
    assert depuis_dict(donnees).noeud("S1").niveau_fumee == fumee


def test_capacite_noeud_positive() -> None:
    donnees = exemple()
    donnees["noeuds"][0]["capacite_max"] = 0
    refuse(donnees, "capacite_max")


@pytest.mark.parametrize("champ", ["capacite_max", "longueur"])
def test_longueur_et_capacite_arete_positives(champ: str) -> None:
    donnees = exemple()
    donnees["aretes"][0][champ] = 0
    refuse(donnees, "positives")


@pytest.mark.parametrize("liste", ["noeuds", "aretes"])
def test_champ_impose_manquant(liste: str) -> None:
    donnees = exemple()
    del donnees[liste][0]["statut"]
    refuse(donnees, "statut.*manquant")


def test_message_nomme_le_noeud_fautif() -> None:
    donnees = exemple()
    donnees["noeuds"][1]["occupation"] = 999
    refuse(donnees, "nœud « C1 »")


def test_erreur_de_fichier_porte_son_chemin(tmp_path: Path) -> None:
    fichier = tmp_path / "centre.json"
    donnees = exemple()
    donnees["noeuds"][0]["type"] = "kiosque"
    fichier.write_text(json.dumps(donnees), encoding="utf-8")
    with pytest.raises(ErreurFormat, match="centre.json.*kiosque"):
        charger_centre(fichier)
    with pytest.raises(ErreurFormat, match="illisible"):
        charger_centre(tmp_path / "absent.json")
    (tmp_path / "casse.json").write_text("{", encoding="utf-8")
    with pytest.raises(ErreurFormat, match="JSON"):
        charger_centre(tmp_path / "casse.json")
