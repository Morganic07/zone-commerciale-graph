"""Story 2.3 : format de la zone, préfixage des identifiants, rattachement des
connexions aux sorties, vue macro (PLAN.md § 2.2)."""

import json
from pathlib import Path
from typing import Any

import pytest

from zc.chargement import charger_centre, charger_zone
from zc.format_zone import depuis_dict, prefixer
from zc.modele import Centre
from zc.validation import ErreurFormat

DONNEES = Path(__file__).resolve().parent / "donnees"
ZONE = DONNEES / "zone_test.json"


def zone_brute() -> dict[str, Any]:
    donnees: dict[str, Any] = json.loads(ZONE.read_text(encoding="utf-8"))
    return donnees


def charger(fichier: str) -> Centre:
    return charger_centre(DONNEES / fichier)


def refuse(donnees: object, motif: str) -> None:
    with pytest.raises(ErreurFormat, match=motif):
        depuis_dict(donnees, charger)


# --- la zone de test se charge ----------------------------------------------------------

def test_zone_de_test_se_charge() -> None:
    zone = charger_zone(ZONE)
    assert [c.id for c in zone.centres] == ["A", "B"]
    assert [(s.id, s.type) for s in zone.sources] == [
        ("P1", "parking"), ("T1", "station"), ("Q1", "quartier")]
    assert len(zone.connexions) == 4
    assert zone.connexions[1].largeur == 3.0 and zone.connexions[2].sens == "unique"


def test_identifiants_prefixes_par_centre() -> None:
    zone = charger_zone(ZONE)
    a, b = zone.centres
    assert [n.id for n in a.centre.noeuds] == ["A:S1", "A:C1", "A:E1"]
    assert [n.id for n in b.centre.noeuds] == ["B:S1", "B:C1", "B:E1"]
    assert [(e.source, e.cible) for e in a.centre.aretes] == [("A:S1", "A:C1"),
                                                             ("A:C1", "A:E1")]
    # Les deux centres viennent du même fichier mais ne partagent aucun objet.
    a.centre.noeud("A:S1").occupation = 0
    assert b.centre.noeud("B:S1").occupation == 12


def test_prefixer_ne_modifie_pas_l_original() -> None:
    original = charger("exemple_consigne.json")
    prefixe = prefixer(original, "Z")
    assert prefixe.noeuds[0].id == "Z:S1"
    assert original.noeuds[0].id == "S1" and original.aretes[0].source == "S1"


def test_connexions_rattachees_aux_sorties() -> None:
    zone = charger_zone(ZONE)
    extremites = {x for c in zone.connexions for x in (c.source, c.cible) if ":" in x}
    assert extremites == {"A:E1", "B:E1"}
    for x in extremites:
        centre = next(c for c in zone.centres if c.id == x.split(":")[0]).centre
        assert centre.noeud(x).type == "sortie"


def test_vue_macro_un_noeud_par_centre_et_par_source() -> None:
    zone = charger_zone(ZONE)
    sommets, aretes = zone.vue_macro()
    assert sommets == ["A", "B", "P1", "T1", "Q1"]
    assert len(sommets) == len(zone.centres) + len(zone.sources)
    assert aretes == [("P1", "A"), ("A", "B"), ("T1", "B"), ("Q1", "P1")]


# --- connexions mal rattachées : erreurs explicites -------------------------------------

def test_connexion_vers_un_noeud_qui_n_est_pas_une_sortie() -> None:
    donnees = zone_brute()
    donnees["connexions"][0]["cible"] = "A:S1"
    refuse(donnees, "« A:S1 » n'est pas une sortie \\(type magasin\\)")


def test_connexion_vers_une_sortie_inexistante() -> None:
    donnees = zone_brute()
    donnees["connexions"][0]["cible"] = "A:E9"
    refuse(donnees, "sortie « A:E9 » inexistante dans le centre « A »")


def test_connexion_vers_un_centre_inconnu() -> None:
    donnees = zone_brute()
    donnees["connexions"][0]["cible"] = "Z:E1"
    refuse(donnees, "centre « Z » inconnu")


