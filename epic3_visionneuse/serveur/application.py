"""Le serveur web : il charge le réseau avec le moteur et l'envoie à la page."""

import json
from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.staticfiles import StaticFiles

from epic2_donnees.moteur.chargement import charger_reseau, station_en_dictionnaire
from epic2_donnees.moteur.modele import Station
from epic4_algorithmes.moteur.chemins import (
    chemin_le_moins_encombre,
    chemin_pmr,
    chemins_d_evacuation,
    plus_court_chemin,
)
from epic4_algorithmes.moteur.navigation import graphe_de_navigation
from epic5_simulation.moteur.simulation import ajouter_visiteurs, creer_simulation, pas

# Racine du projet : serveur/ est dans epic3_visionneuse/, lui-même à la racine.
RACINE = Path(__file__).resolve().parent.parent.parent
RESEAU_PAR_DEFAUT = RACINE / "epic2_donnees" / "donnees" / "reseau.json"
PARAMETRES = RACINE / "epic2_donnees" / "donnees" / "parametres.json"
DOSSIER_WEB = RACINE / "epic3_visionneuse" / "web"


def reseau_en_dictionnaire(reseau):
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
        donnee_source = {}
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


# Ce que le serveur garde en mémoire : le chemin du fichier du réseau, la simulation
# en cours (None tant qu'on n'en a pas créé) et le nombre de pas déjà joués.
etat = {"chemin": None, "simulation": None, "pas": 0}


def donner_reseau():
    """Route GET /api/reseau : relit les fichiers JSON à chaque demande.

    Le réseau n'est pas gardé en mémoire : sinon, après une modification d'un fichier,
    la page continuerait d'afficher l'ancienne version sans qu'on s'en aperçoive.
    Les fichiers sont petits, les relire est instantané.
    """
    return reseau_en_dictionnaire(charger_reseau(etat["chemin"]))


def recharger():
    """Route POST /api/recharger, utilisée par le bouton « Recharger les fichiers » :
    relit les fichiers JSON, comme /api/reseau."""
    return donner_reseau()


def calculer_navigation(demande=Body()):
    """Route POST /api/navigation : lance graphe_de_navigation
    (epic4_algorithmes/moteur/navigation.py) sur le réseau des fichiers, dans la situation
    choisie sur la page.

    `demande=Body()` dit à FastAPI que `demande` est le JSON envoyé par la page.

    La demande contient :
    - « pmr » : vrai pour un trajet en fauteuil ;
    - « beta » : le coefficient β du coût longueur × (1 + β·τ) ;
    - « bloques » : la liste des nœuds à bloquer (« A:A5 »), comme pendant un incendie ;
    - « taux » : le taux d'occupation τ de certaines arêtes, sous la forme
      {"A:A2|A:A5": 0.8} (source et cible de l'arête, comme dans le fichier).
    Renvoie {"voisins": {nœud: [[voisin, coût], ...]}}, le résultat tel quel.
    """
    reseau = reseau_avec_bloques(demande["bloques"])
    taux = lire_taux(demande["taux"])
    voisins = graphe_de_navigation(reseau, demande["pmr"], demande["beta"], taux)
    return {"voisins": voisins}


def reseau_avec_bloques(bloques):
    """Charge le réseau des fichiers, puis donne le statut « bloqué » aux nœuds de la
    liste, comme le ferait le feu."""
    reseau = charger_reseau(etat["chemin"])
    for station_du_reseau in reseau.stations:
        for noeud in station_du_reseau.station.noeuds:
            if noeud.id in bloques:
                noeud.statut = "bloqué"
    return reseau


def lire_taux(taux_de_la_page):
    """« A:A2|A:A5 » devient la paire ("A:A2", "A:A5") qu'attend le moteur : une paire ne
    peut pas être une clé en JSON, la page envoie donc les deux nœuds collés par « | »."""
    taux = {}
    for cle in taux_de_la_page:
        morceaux = cle.split("|")
        taux[(morceaux[0], morceaux[1])] = taux_de_la_page[cle]
    return taux


