"""Lecture des fichiers de données. Seul module du moteur, avec l'export des
indicateurs, à toucher au disque (CLAUDE.md)."""

import json
from pathlib import Path

from zc import format_centre, format_zone, parametres
from zc.modele import Centre, Zone
from zc.parametres import ErreurParametres, ParametresPhysiques
from zc.validation import ErreurFormat


def _lire_json(chemin: Path, erreur: type[ValueError]) -> object:
    """Contenu JSON décodé d'un fichier ; un fichier illisible ou mal formé lève
    l'erreur propre au type de fichier, avec son chemin."""
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError as e:
        raise erreur(f"{chemin} illisible : {e}") from e
    try:
        return json.loads(texte)
    except json.JSONDecodeError as e:
        raise erreur(f"{chemin} n'est pas du JSON valide : {e}") from e


def charger_parametres(chemin: Path) -> ParametresPhysiques:
    """Charge et valide `parametres.json`. Lève ErreurParametres si le fichier est
    illisible, n'est pas du JSON, ou si une valeur est invalide ou non sourcée."""
    donnees = _lire_json(chemin, ErreurParametres)
    try:
        return parametres.depuis_dict(donnees)
    except ErreurParametres as e:
        raise ErreurParametres(f"{chemin} : {e}") from e


def charger_centre(chemin: Path) -> Centre:
    """Charge et valide un centre au format imposé. Lève ErreurFormat en cas d'échec,
    avec le chemin du fichier en tête du message."""
    donnees = _lire_json(chemin, ErreurFormat)
    try:
        return format_centre.depuis_dict(donnees)
    except ErreurFormat as e:
        raise ErreurFormat(f"{chemin} : {e}") from e


def charger_zone(chemin: Path) -> Zone:
    """Charge une zone et ses centres. Les chemins « fichier » des centres sont relatifs
    au dossier de `chemin`. Lève ErreurFormat avec le chemin du fichier fautif."""
    donnees = _lire_json(chemin, ErreurFormat)

    def charger(fichier: str) -> Centre:
        try:
            return charger_centre(chemin.parent / fichier)
        except ErreurFormat as e:
            raise _ErreurFichierCentre(str(e)) from e

    try:
        return format_zone.depuis_dict(donnees, charger)
    except _ErreurFichierCentre:
        raise  # porte déjà le chemin du fichier de centre fautif
    except ErreurFormat as e:
        raise ErreurFormat(f"{chemin} : {e}") from e


class _ErreurFichierCentre(ErreurFormat):
    """Erreur venue d'un fichier de centre lu pendant le chargement d'une zone : son
    message nomme déjà ce fichier, il ne faut pas le préfixer par celui de la zone."""


def ecrire_centre(centre: Centre, chemin: Path) -> None:
    """Écrit un centre au format imposé, en UTF-8, accents conservés."""
    texte = json.dumps(format_centre.vers_dict(centre), ensure_ascii=False, indent=2)
    chemin.write_text(texte + "\n", encoding="utf-8")
