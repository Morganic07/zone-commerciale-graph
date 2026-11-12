"""Story 5.5 : connaissance globale ou locale de l'incendie par les occupants, comparées
sur un même incendie, et export des résultats.

Le plan du centre A est provisoire : on ne cite aucun de ses nœuds. Le feu est allumé
dans un nœud sans capteur voisin d'une sortie, donc sur un chemin d'évacuation.
"""

import csv
from pathlib import Path

import pytest

from zc.chargement import charger_parametres, charger_zone
from zc.evacuation import Evacuation
from zc.incendie import Incendie
from zc.indicateurs import exporter_evacuations
from zc.simulation import Simulation

RACINE = Path(__file__).resolve().parent.parent
PARAMETRES = charger_parametres(RACINE / "donnees" / "parametres.json")


def evacuer(connaissance: str) -> Evacuation:
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=12)
    centre = zone.centres[0]
    sorties = []
    for n in centre.centre.noeuds:
        if n.type == "sortie":
            sorties.append(n.id)
    foyer = None
    for a in centre.centre.aretes:
        for u, v in [(a.source, a.cible), (a.cible, a.source)]:
            sans_capteur = not centre.centre.noeud(u).capteur_fumee
            if v in sorties and u not in sorties and sans_capteur and foyer is None:
                foyer = u
    assert foyer is not None, "le plan doit avoir un nœud sans capteur voisin d'une sortie"

    for n in centre.centre.noeuds:
        if n.type != "sortie" and n.id != foyer:
            for _ in range(min(4, n.capacite_max)):
                sim.ajouter_agent(n.id, [])
    incendie = Incendie(centre.centre, alpha=0.05, foyers={foyer: 1.0}, theta1=20,
                        theta2=50, delai=15)
    evac = Evacuation(sim, centre, incendie, connaissance=connaissance)
    for _ in range(5000):
        evac.pas()
        if evac.termine():
            break
    return evac


@pytest.fixture(scope="module")
def les_deux() -> dict[str, Evacuation]:
    return {"local": evacuer("local"), "global": evacuer("global")}


def test_les_deux_modes_vont_au_bout(les_deux: dict[str, Evacuation]) -> None:
    for mode in les_deux:
        e = les_deux[mode]
        assert e.termine(), mode
        assert e.sauves() + len(e.pieges) == len(e.presents_au_declenchement), mode


def test_les_resultats_different(les_deux: dict[str, Evacuation]) -> None:
    local, global_ = les_deux["local"], les_deux["global"]
    # Sans capteur au foyer, l'alarme attend δ pas : en mode global, les occupants
    # partent plus tôt et sont plus nombreux à sortir.
    assert local.alarme is not None and global_.alarme is not None
    assert global_.alarme < local.alarme
    assert global_.sauves() > local.sauves()


def test_export_de_la_comparaison(les_deux: dict[str, Evacuation], tmp_path: Path) -> None:
    exporter_evacuations(les_deux, tmp_path)
    with open(tmp_path / "evacuations.csv", encoding="utf-8") as f:
        lignes = {}
        for ligne in csv.DictReader(f):
            lignes[ligne["evacuation"]] = ligne
    for mode in ["local", "global"]:
        e = les_deux[mode]
        assert lignes[mode]["sauves"] == str(e.sauves())
        assert lignes[mode]["pieges"] == str(len(e.pieges))
        assert lignes[mode]["presents"] == str(len(e.presents_au_declenchement))

    with open(tmp_path / "courbes_evacuation.csv", encoding="utf-8") as f:
        courbes = list(csv.DictReader(f))
    assert list(courbes[0]) == ["pas_depuis_l_alarme", "global", "local"]
    longueur = max(len(les_deux["local"].courbe), len(les_deux["global"].courbe))
    assert len(courbes) == longueur
    assert courbes[-1]["local"] == str(len(les_deux["local"].pieges))


def test_export_avec_une_evacuation_sans_alarme(les_deux: dict[str, Evacuation],
                                               tmp_path: Path) -> None:
    # Une évacuation où le feu n'est jamais détecté n'a ni courbe ni temps d'évacuation :
    # l'export ne doit pas planter pour autant.
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=1)
    centre = zone.centres[0]
    sans_feu = Evacuation(sim, centre, Incendie(centre.centre, alpha=0.05, foyers={}))
    for _ in range(10):
        sans_feu.pas()
    exporter_evacuations({"local": les_deux["local"], "sans_feu": sans_feu}, tmp_path)
    with open(tmp_path / "evacuations.csv", encoding="utf-8") as f:
        lignes = {}
        for ligne in csv.DictReader(f):
            lignes[ligne["evacuation"]] = ligne
    assert lignes["sans_feu"]["temps_d_evacuation_s"] == "non terminée"
    with open(tmp_path / "courbes_evacuation.csv", encoding="utf-8") as f:
        courbes = list(csv.DictReader(f))
    assert courbes[0]["sans_feu"] == ""


def test_mode_inconnu_refuse() -> None:
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    sim = Simulation(zone, PARAMETRES, graine=1)
    centre = zone.centres[0]
    incendie = Incendie(centre.centre, alpha=0.05, foyers={centre.centre.noeuds[0].id: 1.0})
    with pytest.raises(ValueError, match="connaissance"):
        Evacuation(sim, centre, incendie, connaissance="partielle")
