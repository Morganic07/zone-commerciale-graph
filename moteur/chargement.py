"""Lecture et écriture des fichiers JSON du projet."""

import json
from pathlib import Path
from typing import Any

from moteur.modele import Arete, Noeud, Station

# ---------------------------------------------------------------------------------------
# Paramètres physiques (donnees/parametres.json)
# ---------------------------------------------------------------------------------------


def charger_parametres(chemin: Path) -> dict[str, float]:
    """Lit le fichier des paramètres et renvoie un dictionnaire {nom: valeur}.

    Complexité : O(n), n étant le nombre de paramètres (une seule boucle).
    """
    with open(chemin, encoding="utf-8") as fichier:
        donnees = json.load(fichier)

    valeurs = {}
    for nom in donnees:
        valeurs[nom] = donnees[nom]["valeur"]
    return valeurs


# ---------------------------------------------------------------------------------------
# Stations (donnees/stations/*.json), au format imposé par la consigne
# ---------------------------------------------------------------------------------------


def lire_noeud(donnee_noeud: dict[str, Any]) -> Noeud:
    """Crée un nœud à partir de ce qui a été lu dans le fichier."""
    noeud = Noeud(
        id=donnee_noeud["id"],
        type=donnee_noeud["type"],
        capacite_max=donnee_noeud["capacite_max"],
        occupation=donnee_noeud["occupation"],
        capteur_fumee=donnee_noeud["capteur_fumee"],
        niveau_fumee=donnee_noeud["niveau_fumee"],
        statut=donnee_noeud["statut"],
    )

    # Champs facultatifs : on ne les lit que s'ils sont dans le fichier.
    if "x" in donnee_noeud:
        noeud.x = donnee_noeud["x"]
    if "y" in donnee_noeud:
        noeud.y = donnee_noeud["y"]
    if "nom" in donnee_noeud:
        noeud.nom = donnee_noeud["nom"]

    return noeud


def lire_arete(donnee_arete: dict[str, Any]) -> Arete:
    """Crée une arête à partir de ce qui a été lu dans le fichier."""
    arete = Arete(
        source=donnee_arete["source"],
        cible=donnee_arete["cible"],
        capacite_max=donnee_arete["capacite_max"],
        longueur=donnee_arete["longueur"],
        statut=donnee_arete["statut"],
        sens=donnee_arete["sens"],
        pmr=donnee_arete["pmr"],
    )

    # Champ facultatif.
    if "largeur" in donnee_arete:
        arete.largeur = donnee_arete["largeur"]

    return arete


def lire_station(donnees: dict[str, Any]) -> Station:
    """Crée une station à partir de ce qui a été lu dans son fichier.

    Complexité : O(V + E), V nœuds et E arêtes (chacun est lu une fois).
    """
    noeuds = []
    for donnee_noeud in donnees["noeuds"]:
        noeuds.append(lire_noeud(donnee_noeud))

    aretes = []
    for donnee_arete in donnees["aretes"]:
        aretes.append(lire_arete(donnee_arete))

    return Station(noeuds=noeuds, aretes=aretes)


def station_en_dictionnaire(station: Station) -> dict[str, Any]:
    """Fait l'inverse de lire_station : transforme une station en dictionnaire,
    prêt à être écrit dans un fichier JSON.

    Les champs sont dans l'ordre de la consigne. Les champs facultatifs ne sont écrits
    que s'ils ont une valeur, pour qu'un fichier relu puis réécrit reste identique.
    """
    liste_noeuds = []
    for noeud in station.noeuds:
        donnee_noeud: dict[str, Any] = {}
        donnee_noeud["id"] = noeud.id
        donnee_noeud["type"] = noeud.type
        donnee_noeud["capacite_max"] = noeud.capacite_max
        donnee_noeud["occupation"] = noeud.occupation
        donnee_noeud["capteur_fumee"] = noeud.capteur_fumee
        donnee_noeud["niveau_fumee"] = noeud.niveau_fumee
        donnee_noeud["statut"] = noeud.statut
        if noeud.x is not None:
            donnee_noeud["x"] = noeud.x
        if noeud.y is not None:
            donnee_noeud["y"] = noeud.y
        if noeud.nom is not None:
            donnee_noeud["nom"] = noeud.nom
        liste_noeuds.append(donnee_noeud)

    liste_aretes = []
    for arete in station.aretes:
        donnee_arete: dict[str, Any] = {}
        donnee_arete["source"] = arete.source
        donnee_arete["cible"] = arete.cible
        donnee_arete["capacite_max"] = arete.capacite_max
        donnee_arete["longueur"] = arete.longueur
        donnee_arete["statut"] = arete.statut
        donnee_arete["sens"] = arete.sens
        donnee_arete["pmr"] = arete.pmr
        if arete.largeur is not None:
            donnee_arete["largeur"] = arete.largeur
        liste_aretes.append(donnee_arete)

    return {"noeuds": liste_noeuds, "aretes": liste_aretes}


def charger_station(chemin: Path) -> Station:
    """Lit le fichier JSON d'une station et renvoie la station."""
    with open(chemin, encoding="utf-8") as fichier:
        donnees = json.load(fichier)
    return lire_station(donnees)


def ecrire_station(station: Station, chemin: Path) -> None:
    """Écrit une station dans un fichier JSON."""
    donnees = station_en_dictionnaire(station)
    # ensure_ascii=False garde les accents (« enfumé ») ; indent=2 rend le fichier lisible.
    texte = json.dumps(donnees, ensure_ascii=False, indent=2)
    with open(chemin, "w", encoding="utf-8") as fichier:
        fichier.write(texte + "\n")
