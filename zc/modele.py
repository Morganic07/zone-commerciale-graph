"""Modèle d'un centre commercial (consigne § 2.1) : nœuds, arêtes et ensembles de valeurs.

Les noms des champs sont ceux du format JSON imposé (consigne § 2.3), pour qu'un champ
se lise de la même façon dans le fichier, le code et le rapport.
"""

from dataclasses import dataclass, field

Nombre = int | float

TYPES = frozenset({"magasin", "sanitaire", "carrefour", "sortie"})
STATUTS_NOEUD = frozenset({"libre", "enfumé", "bloqué", "sortie"})
STATUTS_ARETE = frozenset({"libre", "enfumé", "bloqué"})
SENS = frozenset({"bidirectionnel", "unique"})

FUMEE_MIN, FUMEE_MAX = 0, 100


@dataclass
class Noeud:
    """Magasin, sanitaire, carrefour ou sortie. `x`, `y` et `nom` sont des champs
    facultatifs ajoutés au format (position sur le plan, libellé) : PLAN.md § 2.1."""

    id: str
    type: str
    capacite_max: int  # personnes admissibles
    occupation: int  # personnes présentes à l'instant t
    capteur_fumee: bool
    niveau_fumee: Nombre  # dans [0, 100]
    statut: str
    x: Nombre | None = None
    y: Nombre | None = None
    nom: str | None = None

    @property
    def taux_occupation(self) -> float:
        """τ_v = o_v / c_v, dans [0, 1] (consigne § 2.2)."""
        return self.occupation / self.capacite_max


@dataclass
class Arete:
    """Couloir ou passage entre deux nœuds. `sens == "unique"` signifie : seulement de
    `source` vers `cible`. `largeur` est le champ facultatif prévu par la consigne."""

    source: str
    cible: str
    capacite_max: Nombre  # personnes par unité de temps
    longueur: Nombre  # mètres
    statut: str
    sens: str
    pmr: bool
    largeur: Nombre | None = None


@dataclass
class Centre:
    """Graphe d'un centre commercial. L'ordre des listes est celui du fichier, conservé
    pour que la réécriture reproduise le fichier."""

    noeuds: list[Noeud] = field(default_factory=list)
    aretes: list[Arete] = field(default_factory=list)

    def noeud(self, identifiant: str) -> Noeud:
        for n in self.noeuds:
            if n.id == identifiant:
                return n
        raise KeyError(identifiant)
