"""Story 4.3 : routage des agents (moins encombré par défaut, contrainte PMR, recalcul
quand le trajet n'est plus praticable).

Le plan du centre A est provisoire : ces tests utilisent les connexions de la zone et
retrouvent les nœuds de A par leur type.
"""

from pathlib import Path

from zc.chargement import charger_centre, charger_parametres, charger_zone
from zc.chemins import itineraire
from zc.demande import Demande, ParametresDemande, Visite, trajet_praticable
from zc.modele import Arete, CentreZone, Zone
from zc.navigation import graphe_de_la_zone
from zc.simulation import DANS_NOEUD, SUR_ARETE, Agent, Simulation

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = charger_parametres(RACINE / "donnees" / "parametres.json")


def preparer(pmr: bool = False) -> tuple[Simulation, Demande, Agent]:
    """Une zone sans arrivées automatiques, et un visiteur posé à P1 qui doit aller au
    premier magasin du centre A."""
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=1)
    demande = Demande(sim, ParametresDemande(arrivees_par_minute={}, part_pmr=0.0,
                                             visite_min=30.0, visite_max=60.0))
    magasin = None
    for n in zone.centres[0].centre.noeuds:
        if n.type == "magasin" and magasin is None:
            magasin = n.id
    assert magasin is not None
    critere = "pmr" if pmr else "court"
    trajet = itineraire(zone, "P1", "A", critere, magasin=magasin.split(":")[1])
    assert trajet is not None
    agent = sim.ajouter_agent("P1", trajet[1][1:], pmr=pmr)
    demande.visites[agent.id] = Visite(source="P1", programme=[magasin])
    return sim, demande, agent


def connexion(sim: Simulation, u: str, v: str) -> int:
    for i in range(len(sim.aretes)):
        a = sim.aretes[i]
        if (a.source, a.cible) in [(u, v), (v, u)]:
            return i
    raise KeyError((u, v))


def test_l_agent_se_reoriente_si_son_arete_suivante_est_bloquee() -> None:
    sim, demande, agent = preparer()
    premier = agent.itineraire[0]
    destination = agent.itineraire[-1]
    sim.aretes[connexion(sim, "P1", premier)].statut = "bloqué"

    demande.pas()

    assert agent.itineraire[0] != premier
    assert agent.itineraire[-1] == destination  # même destination
    assert agent.etat == SUR_ARETE  # il est reparti par un autre chemin
    assert sim.aretes[agent.arete].statut != "bloqué"


def test_sans_chemin_l_agent_attend_puis_repart() -> None:
    sim, demande, agent = preparer()
    # P1 n'a que deux connexions : on les bloque toutes les deux.
    bloquees = []
    for i in range(len(sim.aretes)):
        if "P1" in (sim.aretes[i].source, sim.aretes[i].cible):
            sim.aretes[i].statut = "bloqué"
            bloquees.append(i)
    for _ in range(5):
        demande.pas()
        assert agent.etat == DANS_NOEUD and agent.position == "P1"

    for i in bloquees:
        sim.aretes[i].statut = "libre"
    demande.pas()
    assert agent.etat == SUR_ARETE


def test_un_agent_pmr_reoriente_reste_sur_des_aretes_pmr() -> None:
    sim, demande, agent = preparer(pmr=True)
    sim.aretes[connexion(sim, "P1", agent.itineraire[0])].statut = "bloqué"
    # Le détour PMR fait environ 1 100 m : à 0,69 m/s, il faut environ 1 500 pas.
    # Ensuite il visite le magasin et repart : on vérifie qu'il est passé par A.
    passe_par_a = False
    for _ in range(2500):
        demande.pas()
        if agent.position.startswith("A:"):
            passe_par_a = True
        if agent.etat == SUR_ARETE and agent.arete is not None:
            assert sim.aretes[agent.arete].pmr
    assert passe_par_a


def test_couloirs_paralleles_le_pmr_prend_le_couloir_pmr() -> None:
    # Deux couloirs S1 – C1 : celui de la consigne (8 m, PMR) et un raccourci de 3 m
    # avec des marches. Le valide prend le raccourci, le PMR le couloir PMR.
    centre = charger_centre(RACINE / "tests" / "donnees" / "exemple_consigne.json")
    centre.aretes.append(Arete(source="S1", cible="C1", capacite_max=5.0, longueur=3.0,
                               statut="libre", sens="bidirectionnel", pmr=False))
    zone = Zone(centres=[CentreZone(id="X", centre=centre)], sources=[], connexions=[])
    sim = Simulation(zone, PARAMETRES, graine=1)
    valide = sim.ajouter_agent("S1", ["C1"])
    pmr = sim.ajouter_agent("S1", ["C1"], pmr=True)
    sim.pas()
    assert valide.arete is not None and pmr.arete is not None
    assert sim.aretes[valide.arete].longueur == 3.0
    assert sim.aretes[pmr.arete].pmr and sim.aretes[pmr.arete].longueur == 8.0


def test_trajet_intact_non_recalcule() -> None:
    sim, demande, agent = preparer()
    avant = list(agent.itineraire)
    demande.pas()
    assert agent.itineraire == avant


def test_trajet_praticable() -> None:
    sim, _, agent = preparer()
    graphe = graphe_de_la_zone(sim.zone, "court")
    assert trajet_praticable(graphe, "P1", agent.itineraire)
    assert not trajet_praticable(graphe, "P1", ["T1"])  # pas d'arc P1 → T1
    sim.aretes[connexion(sim, "P1", agent.itineraire[0])].statut = "bloqué"
    graphe = graphe_de_la_zone(sim.zone, "court")
    assert not trajet_praticable(graphe, "P1", agent.itineraire)
