"""Lecture des fichiers de données. Seul module du moteur, avec l'export des
indicateurs, à toucher au disque (CLAUDE.md)."""

import json
from pathlib import Path

from zc.parametres import ErreurParametres, ParametresPhysiques, depuis_dict


def charger_parametres(chemin: Path) -> ParametresPhysiques:
    """Charge et valide `parametres.json`. Lève ErreurParametres si le fichier est
    illisible, n'est pas du JSON, ou si une valeur est invalide ou non sourcée."""
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError as erreur:
        raise ErreurParametres(f"{chemin} illisible : {erreur}") from erreur
    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError as erreur:
        raise ErreurParametres(f"{chemin} n'est pas du JSON valide : {erreur}") from erreur
    return depuis_dict(donnees)
