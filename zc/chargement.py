"""Lecture et écriture des fichiers de données. C'est le seul module du moteur, avec
l'export des indicateurs, qui touche au disque (CLAUDE.md)."""

import json
from pathlib import Path
from typing import Any

from zc import format_centre, format_zone, parametres
from zc.modele import Centre, ErreurFormat, Zone
from zc.parametres import ParametresPhysiques


def lire_json(chemin: Path) -> Any:
    """Lit un fichier JSON. Lève ErreurFormat si le fichier manque ou est mal écrit."""
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError:
        raise ErreurFormat(f"{chemin} illisible")
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        raise ErreurFormat(f"{chemin} n'est pas du JSON valide")


def charger_parametres(chemin: Path) -> ParametresPhysiques:
    """Charge `parametres.json`."""
    donnees = lire_json(chemin)
    try:
        return parametres.depuis_dict(donnees)
    except ErreurFormat as erreur:
        raise ErreurFormat(f"{chemin} : {erreur}")


def charger_centre(chemin: Path) -> Centre:
    """Charge un fichier de centre."""
    donnees = lire_json(chemin)
    try:
        return format_centre.depuis_dict(donnees)
    except ErreurFormat as erreur:
        raise ErreurFormat(f"{chemin} : {erreur}")


def charger_zone(chemin: Path) -> Zone:
    """Charge une zone et ses centres. Les fichiers des centres sont cherchés dans le
    même dossier que la zone. Un fichier utilisé par deux centres n'est lu qu'une fois."""
    donnees = lire_json(chemin)

    # D'abord les centres : une erreur dans un centre nomme le fichier du centre.
    centres_lus = {}
    for d in donnees["centres"]:
        fichier = d["fichier"]
        if fichier not in centres_lus:
            centres_lus[fichier] = charger_centre(chemin.parent / fichier)

    # Ensuite la zone : une erreur ici nomme le fichier de la zone.
    try:
        return format_zone.depuis_dict(donnees, centres_lus)
    except ErreurFormat as erreur:
        raise ErreurFormat(f"{chemin} : {erreur}")


def ecrire_centre(centre: Centre, chemin: Path) -> None:
    """Écrit un centre dans un fichier JSON, accents conservés."""
    texte = json.dumps(format_centre.vers_dict(centre), ensure_ascii=False, indent=2)
    chemin.write_text(texte + "\n", encoding="utf-8")
