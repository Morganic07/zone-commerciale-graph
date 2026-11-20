"""Story 3.1 : serveur minimal (une route pour le réseau, une pour recharger, la page)."""

import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from serveur.application import RESEAU_PAR_DEFAUT, creer_application

DONNEES_TEST = Path(__file__).resolve().parent / "donnees"


def test_route_reseau() -> None:
    client = TestClient(creer_application(RESEAU_PAR_DEFAUT))
    reponse = client.get("/api/reseau")
    assert reponse.status_code == 200
    reseau = reponse.json()
    assert len(reseau["stations"]) == 3
    assert reseau["stations"][0]["id"] == "A"
    assert reseau["stations"][0]["noeuds"][0]["id"] == "A:SAS1"
    assert len(reseau["sources"]) == 3
    assert reseau["connexions"][0]["cible"] == "A:SAS1"


def test_route_recharger_relit_les_fichiers(tmp_path: Path) -> None:
    shutil.copy(DONNEES_TEST / "reseau_test.json", tmp_path / "reseau.json")
    shutil.copy(DONNEES_TEST / "exemple_consigne.json", tmp_path / "exemple_consigne.json")
    client = TestClient(creer_application(tmp_path / "reseau.json"))
    assert len(client.get("/api/reseau").json()["sources"]) == 2

    # On ajoute une source dans le fichier : elle n'apparaît qu'après le rechargement.
    chemin = tmp_path / "reseau.json"
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    donnees["sources"].append({"id": "R1", "type": "relais"})
    chemin.write_text(json.dumps(donnees), encoding="utf-8")
    assert len(client.get("/api/reseau").json()["sources"]) == 2

    reponse = client.post("/api/recharger")
    assert reponse.status_code == 200
    assert len(reponse.json()["sources"]) == 3
    assert len(client.get("/api/reseau").json()["sources"]) == 3


def test_la_page_est_servie() -> None:
    client = TestClient(creer_application(RESEAU_PAR_DEFAUT))
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "Réseau de stations spatiales" in reponse.text
