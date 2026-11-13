"""Story 2.5 : la zone complète (3 centres, sources, connexions) se charge, et son graphe
de navigation est fortement connexe.

networkx sert ici d'outil de vérification (il est interdit dans zc/, pas dans les tests).
"""

from pathlib import Path

import networkx as nx
import pytest

from zc.chargement import charger_zone
from zc.modele import Arete, Zone

FICHIER = Path(__file__).resolve().parent.parent / "donnees" / "zone.json"


@pytest.fixture(scope="module")
def zone() -> Zone:
    return charger_zone(FICHIER)


def ajouter_arete(g: nx.DiGraph, a: Arete, seulement_pmr: bool) -> None:
    """Ajoute une arête dans le sens autorisé (les deux sens si bidirectionnelle)."""
    if seulement_pmr and not a.pmr:
        return
    g.add_edge(a.source, a.cible)
    if a.sens == "bidirectionnel":
        g.add_edge(a.cible, a.source)


def graphe_de_navigation(zone: Zone, seulement_pmr: bool = False) -> nx.DiGraph:
    """Tous les nœuds de tous les centres, les sources, les couloirs et les connexions."""
    g = nx.DiGraph()
    for c in zone.centres:
        for n in c.centre.noeuds:
            g.add_node(n.id)
        for a in c.centre.aretes:
            ajouter_arete(g, a, seulement_pmr)
    for s in zone.sources:
        g.add_node(s.id)
    for a in zone.connexions:
        ajouter_arete(g, a, seulement_pmr)
    return g


def test_trois_centres_et_au_moins_trois_sources(zone: Zone) -> None:
    assert [c.id for c in zone.centres] == ["A", "B", "C"]
    assert len(zone.sources) >= 3
    types = []
    for s in zone.sources:
        types.append(s.type)
    assert "parking" in types and "station" in types and "quartier" in types


def test_centres_simples_d_au_moins_12_noeuds_et_2_sorties(zone: Zone) -> None:
    # Story 2.7 : les centres simples ont été agrandis (PLAN.md § 6).
    for c in zone.centres[1:]:
        sorties = 0
        for n in c.centre.noeuds:
            if n.type == "sortie":
                sorties += 1
        assert len(c.centre.noeuds) >= 12, c.id
        assert sorties == 2, c.id


def test_une_issue_de_secours_ne_se_traverse_pas(zone: Zone) -> None:
    # Une sortie reliée à aucune connexion de la zone est une issue de secours : un seul
    # couloir y mène, sinon les visiteurs l'emprunteraient comme un passage.
    reliees = set()
    for a in zone.connexions:
        reliees.add(a.source)
        reliees.add(a.cible)
    for c in zone.centres:
        for n in c.centre.noeuds:
            if n.type == "sortie" and n.id not in reliees:
                couloirs = 0
                for a in c.centre.aretes:
                    if n.id in (a.source, a.cible):
                        couloirs += 1
                assert couloirs == 1, n.id


def test_graphe_de_navigation_fortement_connexe(zone: Zone) -> None:
    g = graphe_de_navigation(zone)
    nombre_de_noeuds = len(zone.sources)
    for c in zone.centres:
        nombre_de_noeuds += len(c.centre.noeuds)
    assert g.number_of_nodes() == nombre_de_noeuds
    assert nx.is_strongly_connected(g)


def test_chaque_magasin_accessible_en_fauteuil_aller_et_retour(zone: Zone) -> None:
    # Sans cela, l'itinéraire PMR (story 3.3) n'aurait pas toujours de solution, et un
    # visiteur PMR ne pourrait pas revenir à sa source (PLAN.md § 4.2).
    g = graphe_de_navigation(zone, seulement_pmr=True)
    for s in zone.sources:
        for c in zone.centres:
            for n in c.centre.noeuds:
                if n.type == "magasin":
                    assert nx.has_path(g, s.id, n.id), f"aller {s.id} → {n.id}"
                    assert nx.has_path(g, n.id, s.id), f"retour {n.id} → {s.id}"


def test_une_connexion_non_pmr_dans_la_zone(zone: Zone) -> None:
    # Pour que l'itinéraire PMR diffère du plus court chemin à l'échelle de la zone aussi.
    assert any(not a.pmr for a in zone.connexions)
