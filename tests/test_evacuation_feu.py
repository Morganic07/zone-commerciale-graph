"""Story 5.4 : évacuation d'un centre en feu (alarme, sortie la plus proche recalculée,
sauvés, piégés, charge des sorties, courbe).

Le plan du centre A est provisoire : on ne cite aucun de ses nœuds. On prend sa première
sortie, et on allume le feu chez un de ses voisins, pour qu'elle finisse bloquée.
"""

from pathlib import Path

import pytest

from zc.chargement import charger_parametres, charger_zone
from zc.evacuation import Evacuation
from zc.incendie import Incendie
from zc.simulation import SAUVE, Simulation

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = charger_parametres(RACINE / "donnees" / "parametres.json")


def scenario(personnes_par_noeud: int = 4) -> tuple[Simulation, Evacuation, str]:
    """Incendie qui bloque une sortie : renvoie la simulation, l'évacuation et la sortie
    menacée."""
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=12)
    centre = zone.centres[0]
    sorties = []
    for n in centre.centre.noeuds:
        if n.type == "sortie":
            sorties.append(n.id)
    menacee = sorties[0]
    foyer = None
    for a in centre.centre.aretes:
        if a.source == menacee and a.cible not in sorties:
            foyer = a.cible
        if a.cible == menacee and a.source not in sorties:
            foyer = a.source
    assert foyer is not None

    # Des visiteurs répartis dans le centre, ailleurs que dans les sorties et le foyer.
    for n in centre.centre.noeuds:
        if n.type != "sortie" and n.id != foyer:
            for _ in range(min(personnes_par_noeud, n.capacite_max)):
                sim.ajouter_agent(n.id, [])

    # La fumée avance d'un nœud par pas, quelle que soit la longueur des couloirs : avec
    # Δt = 1 s, α et le terme source doivent rester faibles, sinon elle traverse le centre
    # en quelques secondes et personne ne peut sortir. Avec ces valeurs, la sortie menacée
    # reçoit encore du monde avant d'être bloquée.
    incendie = Incendie(centre.centre, alpha=0.05, foyers={foyer: 1.0}, theta1=20,
                        theta2=50, delai=3)
    return sim, Evacuation(sim, centre, incendie), menacee


@pytest.fixture(scope="module")
def evacuation_complete() -> tuple[Simulation, Evacuation, str, list[tuple[int, int, str]]]:
    """Déroule l'évacuation jusqu'au bout ; note à chaque pas la charge et le statut de
    la sortie menacée."""
    sim, evac, menacee = scenario()
    suivi = []
    for _ in range(5000):
        evac.pas()
        suivi.append((len(suivi), evac.charge[menacee], sim.noeuds[menacee].statut))
        if evac.termine():
            break
    return sim, evac, menacee, suivi


def test_la_sortie_bloquee_ne_recoit_plus_personne(evacuation_complete) -> None:
    _, _, _, suivi = evacuation_complete
    blocage = None
    for pas, charge, statut in suivi:
        if statut == "bloqué" and blocage is None:
            blocage = (pas, charge)
    assert blocage is not None, "la sortie menacée devait finir bloquée"
    assert blocage[1] > 0, "elle doit avoir reçu du monde avant son blocage"
    for pas, charge, _ in suivi:
        if pas >= blocage[0]:
            assert charge == blocage[1]


def test_sauves_plus_pieges_egale_presents_au_declenchement(evacuation_complete) -> None:
    _, evac, _, _ = evacuation_complete
    assert evac.termine()
    assert len(evac.presents_au_declenchement) > 30
    assert evac.sauves() + len(evac.pieges) == len(evac.presents_au_declenchement)
    assert evac.sauves() > 0


def test_charge_des_sorties_egale_aux_sauves(evacuation_complete) -> None:
    _, evac, _, _ = evacuation_complete
    total = 0
    for sortie in evac.charge:
        total += evac.charge[sortie]
    assert total == evac.sauves()


