"""Story 2.4 : le plan du centre détaillé contient tous les cas de PLAN.md § 6.

networkx sert ici d'outil de vérification (il est interdit dans zc/, pas dans les tests).
"""

from pathlib import Path

import networkx as nx
import pytest

from zc.chargement import charger_centre
from zc.modele import Centre

FICHIER = Path(__file__).resolve().parent.parent / "donnees" / "centres" / "A.json"


@pytest.fixture(scope="module")
def centre() -> Centre:
    return charger_centre(FICHIER)


def graphe_non_oriente(centre: Centre) -> nx.Graph:
    g = nx.Graph()
    for n in centre.noeuds:
        g.add_node(n.id)
    for a in centre.aretes:
        g.add_edge(a.source, a.cible)
    return g


def graphe_oriente(centre: Centre, seulement_pmr: bool = False) -> nx.DiGraph:
    """Graphe de circulation : une arête « unique » ne se parcourt que dans un sens."""
    g = nx.DiGraph()
    for n in centre.noeuds:
        g.add_node(n.id)
    for a in centre.aretes:
        if seulement_pmr and not a.pmr:
            continue
        g.add_edge(a.source, a.cible, longueur=a.longueur)
        if a.sens == "bidirectionnel":
            g.add_edge(a.cible, a.source, longueur=a.longueur)
    return g


def ids_du_type(centre: Centre, type_noeud: str) -> list[str]:
    resultat = []
    for n in centre.noeuds:
        if n.type == type_noeud:
            resultat.append(n.id)
    return resultat


def test_deux_sorties_sur_des_cotes_opposes(centre: Centre) -> None:
    sorties = ids_du_type(centre, "sortie")
    assert len(sorties) >= 2
    plus_a_gauche = min(centre.noeuds, key=lambda n: n.x)
    plus_a_droite = max(centre.noeuds, key=lambda n: n.x)
    assert plus_a_gauche.id in sorties and plus_a_droite.id in sorties


def test_au_moins_six_magasins_et_un_sanitaire(centre: Centre) -> None:
    assert len(ids_du_type(centre, "magasin")) >= 6
    assert len(ids_du_type(centre, "sanitaire")) >= 1


def test_tout_le_centre_est_accessible_dans_les_deux_sens(centre: Centre) -> None:
    # Depuis n'importe quel nœud, on peut aller partout en respectant les sens uniques.
    assert nx.is_strongly_connected(graphe_oriente(centre))


def test_au_moins_un_cycle(centre: Centre) -> None:
    assert len(nx.cycle_basis(graphe_non_oriente(centre))) >= 1


def test_un_goulot_sur_un_passage_frequente(centre: Centre) -> None:
    carrefours = ids_du_type(centre, "carrefour")
    couloirs = [a for a in centre.aretes if a.source in carrefours and a.cible in carrefours]
    plus_large = max(a.capacite_max for a in couloirs)
    goulots = [a for a in couloirs if a.capacite_max <= plus_large / 2]
    assert goulots, "aucun couloir deux fois moins capacitaire que le plus large"

    # Fréquenté : le goulot est sur le plus court chemin d'une sortie à l'autre.
    ouest, est = ids_du_type(centre, "sortie")[:2]
    chemin = nx.shortest_path(graphe_oriente(centre), ouest, est, weight="longueur")
    paires = []
    for i in range(len(chemin) - 1):
        paires.append((chemin[i], chemin[i + 1]))
    sur_le_chemin = False
    for g in goulots:
        if (g.source, g.cible) in paires or (g.cible, g.source) in paires:
            sur_le_chemin = True
    assert sur_le_chemin


def test_arete_non_pmr_contournable_par_un_chemin_pmr_plus_long(centre: Centre) -> None:
    non_pmr = [a for a in centre.aretes if not a.pmr]
    assert non_pmr, "aucune arête non PMR"
    pmr = graphe_oriente(centre, seulement_pmr=True)
    for a in non_pmr:
        detour = nx.shortest_path_length(pmr, a.source, a.cible, weight="longueur")
        assert detour > a.longueur


def test_au_moins_une_arete_a_sens_unique(centre: Centre) -> None:
    assert any(a.sens == "unique" for a in centre.aretes)


def test_noeuds_sans_capteur_dont_un_sur_un_chemin_d_evacuation(centre: Centre) -> None:
    sans_capteur = [n.id for n in centre.noeuds if not n.capteur_fumee]
    assert len(sans_capteur) >= 2

    # Chemin d'évacuation : le plus court chemin d'un magasin vers la sortie la plus proche.
    g = graphe_oriente(centre)
    sorties = ids_du_type(centre, "sortie")
    sur_un_chemin = False
    for magasin in ids_du_type(centre, "magasin"):
        chemins = [nx.shortest_path(g, magasin, s, weight="longueur") for s in sorties]
        plus_court = min(chemins, key=lambda c: nx.path_weight(g, c, "longueur"))
        if any(n in sans_capteur for n in plus_court):
            sur_un_chemin = True
    assert sur_un_chemin


def test_un_feu_possible_pres_d_une_sortie(centre: Centre) -> None:
    # Un magasin à au plus deux couloirs d'une sortie : le feu peut bloquer cette sortie.
    g = graphe_non_oriente(centre)
    proches = []
    for magasin in ids_du_type(centre, "magasin"):
        for sortie in ids_du_type(centre, "sortie"):
            if nx.shortest_path_length(g, magasin, sortie) <= 2:
                proches.append(magasin)
    assert proches