def calculer_chemin(demande=Body()):
    """Route POST /api/chemin : lance la fonction du critère choisi
    (epic4_algorithmes/moteur/chemins.py) sur le réseau des fichiers, dans la situation
    choisie sur la page. Comme pour /api/navigation, `demande` est le JSON de la page.

    La demande contient « depart » et « arrivee » (« A:A5 »), « critere » (« plus_court »,
    « moins_encombre » ou « pmr »), et, comme /api/navigation, « beta », « bloques » et
    « taux » (ces deux derniers ne servent qu'au critère « moins_encombre »).
    Renvoie {"chemin": [nœuds], "cout": coût}, ou {"chemin": [], "cout": None} s'il n'y a
    aucun chemin.
    """
    reseau = reseau_avec_bloques(demande["bloques"])
    depart = demande["depart"]
    arrivee = demande["arrivee"]

    if demande["critere"] == "moins_encombre":
        taux = lire_taux(demande["taux"])
        chemin, cout = chemin_le_moins_encombre(reseau, depart, arrivee, demande["beta"], taux)
    elif demande["critere"] == "pmr":
        chemin, cout = chemin_pmr(reseau, depart, arrivee)
    else:
        chemin, cout = plus_court_chemin(reseau, depart, arrivee)
    return {"chemin": chemin, "cout": cout}


def calculer_evacuation(demande=Body()):
    """Route POST /api/evacuation : lance chemins_d_evacuation
    (epic4_algorithmes/moteur/chemins.py) sur le réseau des fichiers. `demande` est le
    JSON de la page : « pmr » (vrai pour un trajet en fauteuil) et « bloques » (les nœuds
    à bloquer, comme pendant un incendie).

    Renvoie {"couts": {nœud: coût}, "suivants": {nœud: nœud suivant vers la sortie},
    "pieges": [nœuds praticables sans chemin vers une sortie]}.
    """
    reseau = reseau_avec_bloques(demande["bloques"])
    couts, suivants = chemins_d_evacuation(reseau, demande["pmr"])

    # Un nœud piégé n'est ni bloqué, ni atteint par le calcul.
    pieges = []
    for station_du_reseau in reseau.stations:
        for noeud in station_du_reseau.station.noeuds:
            if noeud.statut != "bloqué" and noeud.id not in couts:
                pieges.append(noeud.id)

    return {"couts": couts, "suivants": suivants, "pieges": pieges}


def charger_parametres():
    """Lit les valeurs physiques (parametres.json) et renvoie un dictionnaire
    nom → valeur (par exemple « vitesse_valide » → 1.34). La source de chaque valeur
    reste dans le fichier : le programme n'a besoin que du nombre."""
    with open(PARAMETRES, encoding="utf-8") as fichier:
        donnees = json.load(fichier)

    parametres = {}
    for nom in donnees:
        parametres[nom] = donnees[nom]["valeur"]
    return parametres


def creer_la_simulation(demande=Body()):
    """Route POST /api/simulation/creer : crée une simulation (epic5_simulation/moteur/
    simulation.py) sur le réseau des fichiers, avec des visiteurs de démonstration.

    La demande contient « visiteurs » (leur nombre) et « part_pmr » (entre 0 et 1).
    Les visiteurs et leurs chemins sont créés par ajouter_visiteurs
    (simulation.py). Renvoie l'état de la simulation (voir etat_de_la_simulation).
    """
    reseau = charger_reseau(etat["chemin"])
    parametres = charger_parametres()
    simulation = creer_simulation(reseau, parametres["vitesse_valide"], parametres["vitesse_pmr"])
    ajouter_visiteurs(simulation, reseau, demande["visiteurs"], demande["part_pmr"])

    etat["simulation"] = simulation
    etat["pas"] = 0
    return etat_de_la_simulation(simulation)


def jouer_un_pas():
    """Route POST /api/simulation/pas : joue un pas de temps et renvoie le nouvel état."""
    pas(etat["simulation"])
    etat["pas"] = etat["pas"] + 1
    return etat_de_la_simulation(etat["simulation"])


