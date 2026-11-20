"""Le serveur web : il charge le réseau avec le moteur et l'envoie à la page."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from moteur.chargement import charger_reseau, station_en_dictionnaire
from moteur.modele import Reseau, Station

RACINE = Path(__file__).resolve().parent.parent
RESEAU_PAR_DEFAUT = RACINE / "donnees" / "reseau.json"
DOSSIER_WEB = RACINE / "web"


def reseau_en_dictionnaire(reseau: Reseau) -> dict[str, Any]:
    """Transforme le réseau en dictionnaire, envoyé à la page au format JSON.

    Les nœuds et les arêtes gardent les champs du format imposé, avec leurs
    identifiants préfixés (« A:SAS1 »).
    """
    liste_stations = []
    for station_du_reseau in reseau.stations:
        donnee_station = station_en_dictionnaire(station_du_reseau.station)
        donnee_station["id"] = station_du_reseau.id
        # Pour que la page dise dans quel fichier modifier un nœud ou un passage.
        donnee_station["fichier"] = station_du_reseau.fichier
        donnee_station["x"] = station_du_reseau.x
        donnee_station["y"] = station_du_reseau.y
        liste_stations.append(donnee_station)

    liste_sources = []
    for source in reseau.sources:
        donnee_source: dict[str, Any] = {}
        donnee_source["id"] = source.id
        donnee_source["type"] = source.type
        donnee_source["x"] = source.x
        donnee_source["y"] = source.y
        liste_sources.append(donnee_source)

    # Les tunnels s'écrivent comme les arêtes d'une station : on les range dans une
    # station sans nœud pour réutiliser station_en_dictionnaire.
    station_des_tunnels = Station(noeuds=[], aretes=reseau.connexions)
    liste_tunnels = station_en_dictionnaire(station_des_tunnels)["aretes"]

    return {"stations": liste_stations, "sources": liste_sources, "connexions": liste_tunnels}


# Ce que le serveur garde en mémoire : le chemin du fichier du réseau.
etat: dict[str, Any] = {"chemin": None}


def donner_reseau() -> dict[str, Any]:
    """Route GET /api/reseau : relit les fichiers JSON à chaque demande.

    Le réseau n'est pas gardé en mémoire : sinon, après une modification d'un fichier,
    la page continuerait d'afficher l'ancienne version sans qu'on s'en aperçoive.
    Les fichiers sont petits, les relire est instantané.
    """
    return reseau_en_dictionnaire(charger_reseau(etat["chemin"]))


def recharger() -> dict[str, Any]:
    """Route POST /api/recharger, utilisée par le bouton « Recharger les fichiers » :
    relit les fichiers JSON, comme /api/reseau."""
    return donner_reseau()


def creer_application(chemin_reseau: Path) -> FastAPI:
    """Crée le serveur, qui lira le réseau dans ce fichier."""
    etat["chemin"] = chemin_reseau

    application = FastAPI(title="Réseau de stations spatiales")
    application.add_api_route("/api/reseau", donner_reseau, methods=["GET"])
    application.add_api_route("/api/recharger", recharger, methods=["POST"])

    # Tout le reste est la page : web/index.html et ses fichiers.
    application.mount("/", StaticFiles(directory=DOSSIER_WEB, html=True))
    return application
