"""Story 2.5 : stations B et C, et réseau complet."""

from pathlib import Path

import networkx as nx

from moteur.chargement import charger_reseau

RESEAU = Path(__file__).resolve().parent.parent / "donnees" / "reseau.json"


def test_trois_stations_et_les_trois_types_de_source() -> None:
    reseau = charger_reseau(RESEAU)
    ids = []
    for station_du_reseau in reseau.stations:
        ids.append(station_du_reseau.id)
    assert ids == ["A", "B", "C"]
    types = []
    for source in reseau.sources:
        types.append(source.type)
    assert "spatioport" in types
    assert "habitat" in types
    assert "relais" in types


def test_b_et_c_ont_douze_noeuds_et_deux_sorties() -> None:
    reseau = charger_reseau(RESEAU)
    for station_du_reseau in reseau.stations:
        if station_du_reseau.id == "A":
            continue
        noeuds = station_du_reseau.station.noeuds
        sorties = 0
        for noeud in noeuds:
            if noeud.type == "sortie":
                sorties = sorties + 1
        assert len(noeuds) >= 12, station_du_reseau.id
        assert sorties >= 2, station_du_reseau.id


def test_graphe_de_navigation_complet_fortement_connexe() -> None:
    reseau = charger_reseau(RESEAU)
    graphe = nx.DiGraph()
    aretes = list(reseau.connexions)
    for station_du_reseau in reseau.stations:
        for noeud in station_du_reseau.station.noeuds:
            graphe.add_node(noeud.id)
        aretes = aretes + station_du_reseau.station.aretes
    for source in reseau.sources:
        graphe.add_node(source.id)
    for arete in aretes:
        graphe.add_edge(arete.source, arete.cible)
        if arete.sens == "bidirectionnel":
            graphe.add_edge(arete.cible, arete.source)
    # Toutes les extrémités d'arêtes existent : aucun nœud n'a été créé par add_edge.
    assert graphe.number_of_nodes() == 13 + 12 + 12 + 3
    assert nx.is_strongly_connected(graphe)
