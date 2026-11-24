"""Modèle de données d'une station : nœuds et arêtes.

Les noms des champs sont ceux du format JSON imposé par la consigne (§ 2.3).
"""

from dataclasses import dataclass


@dataclass
class Noeud:
    """Un module (type « module », qui remplace le « magasin » de la consigne),
    un module d'hygiène (« sanitaire »), une jonction (« carrefour ») ou un sas
    (« sortie »)."""

    id: str
    type: str
    capacite_max: int  # nombre maximal de personnes
    occupation: int  # nombre de personnes présentes
    capteur_fumee: bool
    niveau_fumee: float  # entre 0 et 100
    statut: str  # « libre », « enfumé », « bloqué » ou « sortie »
    x: float | None = None  # position sur le plan (facultatif)
    y: float | None = None


@dataclass
class Arete:
    """Un passage entre deux nœuds.
    Si `sens` vaut « unique », on ne peut aller que de `source` vers `cible`."""

    source: str
    cible: str
    capacite_max: float  # nombre maximal de personnes par seconde
    longueur: float  # en mètres
    statut: str  # « libre », « enfumé » ou « bloqué »
    sens: str  # « bidirectionnel » ou « unique »
    pmr: bool  # praticable en fauteuil roulant


@dataclass
class Station:
    """Le graphe d'une station."""

    noeuds: list[Noeud]
    aretes: list[Arete]


@dataclass
class StationDuReseau:
    """Une station placée dans le réseau. Ses nœuds ont des identifiants préfixés
    par celui de la station : « A:LAB1 » est le nœud LAB1 de la station A."""

    id: str
    station: Station
    fichier: str  # chemin du plan, relatif au dossier du réseau (« stations/A.json »)
    x: float | None = None  # position sur la vue d'ensemble (facultatif)
    y: float | None = None


@dataclass
class Source:
    """Un point d'arrivée des visiteurs, de capacité illimitée."""

    id: str
    type: str  # « spatioport », « habitat » ou « relais »
    x: float | None = None  # position sur la vue d'ensemble (facultatif)
    y: float | None = None


@dataclass
class Reseau:
    """Le réseau : des stations, des sources, et les tunnels (connexions) qui relient
    une source ou la sortie d'une station à une autre source ou une autre sortie."""

    stations: list[StationDuReseau]
    sources: list[Source]
    connexions: list[Arete]
