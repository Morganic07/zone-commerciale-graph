"""Dessine le plan d'un centre en SVG, à partir de son fichier JSON.

    python rapport/dessiner_plan.py donnees/centres/A.json rapport/figures/plan_A.svg

Le dessin vient des données : une modification du fichier se voit en relançant le script.
"""

import math
import sys
from pathlib import Path

from zc.chargement import charger_centre

ECHELLE = 12  # pixels par mètre
MARGE = 60  # pixels autour du plan
RAYON = 15  # rayon des nœuds, en pixels

COULEURS = {
    "magasin": "#4C78A8",
    "carrefour": "#8C8C8C",
    "sortie": "#2E7D32",
    "sanitaire": "#8E44AD",
}


def position(x: float, y: float) -> tuple[float, float]:
    """Convertit une position en mètres en position en pixels."""
    return MARGE + x * ECHELLE, MARGE + y * ECHELLE


def dessiner(fichier_centre: Path, fichier_svg: Path) -> None:
    centre = charger_centre(fichier_centre)

    # Taille du dessin : la plus grande position, plus les marges et la légende.
    largeur = 0.0
    hauteur = 0.0
    for n in centre.noeuds:
        px, py = position(n.x or 0, n.y or 0)
        largeur = max(largeur, px + MARGE)
        hauteur = max(hauteur, py + MARGE)
    hauteur_totale = hauteur + 110  # place pour la légende

    lignes = []
    lignes.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{largeur:.0f}" '
                  f'height="{hauteur_totale:.0f}" font-family="sans-serif">')
    # Taille de la flèche en pixels, indépendante de l'épaisseur du couloir.
    lignes.append('<defs><marker id="fleche" viewBox="0 0 10 10" refX="9" refY="5" '
                  'markerWidth="16" markerHeight="16" markerUnits="userSpaceOnUse" '
                  'orient="auto">'
                  '<path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker></defs>')
    lignes.append(f'<rect width="{largeur:.0f}" height="{hauteur_totale:.0f}" fill="white"/>')

    # Les arêtes d'abord, pour que les nœuds soient dessinés par-dessus.
    for a in centre.aretes:
        source = centre.noeud(a.source)
        cible = centre.noeud(a.cible)
        x1, y1 = position(source.x or 0, source.y or 0)
        x2, y2 = position(cible.x or 0, cible.y or 0)
        epaisseur = 2 + (a.largeur or 1) * 2
        couleur = "#BBBBBB"
        style = ""
        if not a.pmr:
            couleur = "#E07B00"
            style = ' stroke-dasharray="10,6"'
        fleche = ""
        if a.sens == "unique":
            # On raccourcit la ligne pour que la flèche ne soit pas cachée par le nœud.
            distance = math.hypot(x2 - x1, y2 - y1)
            x2 = x2 - (x2 - x1) * (RAYON + 4) / distance
            y2 = y2 - (y2 - y1) * (RAYON + 4) / distance
            fleche = ' marker-end="url(#fleche)"'
        lignes.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                      f'stroke="{couleur}" stroke-width="{epaisseur:.1f}"{style}{fleche}/>')
        # Capacité au milieu de l'arête (sauf les très courtes, où elle cacherait un nom).
        if a.longueur >= 10:
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            lignes.append(f'<text x="{mx:.1f}" y="{my - 6:.1f}" font-size="10" fill="#555" '
                          f'text-anchor="middle">{a.capacite_max:g} p/s</text>')

    for n in centre.noeuds:
        px, py = position(n.x or 0, n.y or 0)
        bord = ' stroke="#222" stroke-width="2"'
        if not n.capteur_fumee:
            bord = ' stroke="#D62728" stroke-width="3" stroke-dasharray="4,3"'
        lignes.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{RAYON}" '
                      f'fill="{COULEURS[n.type]}"{bord}/>')
        lignes.append(f'<text x="{px:.1f}" y="{py + 4:.1f}" font-size="11" fill="white" '
                      f'text-anchor="middle" font-weight="bold">{n.id}</text>')
        lignes.append(f'<text x="{px:.1f}" y="{py + RAYON + 13:.1f}" font-size="10" '
                      f'fill="#222" text-anchor="middle">{n.nom or ""} ({n.capacite_max})</text>')

    # Légende.
    y = hauteur + 20
    x = MARGE
    for type_noeud, couleur in COULEURS.items():
        lignes.append(f'<circle cx="{x}" cy="{y}" r="8" fill="{couleur}"/>')
        lignes.append(f'<text x="{x + 14}" y="{y + 4}" font-size="12">{type_noeud}</text>')
        x += 120
    y += 30
    x = MARGE
    lignes.append(f'<circle cx="{x}" cy="{y}" r="8" fill="white" stroke="#D62728" '
                  'stroke-width="3" stroke-dasharray="4,3"/>')
    lignes.append(f'<text x="{x + 14}" y="{y + 4}" font-size="12">sans capteur de fumée</text>')
    x += 200
    lignes.append(f'<line x1="{x}" y1="{y}" x2="{x + 40}" y2="{y}" stroke="#E07B00" '
                  'stroke-width="6" stroke-dasharray="10,6"/>')
    lignes.append(f'<text x="{x + 48}" y="{y + 4}" font-size="12">non PMR (marches)</text>')
    x += 190
    lignes.append(f'<line x1="{x}" y1="{y}" x2="{x + 40}" y2="{y}" stroke="#BBBBBB" '
                  'stroke-width="6" marker-end="url(#fleche)"/>')
    lignes.append(f'<text x="{x + 48}" y="{y + 4}" font-size="12">sens unique</text>')
    y += 30
    lignes.append(f'<text x="{MARGE}" y="{y + 4}" font-size="12">Épaisseur des couloirs '
                  'proportionnelle à leur largeur ; capacité des couloirs en personnes par '
                  'seconde ; capacité des nœuds entre parenthèses.</text>')

    lignes.append("</svg>")
    fichier_svg.parent.mkdir(parents=True, exist_ok=True)
    fichier_svg.write_text("\n".join(lignes) + "\n", encoding="utf-8")


if __name__ == "__main__":
    dessiner(Path(sys.argv[1]), Path(sys.argv[2]))
