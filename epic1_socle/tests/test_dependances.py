"""Le moteur (les dossiers `epic*/moteur/`) reste pur : ni bibliothèque de graphes, ni
dépendance web.

Les algorithmes doivent être codés à la main (networkx ne sert que d'oracle dans les
tests), et le moteur doit se tester sans serveur (PLAN.md § 1).
"""

import ast
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent.parent
INTERDITS = {"networkx", "fastapi", "uvicorn"}


def imports_interdits(source: str) -> set[str]:
    """Modules interdits importés par un code source, à n'importe quelle profondeur
    (dans une fonction, sous un `if`…). Les imports relatifs sont internes au paquet.

    Complexité : O(n), n étant le nombre de nœuds de l'arbre syntaxique.
    """
    trouves: set[str] = set()
    for noeud in ast.walk(ast.parse(source)):
        noms: list[str] = []
        if isinstance(noeud, ast.Import):
            for alias in noeud.names:
                noms.append(alias.name)
        elif isinstance(noeud, ast.ImportFrom) and noeud.level == 0 and noeud.module:
            noms.append(noeud.module)
        for nom in noms:
            # « networkx.algorithms » appartient à la bibliothèque « networkx ».
            racine = nom.split(".")[0]
            if racine in INTERDITS:
                trouves.add(racine)
    return trouves


def fichiers_du_moteur() -> list[Path]:
    # Chaque epic range son moteur dans son propre dossier moteur/ : on les prend tous.
    return sorted(RACINE.glob("epic*/moteur/**/*.py"))


def test_le_moteur_existe() -> None:
    # Sans ce garde-fou, un moteur déplacé ferait passer le test suivant à vide.
    # Le moteur n'a pas de __init__.py (choix du 2026-11-20) : on vérifie qu'il a du code.
    assert len(fichiers_du_moteur()) > 0


@pytest.mark.parametrize("fichier", fichiers_du_moteur())
def test_aucun_import_interdit_dans_le_moteur(fichier: Path) -> None:
    interdits = imports_interdits(fichier.read_text(encoding="utf-8"))
    assert not interdits, fichier.name + " importe " + str(sorted(interdits))


@pytest.mark.parametrize(
    "source, attendu",
    [
        ("import networkx", {"networkx"}),
        ("import networkx as nx", {"networkx"}),
        ("from networkx.algorithms import shortest_paths", {"networkx"}),
        ("import os, fastapi", {"fastapi"}),
        ("def f():\n    import uvicorn\n", {"uvicorn"}),
        ("if True:\n    from fastapi import FastAPI\n", {"fastapi"}),
        ("import heapq\nfrom collections import deque", set()),
        ("from . import networkx", set()),  # module interne au paquet, pas la bibliothèque
        ("import networkxx", set()),
    ],
)
def test_detection_des_imports(source: str, attendu: set[str]) -> None:
    assert imports_interdits(source) == attendu
