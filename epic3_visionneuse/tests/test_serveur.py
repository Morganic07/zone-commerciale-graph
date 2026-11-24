"""Story 3.1 : serveur minimal (une route pour le réseau, une pour recharger, la page)."""

import json
import shutil
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from epic3_visionneuse.serveur.application import RESEAU_PAR_DEFAUT, creer_application

# Les petits fichiers de test sont rangés avec ceux de l'epic 2, qui les a créés.
RACINE = Path(__file__).resolve().parent.parent.parent
DONNEES_TEST = RACINE / "epic2_donnees" / "tests" / "donnees"


def test_route_reseau() -> None:
    client = TestClient(creer_application(RESEAU_PAR_DEFAUT))
    reponse = client.get("/api/reseau")
    assert reponse.status_code == 200
    reseau = reponse.json()
    assert len(reseau["stations"]) == 3
    assert reseau["stations"][0]["id"] == "A"
    assert reseau["stations"][0]["fichier"] == "stations/A.json"
    assert reseau["stations"][0]["noeuds"][0]["id"] == "A:A1"
    assert reseau["sources"] == []
    assert reseau["connexions"][0]["source"] == "A:A12"
    assert reseau["connexions"][0]["cible"] == "B:B1"


def test_route_recharger_relit_les_fichiers(tmp_path: Path) -> None:
    shutil.copy(DONNEES_TEST / "reseau_test.json", tmp_path / "reseau.json")
    shutil.copy(DONNEES_TEST / "exemple_consigne.json", tmp_path / "exemple_consigne.json")
    client = TestClient(creer_application(tmp_path / "reseau.json"))
    assert len(client.get("/api/reseau").json()["sources"]) == 2

    # On ajoute une source dans le fichier : elle apparaît dès la demande suivante,
    # sans redémarrer le serveur (le réseau n'est pas gardé en mémoire).
    chemin = tmp_path / "reseau.json"
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    donnees["sources"].append({"id": "R1", "type": "relais"})
    chemin.write_text(json.dumps(donnees), encoding="utf-8")
    assert len(client.get("/api/reseau").json()["sources"]) == 3

    reponse = client.post("/api/recharger")
    assert reponse.status_code == 200
    assert len(reponse.json()["sources"]) == 3


def test_la_page_est_servie() -> None:
    client = TestClient(creer_application(RESEAU_PAR_DEFAUT))
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "Réseau de stations spatiales" in reponse.text


# --- route de navigation (panneau « navigation.py » de la visionneuse) ---------------------


def naviguer(pmr: bool, beta: float, bloques: list[str], taux: dict[str, float]) -> Any:
    client = TestClient(creer_application(DONNEES_TEST / "reseau_test.json"))
    demande = {"pmr": pmr, "beta": beta, "bloques": bloques, "taux": taux}
    reponse = client.post("/api/navigation", json=demande)
    assert reponse.status_code == 200
    return reponse.json()["voisins"]


def test_navigation_a_pied() -> None:
    # Réseau de test : A et B suivent l'exemple de la consigne (S1 - C1 - E1),
    # et le tunnel A:E1 - B:E1 n'est pas praticable en fauteuil.
    voisins = naviguer(False, 0.0, [], {})
    assert voisins["A:S1"] == [["A:C1", 8.0]]
    assert ["B:E1", 300.0] in voisins["A:E1"]


def test_navigation_en_fauteuil_retire_le_tunnel_non_pmr() -> None:
    voisins = naviguer(True, 0.0, [], {})
    for voisin, _ in voisins["A:E1"]:
        assert voisin != "B:E1"


def test_navigation_avec_un_noeud_bloque() -> None:
    voisins = naviguer(False, 0.0, ["A:C1"], {})
    assert "A:C1" not in voisins
    assert voisins["A:S1"] == []


def test_navigation_avec_une_arete_encombree() -> None:
    # 8 × (1 + 2 × 0,5) = 16
    voisins = naviguer(False, 2.0, [], {"A:S1|A:C1": 0.5})
    assert voisins["A:S1"] == [["A:C1", 16.0]]
