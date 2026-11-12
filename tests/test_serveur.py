"""Story 6.1 : le serveur, une route par test avec le client de test de FastAPI, et une
erreur 4xx explicite pour chaque requête invalide."""

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import serveur.session as session_module
from serveur.app import app, courante

client = TestClient(app)


@pytest.fixture(autouse=True)
def session_vide() -> None:
    courante.clear()


def charger() -> dict:
    reponse = client.post("/api/scenarios/journee_normale")
    assert reponse.status_code == 200
    return reponse.json()


def un_noeud(type_noeud: str) -> str:
    for n in client.get("/api/etat").json()["noeuds"]:
        if n["type"] == type_noeud:
            return n["id"]
    raise AssertionError(type_noeud)


# --- scénarios --------------------------------------------------------------------------

def test_liste_des_scenarios() -> None:
    reponse = client.get("/api/scenarios")
    assert reponse.status_code == 200
    ids = []
    for s in reponse.json():
        ids.append(s["id"])
        assert s["nom"] and s["description"]
    assert "journee_normale" in ids


def test_charger_un_scenario() -> None:
    etat = charger()
    assert etat["scenario"] == "journee_normale"
    assert etat["temps"] == 0.0
    assert len(etat["noeuds"]) > 0 and len(etat["sources"]) == 3


def scenario_avec_foyers(dossier: Path, foyers: dict) -> None:
    """Écrit dans `dossier` un scénario « feu » : la journée normale plus un incendie."""
    scenario = json.loads((session_module.SCENARIOS / "journee_normale.json").read_text())
    scenario["incendie"] = {"debut_s": 5, "foyers": foyers, "alpha": 0.05,
                            "theta1": 20, "theta2": 50, "delai": 15,
                            "connaissance": "local"}
    (dossier / "feu.json").write_text(json.dumps(scenario))


