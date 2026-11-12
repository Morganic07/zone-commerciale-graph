# Zone commerciale

Modélisation d'une zone commerciale par des graphes, simulation des flux de visiteurs et de l'évacuation en cas d'incendie, analyse du graphe des propriétaires.

Projet de théorie des graphes. Le sujet est dans `consignes.pdf`, l'architecture et les choix de modélisation dans `PLAN.md`, l'avancement dans `AVANCEMENT.md`.

## Installation

Python 3.11 ou plus récent.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
```

## Lancement

```bash
python -m serveur
```

Puis ouvrir http://localhost:8000. *Disponible à partir de la story 6.1 : le serveur n'est pas encore écrit.*

## Vérifications

```bash
pytest              # tests unitaires
ruff check .        # lint
mypy zc serveur     # typage
```

## Organisation

| Dossier | Rôle |
|---|---|
| `zc/` | moteur en Python pur : modèle, algorithmes de graphes codés à la main, simulation |
| `serveur/` | serveur web qui expose le moteur à la page |
| `web/` | page d'affichage de la simulation |
| `donnees/` | plans des centres, zone, scénarios, paramètres physiques sourcés |
| `tests/` | tests unitaires ; `networkx` n'y sert que d'oracle pour vérifier nos algorithmes |
| `rapport/` | rapport en Markdown, converti en PDF |
