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


def macro_noeud(identifiant: str) -> str:
    """Renvoie le macro-nœud d'un nœud : sa station (« A:SAS1 » donne « A »),
    ou la source elle-même (« P1 » donne « P1 »)."""
    if ":" in identifiant:
        morceaux = identifiant.split(":")
        return morceaux[0]
    return identifiant


def vue_macro(reseau: Reseau) -> tuple[list[str], list[tuple[str, str]]]:
    """Graphe simplifié du réseau : un sommet par station et par source, une arête par
    tunnel. Renvoie la liste des sommets et la liste des arêtes (paires de sommets).

    Complexité : O(S + P + C), S stations, P sources et C connexions.
    """
    sommets = []
    for station_du_reseau in reseau.stations:
        sommets.append(station_du_reseau.id)
    for source in reseau.sources:
        sommets.append(source.id)

    aretes = []
    for connexion in reseau.connexions:
        depart = macro_noeud(connexion.source)
        arrivee = macro_noeud(connexion.cible)
        aretes.append((depart, arrivee))

    return sommets, aretes
