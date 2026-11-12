"""Serveur web : expose la simulation à la page (PLAN.md § 1).

C'est la page qui pilote l'horloge : elle demande un pas (`POST /api/pas`) toutes les
1000 / vitesse millisecondes. Pause = plus de demandes ; pas à pas = une demande.

    GET  /api/scenarios              liste des scénarios
    POST /api/scenarios/{id}         charge un scénario (et repart de zéro)
    GET  /api/etat                   état complet à afficher
    POST /api/pas?nombre=1           avance de 1 à 100 pas, renvoie l'état
    PUT  /api/reglages               modifie les réglages (β, part PMR, incendie…)
    POST /api/feu                    allume un foyer sur un nœud
    GET  /api/itineraire             itinéraire d'une source vers un centre
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from serveur.session import Session, lister_scenarios
from zc.chemins import itineraire
from zc.modele import ErreurFormat
from zc.navigation import CRITERES

WEB = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Zone commerciale")

# La session en cours (une seule : l'application tourne en local, pour une démo).
courante: dict[str, Session] = {}


def session() -> Session:
    if "session" not in courante:
        raise HTTPException(status_code=409,
                            detail="aucun scénario chargé : POST /api/scenarios/{id}")
    return courante["session"]


class Reglages(BaseModel):
    """Réglages modifiables pendant la démonstration. Ceux qui manquent ne changent pas."""

    beta: float | None = Field(default=None, ge=0)
    part_pmr: float | None = Field(default=None, ge=0, le=1)
    alpha: float | None = Field(default=None, gt=0, lt=1)
    theta1: float | None = Field(default=None, gt=0, le=100)
    theta2: float | None = Field(default=None, gt=0, le=100)
    delai: int | None = Field(default=None, ge=0)
    connaissance: str | None = Field(default=None, pattern="^(local|global)$")


class Feu(BaseModel):
    noeud: str


@app.get("/api/scenarios")
def scenarios() -> list[dict[str, str]]:
    return lister_scenarios()


@app.post("/api/scenarios/{scenario_id}")
def charger(scenario_id: str) -> dict[str, Any]:
    try:
        courante["session"] = Session(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"scénario « {scenario_id} » inconnu")
    except ErreurFormat as erreur:
        raise HTTPException(status_code=422, detail=str(erreur))
    return courante["session"].etat()


@app.get("/api/etat")
def etat() -> dict[str, Any]:
    return session().etat()


@app.post("/api/pas")
def pas(nombre: int = 1) -> dict[str, Any]:
    if nombre < 1 or nombre > 100:
        raise HTTPException(status_code=422, detail="nombre de pas entre 1 et 100")
    s = session()
    for _ in range(nombre):
        s.pas()
    return s.etat()


@app.put("/api/reglages")
def regler(reglages: Reglages) -> dict[str, Any]:
    s = session()
    theta1 = s.reglages_feu["theta1"]
    if reglages.theta1 is not None:
        theta1 = reglages.theta1
    theta2 = s.reglages_feu["theta2"]
    if reglages.theta2 is not None:
        theta2 = reglages.theta2
    if theta1 >= theta2:
        raise HTTPException(status_code=422, detail="il faut θ₁ < θ₂")

    if reglages.beta is not None:
        s.demande.parametres.beta = reglages.beta
    if reglages.part_pmr is not None:
        s.demande.parametres.part_pmr = reglages.part_pmr
    # Les réglages de l'incendie valent pour le prochain feu allumé.
    s.reglages_feu["theta1"] = theta1
    s.reglages_feu["theta2"] = theta2
    if reglages.alpha is not None:
        s.reglages_feu["alpha"] = reglages.alpha
    if reglages.delai is not None:
        s.reglages_feu["delai"] = reglages.delai
    if reglages.connaissance is not None:
        s.reglages_feu["connaissance"] = reglages.connaissance
    return s.etat()


@app.post("/api/feu")
def feu(demande: Feu) -> dict[str, Any]:
    s = session()
    try:
        s.allumer(demande.noeud)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"nœud « {demande.noeud} » inconnu")
    except ValueError as erreur:
        raise HTTPException(status_code=409, detail=str(erreur))
    return s.etat()


@app.get("/api/itineraire")
def chemin(source: str, centre: str, critere: str = "court",
           magasin: str | None = None) -> dict[str, Any]:
    if critere not in CRITERES:
        raise HTTPException(status_code=422, detail=f"critère parmi {CRITERES}")
    s = session()
    try:
        resultat = itineraire(s.zone, source, centre, critere,
                              beta=s.demande.parametres.beta, magasin=magasin)
    except ValueError as erreur:
        raise HTTPException(status_code=404, detail=str(erreur))
    if resultat is None:
        return {"cout": None, "chemin": []}
    return {"cout": round(resultat[0], 1), "chemin": resultat[1]}


@app.get("/")
def accueil() -> FileResponse:
    page = WEB / "index.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="la page n'est pas encore écrite")
    return FileResponse(page)


if WEB.is_dir():
    app.mount("/web", StaticFiles(directory=WEB), name="web")
