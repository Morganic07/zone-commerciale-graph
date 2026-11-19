# Réseau de stations spatiales — flux et évacuation

Projet de théorie des graphes : modélisation d'un réseau de trois stations spatiales,
simulation des déplacements de leurs occupants et évacuation en cas d'incendie.

- `moteur/` : modèle et algorithmes, en Python pur (codés à la main).
- `serveur/` : serveur web qui expose le moteur à la page.
- `tests/` : tests ; `networkx` n'y sert que d'oracle pour vérifier nos résultats.

## Installation

Python 3.11 ou plus récent.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
```

## Vérifications

```bash
pytest                  # tests
ruff check .            # lint
mypy moteur serveur     # typage
```

## Lancement

```bash
python -m serveur
```

puis ouvrir http://localhost:8000. Le serveur arrive avec la story 6.1 : d'ici là,
cette commande ne lance encore rien.
