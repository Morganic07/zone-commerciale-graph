"""Le moteur `zc/` reste pur : ni bibliothèque de graphes, ni dépendance web.

Les algorithmes doivent être codés à la main (networkx ne sert que d'oracle dans les
tests), et le moteur doit se tester sans serveur (PLAN.md § 1).
"""

import ast
from pathlib import Path

import pytest

RACINE_ZC = Path(__file__).resolve().parent.parent / "zc"
INTERDITS = frozenset({"networkx", "fastapi", "uvicorn"})


def imports_interdits(source: str) -> set[str]:
    """Modules interdits importés par un code source, à n'importe quelle profondeur
    (dans une fonction, sous un `if`…). Les imports relatifs sont internes au paquet."""
    trouves: set[str] = set()
    for noeud in ast.walk(ast.parse(source)):
        if isinstance(noeud, ast.Import):
            racines = [alias.name.split(".")[0] for alias in noeud.names]
        elif isinstance(noeud, ast.ImportFrom) and noeud.level == 0 and noeud.module:
            racines = [noeud.module.split(".")[0]]
        else:
            continue
        trouves.update(r for r in racines if r in INTERDITS)
    return trouves


def fichiers_du_moteur() -> list[Path]:
    return sorted(RACINE_ZC.rglob("*.py"))


def test_le_moteur_existe() -> None:
    # Sans ce garde-fou, un dossier zc/ déplacé ferait passer le test suivant à vide.
    assert (RACINE_ZC / "__init__.py").is_file()


@pytest.mark.parametrize("fichier", fichiers_du_moteur(), ids=lambda f: f.name)
def test_aucun_import_interdit_dans_zc(fichier: Path) -> None:
    interdits = imports_interdits(fichier.read_text(encoding="utf-8"))
    assert not interdits, f"{fichier.relative_to(RACINE_ZC.parent)} importe {sorted(interdits)}"


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
