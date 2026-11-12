"""Une session de simulation : un scénario chargé, et tout ce qu'il fait tourner
(simulation, demande, incendie éventuel, évacuation, indicateurs).

Format d'un scénario (`donnees/scenarios/*.json`) :

    {
      "nom": "Journée normale", "description": "...", "graine": 2026,
      "arrivees_par_minute": {"P1": 12.0, ...}, "part_pmr": 0.1,
      "visite_min_s": 60.0, "visite_max_s": 300.0, "beta": 2.0,
      "incendie": null
    }

`incendie`, s'il n'est pas null : {"debut_s": 300, "foyers": {"A:C1": 1.0},
"alpha": 0.05, "theta1": 20, "theta2": 50, "delai": 15, "connaissance": "local"}.
Le feu peut aussi être déclenché à la main (`allumer`), avec les réglages courants.
"""

import json
from pathlib import Path
from typing import Any

from zc.chargement import charger_parametres, charger_zone
from zc.demande import Demande, ParametresDemande
from zc.evacuation import Evacuation
from zc.incendie import Incendie
from zc.indicateurs import Indicateurs
from zc.modele import CentreZone, ErreurFormat, macro_noeud
from zc.palette import niveau
from zc.simulation import PARTI, SAUVE, Simulation

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "donnees"
SCENARIOS = DONNEES / "scenarios"


def lister_scenarios() -> list[dict[str, str]]:
    """Identifiant (nom du fichier), nom et description de chaque scénario."""
    resultat = []
    for fichier in sorted(SCENARIOS.glob("*.json")):
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
        resultat.append({"id": fichier.stem, "nom": donnees["nom"],
                         "description": donnees["description"]})
    return resultat


