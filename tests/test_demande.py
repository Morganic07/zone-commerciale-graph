"""Story 4.2 : arrivées, visites de 1 à 3 magasins, retour à la source, part de PMR."""

from pathlib import Path

import pytest

from zc.chargement import charger_parametres, charger_zone
from zc.demande import Demande, ParametresDemande
from zc.simulation import DANS_NOEUD, PARTI, SUR_ARETE, Simulation

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = charger_parametres(RACINE / "donnees" / "parametres.json")


def journee(graine: int, part_pmr: float = 0.25) -> tuple[Simulation, Demande]:
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=graine)
    demande = Demande(sim, ParametresDemande(
        arrivees_par_minute={"P1": 12.0, "T1": 8.0, "Q1": 6.0},
        part_pmr=part_pmr, visite_min=30.0, visite_max=180.0, beta=2.0))
    return sim, demande


@pytest.fixture(scope="module")
def longue_journee() -> tuple[Simulation, Demande, list[str]]:
    """2 400 pas (40 minutes), en vérifiant la conservation à chaque pas."""
    sim, demande = journee(graine=42)
    problemes = []
    for _ in range(2400):
        demande.pas()
        if demande.crees != demande.presents() + demande.repartis:
            problemes.append(f"t = {sim.temps} : {demande.crees} créés, "
                             f"{demande.presents()} présents, {demande.repartis} repartis")
        for agent in sim.agents:
            if agent.pmr and agent.etat == SUR_ARETE and agent.arete is not None:
                if not sim.aretes[agent.arete].pmr:
                    problemes.append(f"agent PMR {agent.id} sur une arête non PMR")
    return sim, demande, problemes


def test_conservation_a_chaque_pas(longue_journee: tuple[Simulation, Demande,
                                                         list[str]]) -> None:
    _, demande, problemes = longue_journee
    assert problemes == []
    assert demande.crees > 500  # la journée a vraiment eu lieu


def test_les_visiteurs_reviennent_a_leur_source(longue_journee: tuple[Simulation, Demande,
                                                                      list[str]]) -> None:
    sim, demande, _ = longue_journee
    assert demande.repartis > 100
    for agent in sim.agents:
        if agent.etat == PARTI:
            assert agent.position == demande.visites[agent.id].source


def test_part_de_pmr_conforme(longue_journee: tuple[Simulation, Demande,
                                                    list[str]]) -> None:
    sim, _, _ = longue_journee
    pmr = 0
    for agent in sim.agents:
        if agent.pmr:
            pmr += 1
    # Plus de 500 tirages à 25 % : l'écart-type est d'environ 2 points.
    assert abs(pmr / len(sim.agents) - 0.25) < 0.06


def test_programme_de_1_a_3_magasins_d_un_meme_centre() -> None:
    # Le programme se vide au fil de la visite : on le contrôle à l'arrivée du visiteur,
    # c'est-à-dire juste après le pas où il a été créé.
    sim, demande = journee(graine=7)
    tailles = set()
    deja_vus = 0
    for _ in range(300):
        demande.pas()
        for agent in sim.agents[deja_vus:]:
            programme = demande.visites[agent.id].programme
            assert 1 <= len(programme) <= 3
            assert len(set(programme)) == len(programme)  # pas deux fois le même magasin
            centres = set()
            for magasin in programme:
                centres.add(magasin.split(":")[0])
            assert len(centres) == 1
            tailles.add(len(programme))
        deja_vus = len(sim.agents)
    assert tailles == {1, 2, 3}


def test_duree_de_visite_entre_les_bornes() -> None:
    sim, demande = journee(graine=8)
    debuts: dict[int, float] = {}
    durees = []
    for _ in range(900):
        demande.pas()
        for agent in sim.agents:
            visite = demande.visites[agent.id]
            dans_un_magasin = (agent.etat == DANS_NOEUD and len(agent.itineraire) == 0
                               and len(visite.programme) > 0)
            if dans_un_magasin and agent.id not in debuts:
                debuts[agent.id] = sim.temps
            if not dans_un_magasin and agent.id in debuts:
                durees.append(sim.temps - debuts.pop(agent.id))
    assert len(durees) > 50
    # Seule la borne basse est stricte : un visiteur peut rester plus que prévu si
    # l'arête par laquelle il doit sortir est saturée.
    for d in durees:
        assert d >= 30.0
    # Les durées couvrent bien l'intervalle [30, 180] s.
    assert min(durees) < 60.0 and max(durees) >= 150.0


def test_sans_pmr_aucun_agent_pmr() -> None:
    sim, demande = journee(graine=3, part_pmr=0.0)
    for _ in range(300):
        demande.pas()
    for agent in sim.agents:
        assert not agent.pmr


def test_meme_graine_meme_journee() -> None:
    etats = []
    for _ in range(2):
        sim, demande = journee(graine=11)
        for _ in range(400):
            demande.pas()
        etats.append(sim.etat())
    assert etats[0] == etats[1]
