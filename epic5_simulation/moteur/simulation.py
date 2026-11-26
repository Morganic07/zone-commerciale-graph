"""
Simulation : les visiteurs (agents) se déplacent dans le réseau, pas de temps par pas
de temps.

Un agent est toujours dans l'un de ces trois états :
- « noeud » : il est dans un nœud ;
- « arete » : il marche sur une arête ;
- « attente » : il attend qu'il y ait de la place dans le nœud suivant.

Deux règles de la consigne sont respectées à chaque pas :
- un nœud ne contient jamais plus de personnes que sa capacité (o_v ≤ c_v) ;
- une arête ne laisse pas entrer plus de c_e · Δt personnes par pas (φ_e ≤ c_e · Δt).
"""

import random
from dataclasses import dataclass

# Durée d'un pas de temps, en secondes (Δt, PLAN.md § 4.1).
DUREE_DU_PAS = 1


@dataclass
class Agent:
    """Un visiteur.

    `chemin` est la liste des nœuds qu'il lui reste à atteindre. Le premier est le
    nœud suivant. Quand la liste est vide, il est arrivé.
    `noeud` est le nœud où il est, ou celui qu'il vient de quitter s'il est sur une
    arête. Il vaut "" tant que l'agent n'est entré dans aucun nœud.
    """

    pmr: bool  # vrai pour une personne en fauteuil roulant
    chemin: list
    noeud: str = ""
    etat: str = "attente"  # « noeud », « arete » ou « attente »
    position: float = 0  # mètres parcourus sur l'arête


class Simulation:
    """Le réseau, les agents et le générateur de hasard."""

    def __init__(self, reseau, vitesse_valide, vitesse_pmr, graine):
        # Tout le hasard vient de ce générateur : une même graine redonne
        # exactement la même simulation.
        self.hasard = random.Random(graine)
        self.vitesse_valide = vitesse_valide
        self.vitesse_pmr = vitesse_pmr
        self.agents = []
        self.temps = 0  # nombre de pas déjà joués

        # Les nœuds, rangés par identifiant.
        self.noeuds = {}
        for station_placee in reseau.stations:
            for noeud in station_placee.station.noeuds:
                self.noeuds[noeud.id] = noeud

        # Les arêtes, rangées par (départ, arrivée). Une arête bidirectionnelle est
        # rangée deux fois, une fois dans chaque sens.
        self.aretes = {}
        for station_placee in reseau.stations:
            for arete in station_placee.station.aretes:
                self.ranger_arete(arete)
        for tunnel in reseau.connexions:
            self.ranger_arete(tunnel)

        # φ_e : nombre d'entrées sur chaque arête pendant le pas, rangé par
        # (source, cible) de l'arête. Les deux sens comptent ensemble.
        self.entrees = {}

    def ranger_arete(self, arete):
        """Range une arête dans self.aretes, dans un sens ou dans les deux."""
        self.aretes[(arete.source, arete.cible)] = arete
        if arete.sens == "bidirectionnel":
            self.aretes[(arete.cible, arete.source)] = arete

    def ajouter_agent(self, agent):
        """Un agent arrive : il attend devant le premier nœud de son chemin."""
        self.agents.append(agent)

    def pas(self):
        """Joue un pas de temps (PLAN.md § 4.2) :
        1. les agents sur une arête avancent ;
        2. les agents en attente entrent dans le nœud suivant, s'il y a de la place ;
        3. les agents dans un nœud prennent l'arête suivante, s'il y a de la place.

        Complexité : O(A), A agents (chaque étape traite chaque agent une fois).
        """
        self.avancer()
        self.entrer_dans_les_noeuds()
        self.prendre_les_aretes()
        self.temps = self.temps + 1

    def avancer(self):
        """Étape 1 : chaque agent sur une arête avance de v · Δt."""
        for agent in self.agents:
            if agent.etat == "arete":
                if agent.pmr:
                    vitesse = self.vitesse_pmr
                else:
                    vitesse = self.vitesse_valide
                agent.position = agent.position + vitesse * DUREE_DU_PAS

                # Au bout de l'arête, il attend d'entrer dans le nœud suivant.
                arete = self.aretes[(agent.noeud, agent.chemin[0])]
                if agent.position >= arete.longueur:
                    agent.etat = "attente"

    def entrer_dans_les_noeuds(self):
        """Étape 2 : les agents en attente entrent dans le nœud suivant."""
        candidats = []
        for agent in self.agents:
            if agent.etat == "attente":
                candidats.append(agent)

        # On mélange les candidats : quand la place manque, c'est le hasard qui
        # décide qui passe.
        self.hasard.shuffle(candidats)

        for agent in candidats:
            suivant = self.noeuds[agent.chemin[0]]
            # Le nœud est plein : l'agent réessaiera au pas suivant.
            if suivant.occupation < suivant.capacite_max:
                suivant.occupation = suivant.occupation + 1
                agent.noeud = agent.chemin.pop(0)
                agent.etat = "noeud"

    def prendre_les_aretes(self):
        """Étape 3 : les agents dans un nœud prennent l'arête suivante."""
        # Nouveau pas : on recompte les entrées à partir de zéro.
        self.entrees = {}

        candidats = []
        for agent in self.agents:
            # Un agent arrivé au bout de son chemin reste dans son nœud.
            if agent.etat == "noeud" and len(agent.chemin) > 0:
                candidats.append(agent)

        # Même tirage au sort qu'à l'entrée des nœuds.
        self.hasard.shuffle(candidats)

        for agent in candidats:
            arete = self.aretes[(agent.noeud, agent.chemin[0])]
            cle = (arete.source, arete.cible)
            if cle not in self.entrees:
                self.entrees[cle] = 0

            # Une entrée de plus ne doit pas dépasser c_e · Δt. Sinon, l'arête est
            # pleine pour ce pas, et l'agent réessaiera au pas suivant.
            if self.entrees[cle] + 1 <= arete.capacite_max * DUREE_DU_PAS:
                self.entrees[cle] = self.entrees[cle] + 1
                self.noeuds[agent.noeud].occupation = self.noeuds[agent.noeud].occupation - 1
                agent.etat = "arete"
                agent.position = 0
