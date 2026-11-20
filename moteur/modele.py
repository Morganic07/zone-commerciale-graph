"""Modèle de données d'une station : nœuds et arêtes.

Les noms des champs sont ceux du format JSON imposé par la consigne (§ 2.3).
"""

from dataclasses import dataclass


@dataclass
class Noeud:
    """Un module (type « magasin »), un module d'hygiène (« sanitaire »),
    une jonction (« carrefour ») ou une sortie."""

    id: str
    type: str
    capacite_max: int  # nombre maximal de personnes
    occupation: int  # nombre de personnes présentes
    capteur_fumee: bool
    niveau_fumee: float  # entre 0 et 100
    statut: str  # « libre », « enfumé », « bloqué » ou « sortie »
    x: float | None = None  # position sur le plan (facultatif)
    y: float | None = None
    nom: str | None = None  # libellé affiché (facultatif)


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
    largeur: float | None = None  # en mètres (facultatif)


@dataclass
class Station:
    """Le graphe d'une station."""

    noeuds: list[Noeud]
    aretes: list[Arete]
