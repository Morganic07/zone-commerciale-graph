"""Palette de couleurs : du taux d'occupation à un niveau de 1 à 5 (PLAN.md § 4.3).

Les bornes sont 0,2 / 0,4 / 0,6 / 0,8. Les seuils imposés par la consigne (0,4 et 0,8)
tombent sur des bornes : on retrouve la lecture vert / orange / rouge de la consigne
en regroupant les niveaux 1-2, 3-4 et 5. Les couleurs elles-mêmes sont choisies avec
l'interface (étape de design).
"""

BORNES = [0.2, 0.4, 0.6, 0.8]


def niveau(taux: float) -> int:
    """Niveau de 1 (très faible) à 5 (très élevé). Une borne appartient au niveau
    supérieur : 0,2 donne le niveau 2, 0,8 le niveau 5."""
    resultat = 1
    for borne in BORNES:
        if taux >= borne:
            resultat += 1
    return resultat
