"""Story 4.4 : taux d'occupation (nœuds et arêtes), palette à 5 niveaux, file d'attente."""

from pathlib import Path

import pytest

from zc.chargement import charger_centre, charger_parametres, charger_zone
from zc.demande import Demande, ParametresDemande
from zc.modele import CentreZone, Zone
from zc.palette import niveau
from zc.simulation import Simulation

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = charger_parametres(RACINE / "donnees" / "parametres.json")


# --- palette aux bornes exactes --------------------------------------------------------

@pytest.mark.parametrize("taux, attendu", [
    (0.0, 1), (0.19, 1),
    (0.2, 2), (0.39, 2),
    (0.4, 3), (0.59, 3),
    (0.6, 4), (0.79, 4),
    (0.8, 5), (1.0, 5),
])
def test_niveau_aux_bornes(taux: float, attendu: int) -> None:
    assert niveau(taux) == attendu


def test_seuils_de_la_consigne_sur_des_bornes() -> None:
    # Vert (τ < 0,4) → niveaux 1-2 ; orange (0,4 ≤ τ < 0,8) → 3-4 ; rouge (τ ≥ 0,8) → 5.
    assert niveau(0.399) <= 2 and niveau(0.4) == 3
    assert niveau(0.799) == 4 and niveau(0.8) == 5


def test_taux_calcules_exactement() -> None:
    # 1/5 et 4/5 tombent exactement sur les bornes.
    assert niveau(1 / 5) == 2
    assert niveau(4 / 5) == 5


# --- taux dans la simulation -----------------------------------------------------------

def zone_exemple(capacite_c1: int = 60) -> Zone:
    centre = charger_centre(RACINE / "tests" / "donnees" / "exemple_consigne.json")
    centre.noeud("C1").capacite_max = capacite_c1
    return Zone(centres=[CentreZone(id="X", centre=centre)], sources=[], connexions=[])


def test_taux_d_arete_egal_flux_sur_capacite() -> None:
    # S1 – C1 : 10 pers/s ; 4 agents s'engagent au premier pas → τ = 4 / 10 = 0,4.
    sim = Simulation(zone_exemple(), PARAMETRES, graine=1)
    for _ in range(4):
        sim.ajouter_agent("S1", ["C1"])
    sim.pas()
    assert sim.flux[0] == 4
    assert sim.aretes[0].taux == pytest.approx(0.4)
    assert niveau(sim.aretes[0].taux) == 3
    # Au pas suivant, plus personne n'entre : τ retombe à 0.
    sim.pas()
    assert sim.aretes[0].taux == 0.0


def test_taux_de_noeud() -> None:
    sim = Simulation(zone_exemple(), PARAMETRES, graine=1)
    for _ in range(12):
        sim.ajouter_agent("S1", [])
    assert sim.noeuds["S1"].taux_occupation() == pytest.approx(12 / 40)
    assert niveau(sim.noeuds["S1"].taux_occupation()) == 2


def test_file_d_attente_exposee_a_part() -> None:
    # C1 n'a que 2 places, 5 agents arrivent : 3 attendent au bout de S1 – C1. L'arête,
    # où plus personne n'entre, a un taux nul : seule la file d'attente le montre.
    sim = Simulation(zone_exemple(capacite_c1=2), PARAMETRES, graine=3)
    for _ in range(5):
        sim.ajouter_agent("S1", ["C1"])
    for _ in range(15):
        sim.pas()
    assert sim.noeuds["C1"].occupation == 2
    assert sim.attente[0] == 3
    assert sim.aretes[0].taux == 0.0


# --- le taux évolue pendant une journée (il alimente le critère « moins encombré ») ---

def test_le_taux_des_aretes_evolue_pendant_une_journee() -> None:
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=4)
    demande = Demande(sim, ParametresDemande(
        arrivees_par_minute={"P1": 60.0}, part_pmr=0.0, visite_min=30.0,
        visite_max=60.0, beta=2.0))
    maximum = 0.0
    for _ in range(300):
        demande.pas()
        for a in sim.aretes:
            maximum = max(maximum, a.taux)
            assert a.taux <= 1.0  # φ_e ≤ c_e × Δt
    assert maximum > 0.0
