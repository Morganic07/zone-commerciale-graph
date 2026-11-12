"""Story 4.1 : pas de temps, contraintes de capacité et tirage au sort reproductible."""

import random
from pathlib import Path

import pytest

from zc.chargement import charger_centre, charger_parametres, charger_zone
from zc.chemins import itineraire
from zc.modele import CentreZone, Zone
from zc.simulation import DANS_NOEUD, EN_ATTENTE, SUR_ARETE, Simulation

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = charger_parametres(RACINE / "donnees" / "parametres.json")


def magasins(zone: Zone) -> list[tuple[str, str]]:
    """(centre, magasin) pour chaque magasin de la zone."""
    resultat = []
    for c in zone.centres:
        for n in c.centre.noeuds:
            if n.type == "magasin":
                resultat.append((c.id, n.id.split(":")[1]))
    return resultat


def simuler(graine: int, pas: int, verifier: bool) -> Simulation:
    """Une zone qui se remplit : à chaque pas, 0 à 3 visiteurs arrivent d'une source et
    vont vers un magasin tiré au hasard. Les magasins finissent par être pleins, ce qui
    crée des files d'attente : c'est là que les contraintes sont mises à l'épreuve."""
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=graine)
    hasard = random.Random(graine)
    destinations = magasins(zone)
    for _ in range(pas):
        for _ in range(hasard.randint(0, 3)):
            source = hasard.choice(zone.sources).id
            centre, magasin = hasard.choice(destinations)
            pmr = hasard.random() < 0.1
            critere = "pmr" if pmr else "court"
            trajet = itineraire(zone, source, centre, critere, magasin=magasin)
            assert trajet is not None
            sim.ajouter_agent(source, trajet[1][1:], pmr=pmr)
        sim.pas()
        if verifier:
            verifier_contraintes(sim)
    return sim


def verifier_contraintes(sim: Simulation) -> None:
    # o_v ≤ c_v, et l'occupation compte exactement les agents présents dans le nœud.
    presents: dict[str, int] = {}
    for agent in sim.agents:
        if agent.etat == DANS_NOEUD and agent.position in sim.noeuds:
            presents[agent.position] = presents.get(agent.position, 0) + 1
    for identifiant in sim.noeuds:
        noeud = sim.noeuds[identifiant]
        assert 0 <= noeud.occupation <= noeud.capacite_max, identifiant
        assert noeud.occupation == presents.get(identifiant, 0), identifiant
    # φ_e ≤ c_e × Δt.
    for i in range(len(sim.aretes)):
        assert sim.flux[i] <= sim.aretes[i].capacite_max * sim.dt, i


# --- le critère de la story ------------------------------------------------------------

def test_contraintes_respectees_a_chaque_pas_sur_1000_pas() -> None:
    sim = simuler(graine=41, pas=1000, verifier=True)
    # La simulation a vraiment été chargée : des agents attendent devant des nœuds
    # pleins, sinon les contraintes n'auraient pas été mises à l'épreuve.
    etats = set()
    for agent in sim.agents:
        etats.add(agent.etat)
    assert len(sim.agents) > 1000
    assert EN_ATTENTE in etats


def test_meme_graine_meme_simulation() -> None:
    assert simuler(graine=42, pas=300, verifier=False).etat() == \
        simuler(graine=42, pas=300, verifier=False).etat()


def test_autre_graine_autre_simulation() -> None:
    assert simuler(graine=42, pas=300, verifier=False).etat() != \
        simuler(graine=43, pas=300, verifier=False).etat()


# --- petits cas calculés à la main -----------------------------------------------------

def zone_exemple(capacite_c1: int = 60) -> Zone:
    """Le centre de l'exemple de la consigne (S1 – C1 – E1), seul dans une zone."""
    centre = charger_centre(RACINE / "tests" / "donnees" / "exemple_consigne.json")
    centre.noeud("C1").capacite_max = capacite_c1
    return Zone(centres=[CentreZone(id="X", centre=centre)], sources=[], connexions=[])


def test_un_agent_avance_a_sa_vitesse() -> None:
    # S1 → C1 : 8 m. À 1,34 m/s, il lui faut 6 pas (8,04 m) pour arriver au bout.
    sim = Simulation(zone_exemple(), PARAMETRES, graine=1)
    agent = sim.ajouter_agent("S1", ["C1"])
    sim.pas()  # il s'engage sur l'arête (et commence à marcher au pas suivant)
    assert agent.etat == SUR_ARETE and sim.flux[0] == 1
    for _ in range(5):
        sim.pas()
        assert agent.etat == SUR_ARETE
    sim.pas()
    assert agent.etat == DANS_NOEUD and agent.position == "C1"
    assert sim.noeuds["C1"].occupation == 1 and sim.noeuds["S1"].occupation == 0


def test_agent_pmr_plus_lent() -> None:
    sim = Simulation(zone_exemple(), PARAMETRES, graine=1)
    valide = sim.ajouter_agent("S1", ["C1"])
    pmr = sim.ajouter_agent("S1", ["C1"], pmr=True)
    sim.pas()
    sim.pas()
    assert valide.avancee == pytest.approx(1.34)
    assert pmr.avancee == pytest.approx(0.69)


def test_noeud_plein_les_autres_attendent() -> None:
    # C1 n'a qu'une place : sur 3 agents arrivés ensemble, un seul entre.
    sim = Simulation(zone_exemple(capacite_c1=1), PARAMETRES, graine=5)
    agents = []
    for _ in range(3):
        agents.append(sim.ajouter_agent("S1", ["C1"]))
    for _ in range(20):
        sim.pas()
        verifier_contraintes(sim)
    entres = 0
    for a in agents:
        if a.etat == DANS_NOEUD and a.position == "C1":
            entres += 1
    assert entres == 1
    assert sim.noeuds["C1"].occupation == 1


def test_arete_limitee_a_l_arrondi_inferieur_de_c_fois_dt() -> None:
    # Capacité de S1 – C1 ramenée à 2,5 pers/s : ⌊2,5 × 1⌋ = 2 entrées par pas, pas 3.
    sim = Simulation(zone_exemple(), PARAMETRES, graine=2)
    for _ in range(25):
        sim.ajouter_agent("S1", ["C1"])
    sim.aretes[0].capacite_max = 2.5
    sim.pas()
    assert sim.flux[0] == 2
    sim.pas()
    assert sim.flux[0] == 2


def test_arete_de_moins_d_une_personne_par_pas_refusee() -> None:
    # Une porte de 0,6 m (0,79 pers/s) laisserait passer ⌊0,79 × 1⌋ = 0 personne par pas.
    zone = zone_exemple()
    zone.centres[0].centre.aretes[0].capacite_max = 0.79
    with pytest.raises(ValueError, match="moins d'une personne par pas"):
        Simulation(zone, PARAMETRES, graine=1)
    # Avec un pas de 2 s, elle laisse passer ⌊1,58⌋ = 1 personne : accepté.
    Simulation(zone, PARAMETRES, graine=1, dt=2.0)


def test_itineraire_impossible_refuse() -> None:
    sim = Simulation(zone_exemple(), PARAMETRES, graine=1)
    with pytest.raises(ValueError, match="aucune arête"):
        sim.ajouter_agent("S1", ["E1"])  # S1 et E1 ne sont pas voisins
