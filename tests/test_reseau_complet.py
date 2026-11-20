"""Story 2.5 : stations B et C, et réseau complet."""

from pathlib import Path

import networkx as nx

from moteur.chargement import charger_reseau

RESEAU = Path(__file__).resolve().parent.parent / "donnees" / "reseau.json"


def test_trois_stations_reliees_par_leurs_sas() -> None:
    # Les sas sont les nœuds sources du réseau : pas de point d'arrivée à part.
    reseau = charger_reseau(RESEAU)
    ids = []
    sas = []
    for station_du_reseau in reseau.stations:
        ids.append(station_du_reseau.id)
        for noeud in station_du_reseau.station.noeuds:
            if noeud.type == "sortie":
                sas.append(noeud.id)
    assert ids == ["A", "B", "C"]
    assert reseau.sources == []
    for tunnel in reseau.connexions:
        assert tunnel.source in sas
        assert tunnel.cible in sas


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
    assert graphe.number_of_nodes() == 12 + 12 + 12
    assert nx.is_strongly_connected(graphe)


def test_deux_aretes_non_pmr_par_station() -> None:
    reseau = charger_reseau(RESEAU)
    for station_du_reseau in reseau.stations:
        non_pmr = 0
        for arete in station_du_reseau.station.aretes:
            if not arete.pmr:
                non_pmr = non_pmr + 1
        assert non_pmr >= 2, station_du_reseau.id


def test_un_sas_de_c_relie_deux_fois_a_a() -> None:
    # On compte, pour chaque sas de C, les tunnels qui le relient à la station A.
    reseau = charger_reseau(RESEAU)
    liens_vers_a: dict[str, int] = {}
    for tunnel in reseau.connexions:
        paires = [(tunnel.source, tunnel.cible), (tunnel.cible, tunnel.source)]
        for sas_c, autre in paires:
            if sas_c.startswith("C:") and autre.startswith("A:"):
                if sas_c not in liens_vers_a:
                    liens_vers_a[sas_c] = 0
                liens_vers_a[sas_c] = liens_vers_a[sas_c] + 1
    assert max(liens_vers_a.values()) == 2


def test_tout_le_reseau_reste_accessible_en_fauteuil() -> None:
    # Les passages non PMR doivent pouvoir se contourner : sans eux, tout reste relié.
    reseau = charger_reseau(RESEAU)
    graphe = nx.Graph()
    aretes = list(reseau.connexions)
    for station_du_reseau in reseau.stations:
        for noeud in station_du_reseau.station.noeuds:
            graphe.add_node(noeud.id)
        aretes = aretes + station_du_reseau.station.aretes
    for arete in aretes:
        if arete.pmr:
            graphe.add_edge(arete.source, arete.cible)
    assert nx.is_connected(graphe)