class Session:
    """Un scénario en cours."""

    def __init__(self, scenario_id: str) -> None:
        fichier = SCENARIOS / f"{scenario_id}.json"
        if not fichier.is_file():
            raise KeyError(scenario_id)
        self.scenario_id = scenario_id
        self.scenario: dict[str, Any] = json.loads(fichier.read_text(encoding="utf-8"))
        self.zone = charger_zone(DONNEES / "zone.json")
        self.sim = Simulation(self.zone, charger_parametres(DONNEES / "parametres.json"),
                              graine=self.scenario["graine"])
        self.demande = Demande(self.sim, ParametresDemande(
            arrivees_par_minute=dict(self.scenario["arrivees_par_minute"]),
            part_pmr=self.scenario["part_pmr"],
            visite_min=self.scenario["visite_min_s"],
            visite_max=self.scenario["visite_max_s"],
            beta=self.scenario["beta"]))
        self.indicateurs = Indicateurs(self.sim)
        self.evacuation: Evacuation | None = None
        # Réglages d'un incendie déclenché à la main (ceux du scénario s'il en a un).
        self.reglages_feu: dict[str, Any] = {
            "alpha": 0.05, "theta1": 20.0, "theta2": 50.0, "delai": 15,
            "connaissance": "local", "source": 1.0}
        incendie = self.scenario["incendie"]
        if incendie is not None:
            for cle in ["alpha", "theta1", "theta2", "delai", "connaissance"]:
                self.reglages_feu[cle] = incendie[cle]
            # Contrôlé dès le chargement : sinon l'erreur n'apparaîtrait qu'au moment
            # d'allumer le feu, en pleine simulation.
            centres = set()
            for foyer in incendie["foyers"]:
                if foyer not in self.sim.noeuds:
                    raise ErreurFormat(f"scénario {scenario_id} : foyer « {foyer} » inconnu")
                centres.add(macro_noeud(foyer))
            if len(centres) > 1:
                raise ErreurFormat(f"scénario {scenario_id} : les foyers doivent être "
                                   f"dans un seul centre")

    # --- déroulement -------------------------------------------------------------------

    def pas(self) -> None:
        """Un pas de temps : feu prévu par le scénario, visiteurs, puis déplacements (et
        incendie, alarme et évacuation s'il y a un feu)."""
        incendie = self.scenario["incendie"]
        if incendie is not None and self.evacuation is None:
            if self.sim.temps >= incendie["debut_s"]:
                for foyer in incendie["foyers"]:
                    self.allumer(foyer, incendie["foyers"][foyer])
        self.demande.preparer_pas()
        if self.evacuation is None:
            self.sim.pas()
        else:
            self.evacuation.pas()
            if self.evacuation.alarme is not None:
                # Le centre en feu ne reçoit plus de nouveaux visiteurs.
                self.demande.magasins.pop(self.evacuation.centre.id, None)
        self.indicateurs.relever()

    def allumer(self, noeud: str, source: float | None = None) -> None:
        """Allume un foyer sur un nœud. Le feu est limité à un centre : un second foyer
        doit être dans le même centre que le premier."""
        if noeud not in self.sim.noeuds:
            raise KeyError(noeud)
        if source is None:
            source = self.reglages_feu["source"]
        centre_id = macro_noeud(noeud)
        if self.evacuation is not None:
            if self.evacuation.centre.id != centre_id:
                raise ValueError(f"un incendie est déjà en cours dans le centre "
                                 f"« {self.evacuation.centre.id} »")
            self.evacuation.incendie.foyers[noeud] = source
            return
        centre = self.centre(centre_id)
        incendie = Incendie(centre.centre, alpha=self.reglages_feu["alpha"],
                            foyers={noeud: source}, theta1=self.reglages_feu["theta1"],
                            theta2=self.reglages_feu["theta2"],
                            delai=self.reglages_feu["delai"])
        self.evacuation = Evacuation(self.sim, centre, incendie,
                                     connaissance=self.reglages_feu["connaissance"])

    def centre(self, centre_id: str) -> CentreZone:
        for c in self.zone.centres:
            if c.id == centre_id:
                return c
        raise KeyError(centre_id)

    # --- état, pour la page --------------------------------------------------------------

    def position(self, identifiant: str) -> tuple[float, float]:
        """Position sur la carte : position du centre dans la zone + position du nœud dans
        le centre ; pour une source, sa position dans la zone."""
        for s in self.zone.sources:
            if s.id == identifiant:
                return s.x or 0, s.y or 0
        centre = self.centre(macro_noeud(identifiant))
        noeud = centre.centre.noeud(identifiant)
        return (centre.x or 0) + (noeud.x or 0), (centre.y or 0) + (noeud.y or 0)

    def etat(self) -> dict[str, Any]:
        """Tout ce que la page doit afficher, en JSON."""
        noeuds = []
        for c in self.zone.centres:
            for n in c.centre.noeuds:
                x, y = self.position(n.id)
                noeuds.append({
                    "id": n.id, "centre": c.id, "nom": n.nom, "type": n.type,
                    "x": x, "y": y, "capacite_max": n.capacite_max,
                    "occupation": n.occupation,
                    "niveau": niveau(n.taux_occupation()),
                    "fumee": round(n.niveau_fumee, 1), "statut": n.statut})
        sources = []
        for s in self.zone.sources:
            sources.append({"id": s.id, "type": s.type, "x": s.x or 0, "y": s.y or 0})
        aretes = []
        for i in range(len(self.sim.aretes)):
            a = self.sim.aretes[i]
            aretes.append({"id": i, "source": a.source, "cible": a.cible,
                           "sens": a.sens, "pmr": a.pmr, "statut": a.statut,
                           "taux": round(a.taux, 3), "niveau": niveau(a.taux),
                           "attente": self.sim.attente[i]})
        agents = []
        for agent in self.sim.agents:
            if agent.etat == PARTI or agent.etat == SAUVE:
                continue
            avancee = 0.0
            vers = None
            if agent.arete is not None:
                avancee = agent.avancee / self.sim.aretes[agent.arete].longueur
                vers = agent.itineraire[0]
            agents.append({"id": agent.id, "pmr": agent.pmr, "etat": agent.etat,
                           "depuis": agent.position, "vers": vers,
                           "avancee": round(avancee, 3)})
        alarme = None
        if self.evacuation is not None:
            e = self.evacuation
            alarme = {"centre": e.centre.id, "debut": e.alarme,
                      "sauves": e.sauves(), "pieges": len(e.pieges),
                      "presents": len(e.presents_au_declenchement),
                      "charge": e.charge, "courbe": e.courbe}
        reglages: dict[str, Any] = {"beta": self.demande.parametres.beta,
                                    "part_pmr": self.demande.parametres.part_pmr}
        for cle in self.reglages_feu:
            reglages[cle] = self.reglages_feu[cle]
        return {"scenario": self.scenario_id, "temps": self.sim.temps,
                "noeuds": noeuds, "sources": sources, "aretes": aretes,
                "agents": agents, "alarme": alarme, "reglages": reglages}
