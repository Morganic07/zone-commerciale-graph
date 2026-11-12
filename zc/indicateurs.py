"""Indicateurs de fréquentation et export CSV (PLAN.md § 5.4, partie hors incendie).

On relève l'état de la simulation après chaque pas avec `relever()`, puis on lit :
- l'occupation moyenne et maximale de chaque nœud (et les taux correspondants) ;
- la file d'attente moyenne et maximale au bout de chaque arête : les arêtes où elle
  est la plus longue sont les goulots ;
- le temps de trajet moyen : temps qu'un visiteur passe à se déplacer (sur une arête ou
  en attente au bout) pendant une visite complète, en moyenne sur les visiteurs repartis.

C'est, avec `chargement.py`, le seul module du moteur qui écrit sur le disque.
"""

import csv
from pathlib import Path

from zc.evacuation import Evacuation
from zc.simulation import EN_ATTENTE, PARTI, SUR_ARETE, Simulation


def exporter_evacuations(evacuations: dict[str, Evacuation], dossier: Path) -> None:
    """Compare plusieurs évacuations (par exemple les modes « local » et « global ») :
    écrit evacuations.csv (un bilan par évacuation) et courbes_evacuation.csv (personnes
    encore dans le centre, pas à pas, une colonne par évacuation)."""
    dossier.mkdir(parents=True, exist_ok=True)
    noms = sorted(evacuations)

    with open(dossier / "evacuations.csv", "w", newline="", encoding="utf-8") as f:
        ecriture = csv.writer(f)
        ecriture.writerow(["evacuation", "presents", "sauves", "pieges",
                           "temps_d_evacuation_s", "charge_des_sorties"])
        for nom in noms:
            e = evacuations[nom]
            charges = []
            for sortie in sorted(e.charge):
                charges.append(f"{sortie}={e.charge[sortie]}")
            temps: object = e.temps_d_evacuation()
            if temps is None:
                temps = "non terminée"  # pas d'alarme, ou évacuation pas encore finie
            ecriture.writerow([nom, len(e.presents_au_declenchement), e.sauves(),
                               len(e.pieges), temps, " ".join(charges)])

    with open(dossier / "courbes_evacuation.csv", "w", newline="", encoding="utf-8") as f:
        ecriture = csv.writer(f)
        ecriture.writerow(["pas_depuis_l_alarme"] + noms)
        longueur = 0
        for nom in noms:
            longueur = max(longueur, len(evacuations[nom].courbe))
        for i in range(longueur):
            ligne: list[object] = [i + 1]
            for nom in noms:
                courbe = evacuations[nom].courbe
                if i < len(courbe):
                    ligne.append(courbe[i][1])
                elif len(courbe) > 0:
                    ligne.append(courbe[-1][1])  # évacuation finie : la valeur reste
                else:
                    ligne.append("")  # pas d'alarme : pas de courbe
            ecriture.writerow(ligne)