def etat_de_la_simulation(simulation):
    """Ce que la page affiche :
    - « pas » : le nombre de pas joués (un pas = une seconde) ;
    - « occupations » : pour chaque nœud, le nombre de personnes présentes ;
    - « sur_les_aretes » : pour chaque arête, le nombre de personnes qui y marchent ou
      attendent à son bout, rangé sous « source vers cible » comme dans la page ;
    - « compteurs » : le nombre d'agents dans chaque état, et le nombre d'arrivés ;
    - « agents » : pour chaque agent, de quoi le dessiner (voir agent_en_dictionnaire).
    """
    occupations = {}
    for identifiant in simulation.noeuds:
        occupations[identifiant] = simulation.noeuds[identifiant].occupation

    sur_les_aretes = {}
    compteurs = {"noeud": 0, "arete": 0, "attente": 0, "arrives": 0}
    for agent in simulation.agents:
        compteurs[agent.etat] = compteurs[agent.etat] + 1
        # Arrivé : dans le dernier nœud de son chemin.
        if agent.etat == "noeud" and len(agent.chemin) == 0:
            compteurs["arrives"] = compteurs["arrives"] + 1

        # Un agent qui attend devant son premier sas n'est sur aucune arête.
        sur_une_arete = agent.etat == "arete" or agent.etat == "attente"
        if sur_une_arete and agent.noeud != "":
            arete = simulation.aretes[(agent.noeud, agent.chemin[0])]
            cle = arete.source + " vers " + arete.cible
            if cle not in sur_les_aretes:
                sur_les_aretes[cle] = 0
            sur_les_aretes[cle] = sur_les_aretes[cle] + 1

    liste_agents = []
    for agent in simulation.agents:
        liste_agents.append(agent_en_dictionnaire(simulation, agent))

    return {
        "pas": etat["pas"],
        "occupations": occupations,
        "sur_les_aretes": sur_les_aretes,
        "compteurs": compteurs,
        "agents": liste_agents,
    }


def agent_en_dictionnaire(simulation, agent):
    """Ce qu'il faut à la page pour dessiner un agent :
    - « etat » : « noeud », « arete » ou « attente » ;
    - « pmr » : vrai s'il est en fauteuil ;
    - « noeud » : le nœud où il est, ou celui qu'il vient de quitter ("" s'il n'est
      encore entré nulle part) ;
    - « suivant » : le nœud suivant de son chemin ("" s'il est arrivé) ;
    - « avance » : la part de l'arête déjà parcourue, entre 0 et 1 (0 hors d'une arête).
    """
    suivant = ""
    if len(agent.chemin) > 0:
        suivant = agent.chemin[0]

    avance = 0
    if agent.etat == "arete":
        arete = simulation.aretes[(agent.noeud, suivant)]
        # Toujours inférieur à 1 : au bout de l'arête, l'agent passe en attente.
        avance = agent.position / arete.longueur

    donnee_agent = {}
    donnee_agent["etat"] = agent.etat
    donnee_agent["pmr"] = agent.pmr
    donnee_agent["noeud"] = agent.noeud
    donnee_agent["suivant"] = suivant
    donnee_agent["avance"] = avance
    return donnee_agent


class PageSansCache(StaticFiles):
    """Sert la page (web/) en demandant au navigateur de revérifier chaque fichier.

    Sans cela, après une modification de visionneuse.js, un simple F5 garde l'ancien
    script en cache : la page mélange alors le nouvel index.html et l'ancien code.
    « no-cache » ne supprime pas le cache : le navigateur demande si le fichier a changé,
    et le serveur répond « 304, pas changé » sans le renvoyer.
    """

    def file_response(self, full_path, stat_result, scope, status_code=200):
        reponse = super().file_response(full_path, stat_result, scope, status_code)
        reponse.headers["Cache-Control"] = "no-cache"
        return reponse


def creer_application(chemin_reseau):
    """Crée le serveur, qui lira le réseau dans ce fichier."""
    etat["chemin"] = chemin_reseau

    application = FastAPI(title="Réseau de stations spatiales")
    application.add_api_route("/api/reseau", donner_reseau, methods=["GET"])
    application.add_api_route("/api/recharger", recharger, methods=["POST"])
    application.add_api_route("/api/navigation", calculer_navigation, methods=["POST"])
    application.add_api_route("/api/chemin", calculer_chemin, methods=["POST"])
    application.add_api_route("/api/evacuation", calculer_evacuation, methods=["POST"])
    application.add_api_route("/api/simulation/creer", creer_la_simulation, methods=["POST"])
    application.add_api_route("/api/simulation/pas", jouer_un_pas, methods=["POST"])

    # Tout le reste est la page : web/index.html et ses fichiers.
    application.mount("/", PageSansCache(directory=DOSSIER_WEB, html=True))
    return application
