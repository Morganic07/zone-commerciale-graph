"""Modèle de la zone commerciale : nœuds, arêtes, centres, sources et zone.

Les noms des champs sont ceux du format JSON imposé par la consigne (§ 2.3).
"""

from dataclasses import dataclass

# Valeurs autorisées pour certains champs.
TYPES = ["magasin", "sanitaire", "carrefour", "sortie"]
STATUTS_NOEUD = ["libre", "enfumé", "bloqué", "sortie"]
STATUTS_ARETE = ["libre", "enfumé", "bloqué"]
SENS = ["bidirectionnel", "unique"]
TYPES_SOURCE = ["parking", "station", "quartier"]

# Dans la zone, un nœud de centre s'écrit « A:S1 » (centre A, nœud S1).
SEPARATEUR = ":"


class ErreurFormat(Exception):
    """Erreur dans un fichier de données. Le message dit ce qui ne va pas."""


@dataclass
class Noeud:
    """Un magasin, un sanitaire, un carrefour ou une sortie."""

    id: str
    type: str
    capacite_max: int  # nombre maximal de personnes
    occupation: int  # nombre de personnes présentes
    capteur_fumee: bool
    niveau_fumee: float  # entre 0 et 100
    statut: str
    x: float | None = None  # position sur le plan (facultatif)
    y: float | None = None
    nom: str | None = None  # libellé lisible (facultatif)

    def taux_occupation(self) -> float:
        """Taux d'occupation τ = occupation / capacité, entre 0 et 1."""
        return self.occupation / self.capacite_max


@dataclass
class Arete:
    """Un couloir (dans un centre) ou une connexion (dans la zone).
    Si `sens` vaut « unique », on ne peut aller que de `source` vers `cible`."""

    source: str
    cible: str
    capacite_max: float  # nombre maximal de personnes par seconde
    longueur: float  # en mètres
    statut: str
    sens: str
    pmr: bool  # praticable en fauteuil roulant
    largeur: float | None = None  # en mètres (facultatif)


@dataclass
class Centre:
    """Le graphe d'un centre commercial."""

    noeuds: list[Noeud]
    aretes: list[Arete]

    def noeud(self, identifiant: str) -> Noeud:
        """Renvoie le nœud qui a cet identifiant."""
        for n in self.noeuds:
            if n.id == identifiant:
                return n
        raise KeyError(identifiant)


@dataclass
class Source:
    """Un parking, une station ou un quartier, d'où partent les visiteurs."""

    id: str
    type: str
    x: float | None = None
    y: float | None = None


@dataclass
class CentreZone:
    """Un centre placé dans la zone. Ses nœuds ont des identifiants préfixés (« A:S1 »)."""

    id: str
    centre: Centre
    x: float | None = None
    y: float | None = None


def macro_noeud(identifiant: str) -> str:
    """Renvoie le centre d'un nœud (« A:S1 » → « A »), ou la source elle-même (« P1 »)."""
    if SEPARATEUR in identifiant:
        return identifiant.split(SEPARATEUR)[0]
    return identifiant


@dataclass
class Zone:
    """La zone commerciale : des centres, des sources et des connexions entre eux."""

    centres: list[CentreZone]
    sources: list[Source]
    connexions: list[Arete]

    def vue_macro(self) -> tuple[list[str], list[tuple[str, str]]]:
        """Graphe simplifié : un sommet par centre et par source, une arête par connexion."""
        sommets = []
        for c in self.centres:
            sommets.append(c.id)
        for s in self.sources:
            sommets.append(s.id)
        aretes = []
        for connexion in self.connexions:
            aretes.append((macro_noeud(connexion.source), macro_noeud(connexion.cible)))
        return sommets, aretes
