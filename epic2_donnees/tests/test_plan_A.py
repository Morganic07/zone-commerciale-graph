"""Story 2.4 : le plan de la station A contient les cas demandés par PLAN.md § 6.

Ces tests ne dépendent pas des identifiants du plan : ils restent valables quand le
groupe remplacera le plan provisoire par le sien.
"""

from pathlib import Path

import networkx as nx

from epic2_donnees.moteur.chargement import charger_reseau
from epic2_donnees.moteur.modele import Arete, Reseau, Station

RESEAU = Path(__file__).resolve().parent.parent / "donnees" / "reseau.json"


def station_a(reseau: Reseau) -> Station:
    for station_du_reseau in reseau.stations:
        if station_du_reseau.id == "A":
            return station_du_reseau.station
    raise AssertionError("pas de station A dans le réseau")


def graphe_oriente(aretes: list[Arete], pmr_seulement: bool) -> nx.DiGraph:
    """Graphe de navigation : deux arcs par arête bidirectionnelle, un seul sinon."""
    graphe = nx.DiGraph()
    for arete in aretes:
        if pmr_seulement and not arete.pmr:
            continue
        graphe.add_edge(arete.source, arete.cible, longueur=arete.longueur)
        if arete.sens == "bidirectionnel":
            graphe.add_edge(arete.cible, arete.source, longueur=arete.longueur)
    return graphe


def test_deux_sas_aux_deux_extremites() -> None:
    # Les sas sont les sorties de la station, et aussi les points d'arrivée des visiteurs.
    station = station_a(charger_reseau(RESEAU))
    sas = []
    for noeud in station.noeuds:
        if noeud.type == "sortie":
            sas.append(noeud.id)
    assert len(sas) >= 2
    plus_a_gauche = min(station.noeuds, key=lambda noeud: noeud.x or 0)
    plus_a_droite = max(station.noeuds, key=lambda noeud: noeud.x or 0)
    assert plus_a_gauche.id in sas
    assert plus_a_droite.id in sas


def test_six_modules_et_un_sanitaire() -> None:
    station = station_a(charger_reseau(RESEAU))
    types = []
    for noeud in station.noeuds:
        types.append(noeud.type)
    assert types.count("module") >= 6
    assert types.count("sanitaire") >= 1


def test_au_moins_un_cycle() -> None:
    station = station_a(charger_reseau(RESEAU))
    graphe = graphe_oriente(station.aretes, False).to_undirected()
    assert len(nx.cycle_basis(graphe)) >= 1


def test_un_goulot() -> None:
    # Goulot : une arête entre deux jonctions qui laisse passer moins de monde par seconde
    # que les arêtes des sas.
    station = station_a(charger_reseau(RESEAU))
    types = {}
    for noeud in station.noeuds:
        types[noeud.id] = noeud.type
    capacites_des_sas = []
    for arete in station.aretes:
        if types[arete.source] == "sortie" or types[arete.cible] == "sortie":
            capacites_des_sas.append(arete.capacite_max)
    goulots = []
    for arete in station.aretes:
        entre_jonctions = types[arete.source] == "carrefour" and types[arete.cible] == "carrefour"
        if entre_jonctions and arete.capacite_max < min(capacites_des_sas):
            goulots.append(arete)
    assert len(goulots) >= 1


def test_arete_non_pmr_contournable_par_un_chemin_pmr_plus_long() -> None:
    station = station_a(charger_reseau(RESEAU))
    graphe_pmr = graphe_oriente(station.aretes, True)
    contournables = []
    for arete in station.aretes:
        if arete.pmr:
            continue
        detour = nx.shortest_path_length(graphe_pmr, arete.source, arete.cible, "longueur")
        if detour > arete.longueur:
            contournables.append(arete)
    assert len(contournables) >= 1


def test_deux_noeuds_sans_capteur_dont_un_sur_un_chemin_d_evacuation() -> None:
    station = station_a(charger_reseau(RESEAU))
    sans_capteur = []
    sorties = []
    for noeud in station.noeuds:
        if not noeud.capteur_fumee:
            sans_capteur.append(noeud.id)
        if noeud.type == "sortie":
            sorties.append(noeud.id)
    assert len(sans_capteur) >= 2

    # Chemins vers la sortie la plus proche : Dijkstra depuis les sorties, graphe inversé.
    inverse = graphe_oriente(station.aretes, False).reverse()
    chemins = nx.multi_source_dijkstra_path(inverse, set(sorties), weight="longueur")
    sur_un_chemin = False
    for depart in chemins:
        if depart in sans_capteur:
            continue
        if len(set(chemins[depart]) & set(sans_capteur)) > 0:
            sur_un_chemin = True
    assert sur_un_chemin
