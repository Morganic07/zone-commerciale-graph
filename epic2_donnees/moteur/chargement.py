"""Lecture des fichiers JSON du projet.

Deux sortes de fichiers :
- stations/A.json, B.json… : le plan d'une station, une liste de nœuds et d'arêtes ;
- reseau.json : la liste des stations, des sources et des tunnels qui les relient.

Fonctionnement : json.load transforme le fichier en dictionnaires et en listes Python,
puis les fonctions lire_… recopient ces valeurs dans les objets du modèle (modele.py).
station_en_dictionnaire fait le chemin inverse, pour envoyer une station à la page web.
"""

import json

from epic2_donnees.moteur.modele import Arete, Noeud, Reseau, Source, Station, StationDuReseau

# ---------------------------------------------------------------------------------------
# Stations (donnees/stations/*.json), au format imposé par la consigne
# ---------------------------------------------------------------------------------------


def lire_noeud(donnee_noeud):
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

    # La position sur le plan n'est pas dans le format de la consigne : on ne la lit
    # que si elle est dans le fichier.
    if "x" in donnee_noeud:
        noeud.x = donnee_noeud["x"]
    if "y" in donnee_noeud:
        noeud.y = donnee_noeud["y"]

    return noeud


def lire_arete(donnee_arete):
    """Crée une arête à partir de ce qui a été lu dans le fichier."""
    return Arete(
        source=donnee_arete["source"],
        cible=donnee_arete["cible"],
        capacite_max=donnee_arete["capacite_max"],
        longueur=donnee_arete["longueur"],
        statut=donnee_arete["statut"],
        sens=donnee_arete["sens"],
        pmr=donnee_arete["pmr"],
    )


def lire_station(donnees):
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


def station_en_dictionnaire(station):
    """Fait l'inverse de lire_station : transforme une station en dictionnaire,
    que le serveur envoie à la page web au format JSON.

    Les champs sont dans l'ordre de la consigne, suivis de la position.
    """
    liste_noeuds = []
    for noeud in station.noeuds:
        donnee_noeud = {}
        donnee_noeud["id"] = noeud.id
        donnee_noeud["type"] = noeud.type
        donnee_noeud["capacite_max"] = noeud.capacite_max
        donnee_noeud["occupation"] = noeud.occupation
        donnee_noeud["capteur_fumee"] = noeud.capteur_fumee
        donnee_noeud["niveau_fumee"] = noeud.niveau_fumee
        donnee_noeud["statut"] = noeud.statut
        donnee_noeud["x"] = noeud.x
        donnee_noeud["y"] = noeud.y
        liste_noeuds.append(donnee_noeud)

    liste_aretes = []
    for arete in station.aretes:
        donnee_arete = {}
        donnee_arete["source"] = arete.source
        donnee_arete["cible"] = arete.cible
        donnee_arete["capacite_max"] = arete.capacite_max
        donnee_arete["longueur"] = arete.longueur
        donnee_arete["statut"] = arete.statut
        donnee_arete["sens"] = arete.sens
        donnee_arete["pmr"] = arete.pmr
        liste_aretes.append(donnee_arete)

    return {"noeuds": liste_noeuds, "aretes": liste_aretes}


def charger_station(chemin):
    """Lit le fichier JSON d'une station et renvoie la station."""
    with open(chemin, encoding="utf-8") as fichier:
        donnees = json.load(fichier)
    return lire_station(donnees)


# ---------------------------------------------------------------------------------------
# Réseau (donnees/reseau.json)
# ---------------------------------------------------------------------------------------


def prefixer(station, prefixe):
    """Ajoute « prefixe: » devant les identifiants des nœuds de la station, et devant
    les extrémités de ses arêtes. Deux stations peuvent ainsi avoir un nœud SAS1
    chacune : ils deviennent A:SAS1 et B:SAS1."""
    for noeud in station.noeuds:
        noeud.id = prefixe + ":" + noeud.id
    for arete in station.aretes:
        arete.source = prefixe + ":" + arete.source
        arete.cible = prefixe + ":" + arete.cible


def charger_reseau(chemin):
    """Lit le fichier du réseau, puis le fichier de chaque station.

    Étapes : (1) chaque station est chargée depuis son fichier, puis ses identifiants
    sont préfixés ; (2) les sources sont lues ; (3) les tunnels (« connexions ») sont
    lus comme des arêtes ordinaires, entre identifiants déjà préfixés (« A:SAS1 »).
    Les fichiers des stations sont cherchés dans le même dossier que celui du réseau.
    Complexité : O(V + E), V nœuds et E arêtes en tout (chacun est lu une fois).
    """
    with open(chemin, encoding="utf-8") as fichier:
        donnees = json.load(fichier)

    dossier = chemin.parent

    # (1) Les stations.
    stations = []
    for donnee_station in donnees["stations"]:
        # Le fichier est relu pour chaque station : deux stations qui utilisent le même
        # plan ont ainsi chacune leurs propres nœuds, préfixés différemment.
        station = charger_station(dossier / donnee_station["fichier"])
        prefixer(station, donnee_station["id"])
        station_du_reseau = StationDuReseau(
            id=donnee_station["id"], station=station, fichier=donnee_station["fichier"]
        )
        # La position sert seulement à placer la station sur la vue d'ensemble.
        if "x" in donnee_station:
            station_du_reseau.x = donnee_station["x"]
        if "y" in donnee_station:
            station_du_reseau.y = donnee_station["y"]
        stations.append(station_du_reseau)

    # (2) Les sources, d'où arrivent les visiteurs.
    sources = []
    for donnee_source in donnees["sources"]:
        source = Source(id=donnee_source["id"], type=donnee_source["type"])
        # Même chose : la position ne sert qu'à l'affichage.
        if "x" in donnee_source:
            source.x = donnee_source["x"]
        if "y" in donnee_source:
            source.y = donnee_source["y"]
        sources.append(source)

    # (3) Les tunnels, qui ont les mêmes champs qu'une arête de station.
    connexions = []
    for donnee_connexion in donnees["connexions"]:
        connexions.append(lire_arete(donnee_connexion))

    return Reseau(stations=stations, sources=sources, connexions=connexions)