def test_scenario_au_foyer_inconnu(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scenario_avec_foyers(tmp_path, {"Z:99": 1.0})
    monkeypatch.setattr(session_module, "SCENARIOS", tmp_path)
    reponse = client.post("/api/scenarios/feu")
    assert reponse.status_code == 422
    assert "Z:99" in reponse.json()["detail"]


def test_scenario_aux_foyers_dans_deux_centres(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    noeuds = charger()["noeuds"]
    premier = noeuds[0]
    autre = noeuds[-1]
    assert premier["centre"] != autre["centre"]
    scenario_avec_foyers(tmp_path, {premier["id"]: 1.0, autre["id"]: 1.0})
    monkeypatch.setattr(session_module, "SCENARIOS", tmp_path)
    reponse = client.post("/api/scenarios/feu")
    assert reponse.status_code == 422
    assert "un seul centre" in reponse.json()["detail"]


def test_chaque_scenario_se_joue() -> None:
    for scenario in client.get("/api/scenarios").json():
        assert client.post(f"/api/scenarios/{scenario['id']}").status_code == 200
        for _ in range(3):
            reponse = client.post("/api/pas?nombre=100")
            assert reponse.status_code == 200, scenario["id"]
        assert reponse.json()["temps"] == 300.0


def test_scenario_inconnu() -> None:
    reponse = client.post("/api/scenarios/inexistant")
    assert reponse.status_code == 404
    assert "inexistant" in reponse.json()["detail"]


# --- état et pas ------------------------------------------------------------------------

def test_etat_sans_scenario() -> None:
    reponse = client.get("/api/etat")
    assert reponse.status_code == 409
    assert "aucun scénario" in reponse.json()["detail"]


def test_etat_contenu() -> None:
    charger()
    etat = client.get("/api/etat").json()
    noeud = etat["noeuds"][0]
    for cle in ["id", "x", "y", "occupation", "capacite_max", "niveau", "fumee", "statut"]:
        assert cle in noeud
    arete = etat["aretes"][0]
    for cle in ["source", "cible", "taux", "niveau", "statut", "attente"]:
        assert cle in arete


def test_pas() -> None:
    charger()
    reponse = client.post("/api/pas?nombre=60")
    assert reponse.status_code == 200
    etat = reponse.json()
    assert etat["temps"] == 60.0
    assert len(etat["agents"]) > 0
    for agent in etat["agents"]:
        assert 0 <= agent["avancee"] <= 1


@pytest.mark.parametrize("nombre", [0, 101, -3])
def test_nombre_de_pas_invalide(nombre: int) -> None:
    charger()
    reponse = client.post(f"/api/pas?nombre={nombre}")
    assert reponse.status_code == 422


# --- réglages ---------------------------------------------------------------------------

def test_reglages() -> None:
    charger()
    reponse = client.put("/api/reglages", json={"beta": 4.0, "part_pmr": 0.3,
                                                 "connaissance": "global"})
    assert reponse.status_code == 200
    reglages = reponse.json()["reglages"]
    assert reglages["beta"] == 4.0 and reglages["part_pmr"] == 0.3
    assert reglages["connaissance"] == "global"


@pytest.mark.parametrize("corps", [
    {"part_pmr": 1.5}, {"beta": -1}, {"alpha": 1.0}, {"connaissance": "partielle"},
    {"theta1": 60, "theta2": 40},
])
def test_reglages_invalides(corps: dict) -> None:
    charger()
    assert client.put("/api/reglages", json=corps).status_code == 422


# --- feu --------------------------------------------------------------------------------

def test_allumer_un_feu() -> None:
    charger()
    foyer = un_noeud("magasin")
    reponse = client.post("/api/feu", json={"noeud": foyer})
    assert reponse.status_code == 200
    assert reponse.json()["alarme"]["centre"] == foyer.split(":")[0]
    etat = client.post("/api/pas?nombre=100").json()
    fumee = 0.0
    for n in etat["noeuds"]:
        if n["id"] == foyer:
            fumee = n["fumee"]
    assert fumee > 0


def test_feu_sur_un_noeud_inconnu() -> None:
    charger()
    reponse = client.post("/api/feu", json={"noeud": "Z:99"})
    assert reponse.status_code == 404


def test_un_seul_centre_en_feu() -> None:
    charger()
    noeuds = client.get("/api/etat").json()["noeuds"]
    premier = noeuds[0]
    autre = None
    for n in noeuds:
        if n["centre"] != premier["centre"]:
            autre = n
    assert autre is not None
    assert client.post("/api/feu", json={"noeud": premier["id"]}).status_code == 200
    reponse = client.post("/api/feu", json={"noeud": autre["id"]})
    assert reponse.status_code == 409
    assert "déjà en cours" in reponse.json()["detail"]


# --- itinéraire -------------------------------------------------------------------------

def test_itineraire() -> None:
    charger()
    reponse = client.get("/api/itineraire?source=P1&centre=B&critere=pmr")
    assert reponse.status_code == 200
    resultat = reponse.json()
    assert resultat["chemin"][0] == "P1" and resultat["cout"] > 0


@pytest.mark.parametrize("requete, code", [
    ("source=P1&centre=B&critere=rapide", 422),
    ("source=XX&centre=B", 404),
    ("source=P1&centre=Z", 404),
    ("source=P1", 422),
])
def test_itineraire_invalide(requete: str, code: int) -> None:
    charger()
    assert client.get(f"/api/itineraire?{requete}").status_code == code


def test_page() -> None:
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "cytoscape.min.js" in reponse.text


def test_fichiers_de_la_page_servis() -> None:
    # Chaque fichier cité par la page (scripts, feuille de style, pictogrammes) et par la
    # feuille de style (polices) est bien servi : rien ne vient d'Internet.
    page = client.get("/").text
    style = client.get("/web/style.css").text
    adresses = re.findall(r'(?:src|href)="(/web/[^"]+)"', page)
    adresses = adresses + re.findall(r'url\("(/web/[^"]+)"\)', style)
    assert len(adresses) >= 8
    for adresse in adresses:
        assert client.get(adresse).status_code == 200, adresse
    assert "http" not in page


def test_foyers_dans_l_etat() -> None:
    charger()
    foyer = un_noeud("magasin")
    etat = client.post("/api/feu", json={"noeud": foyer}).json()
    assert etat["alarme"]["foyers"] == [foyer]
