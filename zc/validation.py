"""Lecture typée et validée de données JSON décodées, commune aux formats du projet.

Chaque fonction lève ErreurFormat avec un message qui commence par `ou`, la
désignation de l'élément fautif (« nœud « C1 » », « connexions[2] »…).
"""

import math

from zc.modele import Nombre


class ErreurFormat(ValueError):
    """Fichier de données invalide ; le message nomme l'élément et le champ fautifs."""


def objet(valeur: object, ou: str) -> dict[str, object]:
    if not isinstance(valeur, dict):
        raise ErreurFormat(f"{ou} : objet JSON attendu")
    return valeur


def liste(valeur: object, ou: str) -> list[object]:
    if not isinstance(valeur, list):
        raise ErreurFormat(f"{ou} : liste attendue")
    return valeur


def champs(d: dict[str, object], requis: tuple[str, ...], facultatifs: tuple[str, ...],
           ou: str) -> None:
    """Refuse un champ requis manquant et un champ inconnu (faute de frappe probable)."""
    manquants = [c for c in requis if c not in d]
    if manquants:
        raise ErreurFormat(f"{ou} : champs manquants : {', '.join(manquants)}")
    inconnus = sorted(set(d) - set(requis) - set(facultatifs))
    if inconnus:
        raise ErreurFormat(f"{ou} : champs inconnus : {', '.join(inconnus)}")


def texte(d: dict[str, object], cle: str, ou: str) -> str:
    v = d[cle]
    if not isinstance(v, str) or not v:
        raise ErreurFormat(f"{ou} : « {cle} » doit être une chaîne non vide")
    return v


def booleen(d: dict[str, object], cle: str, ou: str) -> bool:
    v = d[cle]
    if not isinstance(v, bool):
        raise ErreurFormat(f"{ou} : « {cle} » doit être true ou false")
    return v


def entier(d: dict[str, object], cle: str, ou: str) -> int:
    v = d[cle]
    # bool est un sous-type d'int : true passerait pour 1 sans ce test.
    if isinstance(v, bool) or not isinstance(v, int):
        raise ErreurFormat(f"{ou} : « {cle} » doit être un entier")
    return v


def nombre(d: dict[str, object], cle: str, ou: str) -> Nombre:
    v = d[cle]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ErreurFormat(f"{ou} : « {cle} » doit être un nombre fini")
    return v


def nombre_facultatif(d: dict[str, object], cle: str, ou: str) -> Nombre | None:
    return nombre(d, cle, ou) if cle in d else None


def dans(valeur: str, ensemble: frozenset[str], cle: str, ou: str) -> str:
    if valeur not in ensemble:
        raise ErreurFormat(f"{ou} : « {cle} » vaut « {valeur} », attendu parmi "
                           f"{', '.join(sorted(ensemble))}")
    return valeur
