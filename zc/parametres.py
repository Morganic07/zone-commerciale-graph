"""Valeurs physiques du modèle, chacune avec sa source publiée (PLAN.md § 4.1).

Elles viennent toutes de `donnees/parametres.json`. Une valeur sans source ou sans
année est refusée, pour que le rapport puisse citer l'origine de chaque chiffre.
"""

from dataclasses import dataclass
from typing import Any

from zc.modele import ErreurFormat

CLES = ["vitesse_marche", "vitesse_pmr", "debit_specifique_max", "densite_max"]


@dataclass
class ParametresPhysiques:
    """Valeurs physiques de la simulation."""

    vitesse_marche: float  # m/s, piéton valide
    vitesse_pmr: float  # m/s, personne en fauteuil roulant manuel
    debit_specifique_max: float  # personnes par mètre de largeur et par seconde
    densite_max: float  # personnes par m²


def depuis_dict(donnees: dict[str, Any]) -> ParametresPhysiques:
    """Lit les paramètres. Refuse un paramètre manquant, une valeur sans source ou
    sans année, et une valeur nulle ou négative."""
    valeurs = {}
    for cle in CLES:
        if cle not in donnees:
            raise ErreurFormat(f"paramètre « {cle} » manquant")
        entree = donnees[cle]
        if not entree.get("source"):
            raise ErreurFormat(f"« {cle} » : source absente ; chaque valeur doit être sourcée")
        if not entree.get("annee"):
            raise ErreurFormat(f"« {cle} » : année de la source absente")
        if entree["valeur"] <= 0:
            raise ErreurFormat(f"« {cle} » : la valeur doit être positive")
        valeurs[cle] = entree["valeur"]

    return ParametresPhysiques(
        vitesse_marche=valeurs["vitesse_marche"],
        vitesse_pmr=valeurs["vitesse_pmr"],
        debit_specifique_max=valeurs["debit_specifique_max"],
        densite_max=valeurs["densite_max"],
    )