def test_courbe_jamais_croissante_et_temps_d_evacuation(evacuation_complete) -> None:
    _, evac, _, _ = evacuation_complete
    nombres = []
    for _, restants in evac.courbe:
        nombres.append(restants)
    for i in range(len(nombres) - 1):
        assert nombres[i + 1] <= nombres[i]
    assert nombres[-1] == len(evac.pieges)
    duree = evac.temps_d_evacuation()
    assert duree is not None and duree > 0


def test_arriver_dans_une_sortie_bloquee_ne_sauve_pas() -> None:
    # Un agent peut entrer dans une sortie déjà bloquée (il était engagé au-delà de la
    # moitié du couloir) : il n'est pas sauvé, et la sortie ne le compte pas.
    sim, evac, menacee = scenario(personnes_par_noeud=0)
    sortie = sim.noeuds[menacee]
    agent = sim.ajouter_agent(menacee, [])
    evac.presents_au_declenchement.append(agent.id)  # seuls les présents sont sauvés
    sortie.statut = "bloqué"
    evac.sauver_aux_sorties()
    assert agent.etat != SAUVE and evac.charge[menacee] == 0
    sortie.statut = "sortie"
    evac.sauver_aux_sorties()
    assert agent.etat == SAUVE and evac.charge[menacee] == 1
    assert sortie.occupation == 0  # sa place est libérée


def test_en_chemin_vers_une_sortie_il_s_y_arrete_et_est_sauve() -> None:
    # À l'alarme, un visiteur marche vers une sortie et son trajet continue au-delà, hors
    # du centre. Il doit s'arrêter à la sortie et compter parmi les sauvés : sinon il
    # quitterait le centre sans être compté, et l'évacuation ne finirait jamais.
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=12)
    centre = zone.centres[0]
    dans_le_centre = set()
    sorties = []
    for n in centre.centre.noeuds:
        dans_le_centre.add(n.id)
        if n.type == "sortie":
            sorties.append(n.id)
    # Une sortie, le nœud du centre qui y mène, et le nœud hors du centre qui la suit.
    sortie = None
    avant = None
    apres = None
    for a in sim.aretes:
        for x, y in [(a.source, a.cible), (a.cible, a.source)]:
            if x in sorties and y not in dans_le_centre:
                sortie = x
                apres = y
    for a in centre.centre.aretes:
        if a.sens == "bidirectionnel" and sortie in (a.source, a.cible):
            autre = a.cible if a.source == sortie else a.source
            if autre not in sorties:
                avant = autre
    assert sortie is not None and avant is not None and apres is not None

    agent = sim.ajouter_agent(avant, [sortie, apres])
    sim.pas()  # il s'engage sur le couloir qui mène à la sortie
    assert agent.etat == "sur_arete"

    # Un feu loin de cette sortie, détecté tout de suite (mode global, θ₁ très bas).
    foyer = None
    for n in centre.centre.noeuds:
        if n.id not in (sortie, avant) and n.type != "sortie":
            foyer = n.id
    incendie = Incendie(centre.centre, alpha=0.05, foyers={foyer: 1.0}, theta1=0.5,
                        theta2=50, delai=3)
    evac = Evacuation(sim, centre, incendie, connaissance="global")
    for _ in range(100):
        evac.pas()
        if evac.termine():
            break
    assert evac.alarme is not None
    assert agent.id in evac.presents_au_declenchement
    assert agent.etat == SAUVE and agent.position == sortie
    assert evac.charge[sortie] == 1
    assert evac.termine()


def test_avant_l_alarme_personne_n_evacue() -> None:
    sim, evac, _ = scenario()
    evac.pas()
    assert evac.alarme is None  # la fumée n'a encore franchi θ₁ nulle part
    for agent in sim.agents:
        assert agent.itineraire == []
        assert agent.etat != SAUVE


def test_l_alarme_retient_les_presents() -> None:
    sim, evac, _ = scenario()
    while evac.alarme is None:
        evac.pas()
    assert sorted(evac.presents_au_declenchement) == list(range(len(sim.agents)))
