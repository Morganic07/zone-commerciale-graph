"""Story 4.5 : indicateurs de fréquentation et export CSV, vérifiés sur un scénario
calculé à la main."""

import csv
from pathlib import Path

import pytest

from zc.chargement import charger_centre, charger_parametres, charger_zone
from zc.demande import Demande, ParametresDemande
from zc.indicateurs import Indicateurs
from zc.modele import Arete, CentreZone, Source, Zone
from zc.simulation import Simulation

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = charger_parametres(RACINE / "donnees" / "parametres.json")


def scenario_a_la_main() -> tuple[Simulation, Indicateurs]:
    """Centre de la consigne (S1 – C1 – E1), C1 réduit à 1 place, 3 agents de S1 vers C1.

    Calcul à la main, sur 10 pas (un relevé après chaque pas) :
    - pas 1 : les 3 entrent sur S1 – C1 (8 m, capacité 10 pers/s, donc tous passent) ;
    - pas 2 à 7 : ils marchent à 1,34 m/s ; au pas 7 ils ont fait 6 × 1,34 = 8,04 m ;
      un seul entre dans C1 (1 place), les 2 autres attendent au bout de l'arête ;
    - pas 8 à 10 : rien ne bouge.
    """
    centre = charger_centre(RACINE / "tests" / "donnees" / "exemple_consigne.json")
    centre.noeud("C1").capacite_max = 1
    zone = Zone(centres=[CentreZone(id="X", centre=centre)], sources=[], connexions=[])
    sim = Simulation(zone, PARAMETRES, graine=1)
    for _ in range(3):
        sim.ajouter_agent("S1", ["C1"])
    indicateurs = Indicateurs(sim)
    for _ in range(10):
        sim.pas()
        indicateurs.relever()
    return sim, indicateurs


def test_occupation_moyenne_et_maximale() -> None:
    _, ind = scenario_a_la_main()
    # C1 : 0 aux pas 1 à 6, 1 aux pas 7 à 10 → moyenne 4 / 10 = 0,4, maximum 1.
    assert ind.occupation_moyenne("C1") == pytest.approx(0.4)
    assert ind.occupation_max["C1"] == 1
    # S1 : vidé dès le pas 1 (les relevés sont faits après chaque pas).
    assert ind.occupation_moyenne("S1") == 0.0
    assert ind.occupation_max["S1"] == 0


def test_file_d_attente_et_goulots() -> None:
    sim, ind = scenario_a_la_main()
    # 2 personnes attendent aux pas 7 à 10 → moyenne 8 / 10 = 0,8, maximum 2.
    assert ind.attente_moyenne(0) == pytest.approx(0.8)
    assert ind.attente_max[0] == 2
    assert ind.goulots() == [0]
    assert (sim.aretes[0].source, sim.aretes[0].cible) == ("S1", "C1")


def test_temps_de_deplacement_par_visiteur() -> None:
    _, ind = scenario_a_la_main()
    # Celui qui entre : 6 pas en mouvement (pas 1 à 6). Les deux autres : 6 pas de
    # marche puis 4 d'attente (pas 7 à 10).
    assert sorted(ind.temps_de_deplacement.values()) == [6.0, 10.0, 10.0]
    # Personne n'est reparti : aucune visite terminée, pas de temps de trajet moyen.
    assert ind.visites_terminees() == []
    assert ind.temps_de_trajet_moyen() == 0.0


def aller_retour() -> tuple[Simulation, Indicateurs]:
    """Un parking P relié à la sortie E1 par une connexion de 2,68 m. Un visiteur va de P
    à E1 et revient : à 1,34 m/s, 2 pas à l'aller, 2 au retour.

    pas 1 : il s'engage ; pas 2 : 1,34 m ; pas 3 : 2,68 m, il entre dans E1 et repart
    aussitôt ; pas 4 : 1,34 m ; pas 5 : il arrive à P. En mouvement aux pas 1 à 4 : 4 s.
    """
    centre = charger_centre(RACINE / "tests" / "donnees" / "exemple_consigne.json")
    retour = Arete(source="P", cible="E1", capacite_max=5.0, longueur=2.68,
                   statut="libre", sens="bidirectionnel", pmr=True)
    zone = Zone(centres=[CentreZone(id="X", centre=centre)],
                sources=[Source(id="P", type="parking")], connexions=[retour])
    sim = Simulation(zone, PARAMETRES, graine=1)
    agent = sim.ajouter_agent("P", ["E1", "P"])
    ind = Indicateurs(sim)
    for _ in range(5):
        sim.pas()
        ind.relever()
    sim.retirer(agent)
    return sim, ind


def test_temps_de_trajet_moyen_sur_les_visites_terminees(tmp_path: Path) -> None:
    _, ind = aller_retour()
    assert ind.visites_terminees() == [0]
    assert ind.temps_de_trajet_moyen() == 4.0
    ind.exporter_csv(tmp_path)
    with open(tmp_path / "resume.csv", encoding="utf-8") as f:
        resume = {}
        for ligne in csv.DictReader(f):
            resume[ligne["indicateur"]] = ligne["valeur"]
    assert resume["visites_terminees"] == "1"
    assert resume["temps_de_trajet_moyen_s"] == "4.0"


def test_export_csv_valeurs_exactes(tmp_path: Path) -> None:
    _, ind = scenario_a_la_main()
    ind.exporter_csv(tmp_path)

    with open(tmp_path / "noeuds.csv", encoding="utf-8") as f:
        noeuds = {}
        for ligne in csv.DictReader(f):
            noeuds[ligne["id"]] = ligne
    assert noeuds["C1"]["occupation_moyenne"] == "0.4"
    assert noeuds["C1"]["occupation_max"] == "1"
    assert noeuds["C1"]["taux_max"] == "1.0"

    with open(tmp_path / "aretes.csv", encoding="utf-8") as f:
        aretes = list(csv.DictReader(f))
    assert aretes[0]["source"] == "S1" and aretes[0]["cible"] == "C1"
    assert aretes[0]["attente_moyenne"] == "0.8" and aretes[0]["attente_max"] == "2"
    assert aretes[1]["attente_max"] == "0"

    with open(tmp_path / "resume.csv", encoding="utf-8") as f:
        resume = {}
        for ligne in csv.DictReader(f):
            resume[ligne["indicateur"]] = ligne["valeur"]
    assert resume["duree_simulee_s"] == "10.0"
    assert resume["visiteurs"] == "3"
    assert resume["visites_terminees"] == "0"
    assert resume["temps_de_trajet_moyen_s"] == "0.0"
    assert resume["goulots"] == "S1-C1"


def test_sur_une_journee_les_indicateurs_restent_coherents() -> None:
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=5)
    demande = Demande(sim, ParametresDemande(
        arrivees_par_minute={"P1": 30.0, "T1": 20.0}, part_pmr=0.2, visite_min=30.0,
        visite_max=120.0, beta=2.0))
    ind = Indicateurs(sim)
    for _ in range(600):
        demande.pas()
        ind.relever()
    for identifiant in sim.noeuds:
        n = sim.noeuds[identifiant]
        assert 0 <= ind.occupation_moyenne(identifiant) <= ind.occupation_max[identifiant]
        assert ind.occupation_max[identifiant] <= n.capacite_max
    assert len(ind.visites_terminees()) > 0
    assert ind.temps_de_trajet_moyen() > 0