def test_connexion_depuis_une_source_inconnue() -> None:
    donnees = zone_brute()
    donnees["connexions"][0]["source"] = "P9"
    refuse(donnees, "source « P9 » inconnue")


def test_connexion_boucle_refusee() -> None:
    donnees = zone_brute()
    donnees["connexions"][0]["cible"] = "P1"
    refuse(donnees, "lui-même")


def test_connexion_interne_a_un_centre_refusee(tmp_path: Path) -> None:
    # Un centre à deux sorties, reliées entre elles par une « connexion » : interdit.
    centre = json.loads((DONNEES / "exemple_consigne.json").read_text(encoding="utf-8"))
    centre["noeuds"].append({"id": "E2", "type": "sortie", "capacite_max": 50,
                             "occupation": 0, "capteur_fumee": True, "niveau_fumee": 0,
                             "statut": "sortie"})
    (tmp_path / "deux_sorties.json").write_text(json.dumps(centre), encoding="utf-8")
    donnees = zone_brute()
    donnees["centres"][0]["fichier"] = "deux_sorties.json"
    donnees["connexions"][0].update({"source": "A:E1", "cible": "A:E2"})
    with pytest.raises(ErreurFormat, match="dans le centre « A »"):
        depuis_dict(donnees, lambda f: charger_centre(
            (tmp_path if f == "deux_sorties.json" else DONNEES) / f))


def test_connexion_soumise_aux_regles_d_une_arete() -> None:
    donnees = zone_brute()
    donnees["connexions"][0]["longueur"] = -1
    refuse(donnees, "connexions\\[0\\].*longueur")


# --- centres et sources -----------------------------------------------------------------

@pytest.mark.parametrize("liste", ["centres", "sources"])
def test_identifiant_avec_separateur_refuse(liste: str) -> None:
    donnees = zone_brute()
    donnees[liste][0]["id"] = "X:1"
    refuse(donnees, "ne doit pas contenir « : »")


def test_identifiant_en_double_entre_centre_et_source() -> None:
    donnees = zone_brute()
    donnees["sources"][0]["id"] = "A"
    refuse(donnees, "double.*« A »")


def test_type_de_source_invalide() -> None:
    donnees = zone_brute()
    donnees["sources"][0]["type"] = "aéroport"
    refuse(donnees, "type.*aéroport")


def test_champ_inconnu_dans_la_zone() -> None:
    donnees = zone_brute()
    donnees["centres"][0]["fichiers"] = "x.json"
    refuse(donnees, "inconnus.*fichiers")


# --- chemins dans les messages ----------------------------------------------------------

def test_erreur_de_zone_porte_le_chemin_de_la_zone(tmp_path: Path) -> None:
    donnees = zone_brute()
    donnees["connexions"][0]["cible"] = "A:S1"
    for nom in ("exemple_consigne.json",):
        (tmp_path / nom).write_text((DONNEES / nom).read_text(encoding="utf-8"),
                                    encoding="utf-8")
    zone = tmp_path / "zone.json"
    zone.write_text(json.dumps(donnees), encoding="utf-8")
    with pytest.raises(ErreurFormat, match="zone.json : connexions\\[0\\]"):
        charger_zone(zone)


def test_centre_absent_ou_invalide_nomme_le_fichier_du_centre(tmp_path: Path) -> None:
    donnees = zone_brute()
    zone = tmp_path / "zone.json"
    zone.write_text(json.dumps(donnees), encoding="utf-8")
    with pytest.raises(ErreurFormat, match="exemple_consigne.json illisible") as e:
        charger_zone(zone)
    assert not str(e.value).startswith(str(zone)), "message préfixé deux fois"

    centre = json.loads((DONNEES / "exemple_consigne.json").read_text(encoding="utf-8"))
    centre["noeuds"][0]["type"] = "kiosque"
    (tmp_path / "exemple_consigne.json").write_text(json.dumps(centre), encoding="utf-8")
    with pytest.raises(ErreurFormat, match="exemple_consigne.json : .*kiosque") as e:
        charger_zone(zone)
    assert not str(e.value).startswith(str(zone)), "message préfixé deux fois"
