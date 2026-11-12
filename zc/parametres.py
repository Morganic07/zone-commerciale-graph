"""Valeurs physiques du modèle, chacune adossée à une source publiée (PLAN.md § 4.1).

Aucune constante physique n'est écrite en dur dans le moteur : elles viennent toutes de
`donnees/parametres.json`, validé ici. Une valeur sans source ou sans année est refusée,
pour que le rapport puisse citer l'origine de chaque chiffre.
"""

import math
from dataclasses import dataclass

# Clé attendue → unité exigée. L'unité est vérifiée pour qu'une valeur saisie dans une
# autre unité (km/h au lieu de m/s…) ne passe pas en silence.
UNITES: dict[str, str] = {
    "vitesse_marche": "m/s",
    "vitesse_pmr": "m/s",
    "debit_specifique_max": "pers/(m.s)",
    "densite_max": "pers/m2",
}

ANNEE_MIN, ANNEE_MAX = 1900, 2100


class ErreurParametres(ValueError):
    """Fichier de paramètres invalide ; le message nomme la clé fautive."""


@dataclass(frozen=True)
class ParametresPhysiques:
    """Valeurs physiques de la simulation, en unités SI."""

    vitesse_marche: float  # m/s, piéton valide
    vitesse_pmr: float  # m/s, personne à mobilité réduite (fauteuil manuel)
    debit_specifique_max: float  # personnes par mètre de largeur et par seconde
    densite_max: float  # personnes par m²


def _valeur(cle: str, entree: object) -> float:
    if not isinstance(entree, dict):
        raise ErreurParametres(f"« {cle} » doit être un objet {{valeur, unite, source, annee}}")
    valeur = entree.get("valeur")
    # bool est un sous-type d'int en Python : true passerait pour 1 sans ce test.
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise ErreurParametres(f"« {cle} » : valeur numérique attendue, reçu {valeur!r}")
    if not math.isfinite(valeur) or valeur <= 0:
        raise ErreurParametres(f"« {cle} » : valeur strictement positive attendue, reçu {valeur}")
    unite = entree.get("unite")
    if unite != UNITES[cle]:
        raise ErreurParametres(f"« {cle} » : unité « {UNITES[cle]} » attendue, reçu {unite!r}")
    source = entree.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ErreurParametres(f"« {cle} » : source absente ; chaque valeur doit être sourcée")
    annee = entree.get("annee")
    if isinstance(annee, bool) or not isinstance(annee, int) or not (
        ANNEE_MIN <= annee <= ANNEE_MAX
    ):
        raise ErreurParametres(f"« {cle} » : année de la source absente ou invalide ({annee!r})")
    return float(valeur)


def depuis_dict(donnees: object) -> ParametresPhysiques:
    """Valide le contenu décodé de `parametres.json` et en tire les valeurs.

    Refuse une clé manquante, une clé inconnue (faute de frappe probable), une valeur non
    positive, une unité inattendue, une source vide ou une année absente.
    """
    if not isinstance(donnees, dict):
        raise ErreurParametres("le fichier de paramètres doit contenir un objet JSON")
    manquantes = sorted(set(UNITES) - set(donnees))
    if manquantes:
        raise ErreurParametres(f"paramètres manquants : {', '.join(manquantes)}")
    inconnues = sorted(set(donnees) - set(UNITES))
    if inconnues:
        raise ErreurParametres(f"paramètres inconnus : {', '.join(inconnues)}")
    valeurs = {cle: _valeur(cle, donnees[cle]) for cle in UNITES}
    return ParametresPhysiques(**valeurs)