class Indicateurs:
    """Mesures accumulées au fil d'une simulation."""

    def __init__(self, sim: Simulation) -> None:
        self.sim = sim
        self.releves = 0
        self.occupation_totale: dict[str, int] = {}
        self.occupation_max: dict[str, int] = {}
        for identifiant in sim.noeuds:
            self.occupation_totale[identifiant] = 0
            self.occupation_max[identifiant] = 0
        self.attente_totale = [0] * len(sim.aretes)
        self.attente_max = [0] * len(sim.aretes)
        self.temps_de_deplacement: dict[int, float] = {}

    def relever(self) -> None:
        """À appeler après chaque pas de la simulation."""
        self.releves += 1
        for identifiant in self.sim.noeuds:
            occupation = self.sim.noeuds[identifiant].occupation
            self.occupation_totale[identifiant] += occupation
            self.occupation_max[identifiant] = max(self.occupation_max[identifiant],
                                                   occupation)
        for i in range(len(self.sim.aretes)):
            attente = self.sim.attente[i]
            self.attente_totale[i] += attente
            self.attente_max[i] = max(self.attente_max[i], attente)
        for agent in self.sim.agents:
            if agent.id not in self.temps_de_deplacement:
                self.temps_de_deplacement[agent.id] = 0.0
            if agent.etat == SUR_ARETE or agent.etat == EN_ATTENTE:
                self.temps_de_deplacement[agent.id] += self.sim.dt

    # --- lecture ------------------------------------------------------------------------

    def occupation_moyenne(self, noeud: str) -> float:
        if self.releves == 0:
            return 0.0
        return self.occupation_totale[noeud] / self.releves

    def attente_moyenne(self, arete: int) -> float:
        if self.releves == 0:
            return 0.0
        return self.attente_totale[arete] / self.releves

    def visites_terminees(self) -> list[int]:
        """Identifiants des visiteurs repartis (visite complète)."""
        termines = []
        for agent in self.sim.agents:
            if agent.etat == PARTI and agent.id in self.temps_de_deplacement:
                termines.append(agent.id)
        return termines

    def temps_de_trajet_moyen(self) -> float:
        """Temps moyen passé à se déplacer pendant une visite complète, sur les visiteurs
        repartis. Les visiteurs encore en route sont exclus : leur trajet n'est pas fini,
        et les compter ferait baisser la moyenne (de 20 % sur une journée type)."""
        termines = self.visites_terminees()
        if len(termines) == 0:
            return 0.0
        total = 0.0
        for agent_id in termines:
            total += self.temps_de_deplacement[agent_id]
        return total / len(termines)

    def goulots(self) -> list[int]:
        """Numéros des arêtes où des gens ont attendu, de la file moyenne la plus longue
        à la plus courte."""
        # Couples (−file moyenne, numéro) : le tri croissant met la file la plus longue
        # en premier, et départage les égalités par le numéro de l'arête.
        couples = []
        for i in range(len(self.sim.aretes)):
            if self.attente_max[i] > 0:
                couples.append((-self.attente_moyenne(i), i))
        couples.sort()
        resultat = []
        for _, i in couples:
            resultat.append(i)
        return resultat

    # --- export -------------------------------------------------------------------------

    def exporter_csv(self, dossier: Path) -> None:
        """Écrit noeuds.csv, aretes.csv et resume.csv dans `dossier`."""
        dossier.mkdir(parents=True, exist_ok=True)

        with open(dossier / "noeuds.csv", "w", newline="", encoding="utf-8") as f:
            ecriture = csv.writer(f)
            ecriture.writerow(["id", "type", "capacite_max", "occupation_moyenne",
                               "occupation_max", "taux_moyen", "taux_max"])
            for identifiant in self.sim.noeuds:
                n = self.sim.noeuds[identifiant]
                moyenne = self.occupation_moyenne(identifiant)
                maximum = self.occupation_max[identifiant]
                ecriture.writerow([identifiant, n.type, n.capacite_max, round(moyenne, 4),
                                   maximum, round(moyenne / n.capacite_max, 4),
                                   round(maximum / n.capacite_max, 4)])

        with open(dossier / "aretes.csv", "w", newline="", encoding="utf-8") as f:
            ecriture = csv.writer(f)
            ecriture.writerow(["source", "cible", "capacite_max", "attente_moyenne",
                               "attente_max"])
            for i in range(len(self.sim.aretes)):
                a = self.sim.aretes[i]
                ecriture.writerow([a.source, a.cible, a.capacite_max,
                                   round(self.attente_moyenne(i), 4), self.attente_max[i]])

        with open(dossier / "resume.csv", "w", newline="", encoding="utf-8") as f:
            ecriture = csv.writer(f)
            ecriture.writerow(["indicateur", "valeur"])
            ecriture.writerow(["duree_simulee_s", self.sim.temps])
            ecriture.writerow(["visiteurs", len(self.temps_de_deplacement)])
            ecriture.writerow(["visites_terminees", len(self.visites_terminees())])
            ecriture.writerow(["temps_de_trajet_moyen_s",
                               round(self.temps_de_trajet_moyen(), 4)])
            premiers = []
            for i in self.goulots()[:3]:
                premiers.append(f"{self.sim.aretes[i].source}-{self.sim.aretes[i].cible}")
            ecriture.writerow(["goulots", " ".join(premiers)])
