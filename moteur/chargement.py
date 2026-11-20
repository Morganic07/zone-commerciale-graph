"""Lecture des fichiers JSON du projet."""

import json
from pathlib import Path
from typing import Any

from moteur.modele import ErreurFormat


def est_justifie(parametre: dict[str, Any]) -> bool:
    """Vrai si le paramètre cite une source avec son année, ou s'il est une hypothèse
    expliquée. Une valeur physique sans l'un ni l'autre ne peut pas être défendue."""
    source = parametre.get("source") or ""
    annee = parametre.get("annee")
    hypothese = parametre.get("hypothese") or ""
    if source.strip() != "" and annee is not None:
        return True
    return hypothese.strip() != ""


def charger_parametres(chemin: Path) -> dict[str, float]:
    """Lit `parametres.json` et renvoie la valeur de chaque paramètre, par son nom.

    Refuse un paramètre sans valeur, ou sans source datée ni hypothèse.
    Complexité : O(n), n étant le nombre de paramètres.
    """
    with open(chemin, encoding="utf-8") as fichier:
        donnees: dict[str, Any] = json.load(fichier)

    valeurs: dict[str, float] = {}
    for nom, parametre in donnees.items():
        if parametre.get("valeur") is None:
            raise ErreurFormat(f"paramètre « {nom} » : valeur manquante")
        if not est_justifie(parametre):
            raise ErreurFormat(
                f"paramètre « {nom} » : il faut une source avec son année, "
                "ou une hypothèse avec son raisonnement"
            )
        valeurs[nom] = parametre["valeur"]
    return valeurs
