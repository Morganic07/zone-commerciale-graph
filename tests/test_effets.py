"""Story 5.3 : effets de la fumée sur la circulation (vitesse, débit, règle de la
moitié sur une arête qui se bloque)."""

from pathlib import Path

import pytest

from zc.chargement import charger_centre, charger_parametres
from zc.modele import CentreZone, Zone
from zc.simulation import DANS_NOEUD, SUR_ARETE, Simulation

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = charger_parametres(RACINE / "donnees" / "parametres.json")


def simulation(reduction_fumee: float = 0.5) -> Simulation:
    """Centre de la consigne : S1 – C1 (8 m, 10 pers/s) – E1 (12 m, 15 pers/s)."""
    centre = charger_centre(RACINE / "tests" / "donnees" / "exemple_consigne.json")
    zone = Zone(centres=[CentreZone(id="X", centre=centre)], sources=[], connexions=[])
    return Simulation(zone, PARAMETRES, graine=1, reduction_fumee=reduction_fumee)


# --- vitesse et débit ------------------------------------------------------------------

def test_la_vitesse_baisse_avec_la_fumee() -> None:
    avancees = []
    for fumee in [0.0, 40.0, 80.0]:
        sim = simulation()
        sim.noeuds["C1"].niveau_fumee = fumee
        agent = sim.ajouter_agent("S1", ["C1"])
        sim.pas()  # il s'engage
        sim.pas()  # il marche un pas
        avancees.append(agent.avancee)
    # facteur = 1 − 0,5 × fumée / 100 : 1 ; 0,8 ; 0,6.
    assert avancees == pytest.approx([1.34, 1.34 * 0.8, 1.34 * 0.6])


def test_le_debit_baisse_avec_la_fumee() -> None:
    entrees = []
    for fumee in [0.0, 40.0, 80.0]:
        sim = simulation()
        sim.noeuds["S1"].niveau_fumee = fumee
        for _ in range(20):
            sim.ajouter_agent("S1", ["C1"])
        sim.pas()
        entrees.append(sim.flux[0])
    # S1 – C1 : 10 pers/s × 1 ; × 0,8 ; × 0,6 → 10, 8, 6 entrées.
    assert entrees == [10, 8, 6]


def test_au_moins_une_entree_par_pas_tant_que_l_arete_n_est_pas_bloquee() -> None:
    sim = simulation(reduction_fumee=0.9)
    sim.aretes[0].capacite_max = 1.2
    sim.noeuds["S1"].niveau_fumee = 100.0  # facteur 0,1 : 0,12 pers/s
    for _ in range(3):
        sim.ajouter_agent("S1", ["C1"])
    sim.pas()
    assert sim.flux[0] == 1


def test_sans_fumee_rien_ne_change() -> None:
    sim = simulation()
    assert sim.facteur_fumee(0) == 1.0


@pytest.mark.parametrize("k", [-0.1, 1.0, 1.5])
def test_coefficient_hors_bornes_refuse(k: float) -> None:
    with pytest.raises(ValueError, match="k"):
        simulation(reduction_fumee=k)


# --- règle de la moitié ----------------------------------------------------------------

def engage_sur_c1_e1(avancee: float) -> tuple[Simulation, object]:
    """Un agent sur C1 – E1 (12 m), à `avancee` mètres de C1, en route vers E1."""
    sim = simulation()
    agent = sim.ajouter_agent("C1", ["E1"])
    sim.pas()
    assert agent.etat == SUR_ARETE
    agent.avancee = avancee
    return sim, agent


def test_a_40_pour_cent_il_fait_demi_tour() -> None:
    sim, agent = engage_sur_c1_e1(avancee=0.4 * 12)
    sim.aretes[1].statut = "bloqué"
    for _ in range(20):
        sim.pas()
    assert agent.etat == DANS_NOEUD and agent.position == "C1"  # revenu à son départ
    assert agent.itineraire == ["E1"]  # sa destination reste E1, à recalculer


def test_a_60_pour_cent_il_continue() -> None:
    sim, agent = engage_sur_c1_e1(avancee=0.6 * 12)
    sim.aretes[1].statut = "bloqué"
    for _ in range(20):
        sim.pas()
    assert agent.etat == DANS_NOEUD and agent.position == "E1"
    assert agent.itineraire == []


def test_demi_tour_a_la_distance_deja_parcourue() -> None:
    # À 4,8 m de C1, il lui reste 4,8 m pour revenir : 4 pas à 1,34 m/s (5,36 m).
    sim, agent = engage_sur_c1_e1(avancee=4.8)
    sim.aretes[1].statut = "bloqué"
    for _ in range(3):
        sim.pas()
        assert agent.etat == SUR_ARETE
    sim.pas()
    assert agent.position == "C1" and agent.etat == DANS_NOEUD


def test_pas_de_demi_tours_en_boucle() -> None:
    # Après un demi-tour à 40 %, il repart à 60 % de l'arête dans l'autre sens : la règle
    # le fait continuer jusqu'à C1, sans nouveau demi-tour.
    sim, agent = engage_sur_c1_e1(avancee=0.4 * 12)
    sim.aretes[1].statut = "bloqué"
    sim.pas()
    # Tant qu'il est sur l'arête, il se dirige vers C1, sans nouveau changement d'avis.
    pas_sur_l_arete = 0
    while agent.etat == SUR_ARETE:
        assert agent.itineraire[0] == "C1"
        sim.pas()
        pas_sur_l_arete += 1
    assert pas_sur_l_arete >= 1
    assert agent.position == "C1"


def test_personne_ne_s_engage_sur_une_arete_bloquee() -> None:
    sim = simulation()
    sim.aretes[0].statut = "bloqué"
    agent = sim.ajouter_agent("S1", ["C1"])
    for _ in range(5):
        sim.pas()
    assert agent.etat == DANS_NOEUD and agent.position == "S1"
