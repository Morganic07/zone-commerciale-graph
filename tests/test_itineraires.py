"""Story 3.3 : itinéraire d'une région vers un centre, pour les trois critères.

Le plan du centre A est provisoire (story 2.6) : ces tests ne citent aucun de ses
nœuds, ils les retrouvent par leur type.
"""

from pathlib import Path

import pytest

from zc.chargement import charger_zone
from zc.chemins import dijkstra, itineraire
from zc.modele import Arete, Zone
from zc.navigation import graphe_de_la_zone

ZONE = Path(__file__).resolve().parent.parent / "donnees" / "zone.json"


@pytest.fixture
def zone() -> Zone:
    return charger_zone(ZONE)


def toutes_les_aretes(zone: Zone) -> list[Arete]:
    aretes = list(zone.connexions)
    for c in zone.centres:
        aretes += c.centre.aretes
    return aretes


def existe_une_arete_pmr(aretes: list[Arete], u: str, v: str) -> bool:
    """Y a-t-il une arête PMR qui permet d'aller de u à v ?"""
    for a in aretes:
        if not a.pmr:
            continue
        if a.source == u and a.cible == v:
            return True
        if a.sens == "bidirectionnel" and a.source == v and a.cible == u:
            return True
    return False


def ids_du_type(zone: Zone, centre: str, type_noeud: str) -> list[str]:
    resultat = []
    for c in zone.centres:
        if c.id == centre:
            for n in c.centre.noeuds:
                if n.type == type_noeud:
                    resultat.append(n.id)
    return resultat


def destinations(zone: Zone) -> list[tuple[str, str | None]]:
    """Chaque centre, sans magasin puis vers chacun de ses magasins."""
    resultat: list[tuple[str, str | None]] = []
    for c in zone.centres:
        resultat.append((c.id, None))
        for identifiant in ids_du_type(zone, c.id, "magasin"):
            resultat.append((c.id, identifiant.split(":")[1]))
    return resultat


def test_pmr_sans_arete_non_pmr_et_jamais_plus_court(zone: Zone) -> None:
    aretes = toutes_les_aretes(zone)
    for s in zone.sources:
        for centre, magasin in destinations(zone):
            court = itineraire(zone, s.id, centre, "court", magasin=magasin)
            pmr = itineraire(zone, s.id, centre, "pmr", magasin=magasin)
            assert court is not None and pmr is not None, (s.id, centre, magasin)
            cout_pmr, chemin_pmr = pmr
            for i in range(len(chemin_pmr) - 1):
                assert existe_une_arete_pmr(aretes, chemin_pmr[i], chemin_pmr[i + 1])
            assert cout_pmr >= court[0]


def test_l_itineraire_pmr_contourne_la_connexion_non_pmr(zone: Zone) -> None:
    # Au moins un trajet emprunte la connexion non PMR en plus court chemin ; l'itinéraire
    # PMR l'évite alors, et coûte plus cher.
    non_pmr = []
    for a in zone.connexions:
        if not a.pmr:
            non_pmr.append((a.source, a.cible))
    assert non_pmr

    def emprunte(chemin: list[str]) -> bool:
        for i in range(len(chemin) - 1):
            pas = (chemin[i], chemin[i + 1])
            if pas in non_pmr or (pas[1], pas[0]) in non_pmr:
                return True
        return False

    contournements = 0
    for s in zone.sources:
        for c in zone.centres:
            court = itineraire(zone, s.id, c.id, "court")
            pmr = itineraire(zone, s.id, c.id, "pmr")
            assert court is not None and pmr is not None
            if emprunte(court[1]):
                assert not emprunte(pmr[1])
                assert pmr[0] > court[0]
                contournements += 1
    assert contournements >= 1


@pytest.mark.parametrize("critere", ["court", "encombre", "pmr"])
def test_sans_magasin_on_s_arrete_a_la_sortie_la_moins_couteuse(zone: Zone,
                                                                 critere: str) -> None:
    graphe = graphe_de_la_zone(zone, critere, beta=2.0)
    for s in zone.sources:
        distances, _ = dijkstra(graphe, s.id)
        for c in zone.centres:
            resultat = itineraire(zone, s.id, c.id, critere, beta=2.0)
            assert resultat is not None
            cout, chemin = resultat
            sorties = ids_du_type(zone, c.id, "sortie")
            assert chemin[0] == s.id and chemin[-1] in sorties
            meilleur = None
            for sortie in sorties:
                if sortie in distances and (meilleur is None or distances[sortie] < meilleur):
                    meilleur = distances[sortie]
            assert cout == meilleur


def test_avec_magasin_le_chemin_entre_par_une_sortie(zone: Zone) -> None:
    magasin = ids_du_type(zone, "A", "magasin")[0]
    cout, chemin = itineraire(zone, "P1", "A", "court", magasin=magasin.split(":")[1])
    assert chemin[0] == "P1" and chemin[-1] == magasin
    sorties = ids_du_type(zone, "A", "sortie")
    entrees = []
    for n in chemin:
        if n in sorties:
            entrees.append(n)
    assert entrees  # on entre dans le centre par une de ses sorties


def test_centre_inconnu_refuse(zone: Zone) -> None:
    with pytest.raises(ValueError, match="Z"):
        itineraire(zone, "P1", "Z", "court")


def test_source_ou_magasin_inconnus_refuses(zone: Zone) -> None:
    # Une faute de frappe ne doit pas passer pour « aucun chemin ».
    with pytest.raises(ValueError, match="source « XX »"):
        itineraire(zone, "XX", "A", "court")
    with pytest.raises(ValueError, match="« M99 » n'existe pas"):
        itineraire(zone, "P1", "A", "court", magasin="M99")


def test_magasin_bloque_aucun_chemin(zone: Zone) -> None:
    magasin = ids_du_type(zone, "A", "magasin")[0]
    zone.centres[0].centre.noeud(magasin).statut = "bloqué"
    assert itineraire(zone, "P1", "A", "court", magasin=magasin.split(":")[1]) is None
