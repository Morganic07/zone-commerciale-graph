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

`pip install -e .` suffit pour lancer l'application ; `[test]` ajoute les outils de
vérification. La page n'appelle aucun service en ligne : Cytoscape.js et la police sont
copiés dans `web/vendor/`.

## Lancement

```bash
. .venv/bin/activate
python -m serveur
```

Puis ouvrir http://localhost:8000 dans un navigateur. Pour un autre port :
`ZC_PORT=8080 python -m serveur`.

## Démonstration

1. Choisir un scénario, puis « Charger ».
2. « Lancer » fait avancer la simulation à la vitesse choisie (× 1 à × 60) ; « Pause »
   l'arrête, « Pas à pas » avance d'une seconde.
3. Les réglages du panneau s'appliquent aussitôt (ceux de l'incendie, au prochain feu).
   « Allumer un feu », puis un clic sur un nœud d'un centre, déclenche un incendie.
   « Tracer » dessine l'itinéraire d'une source vers un centre, avec son coût.

| Scénario | Ce qu'il montre |
|---|---|
| Journée normale | affluence ordinaire, sans incendie |
| Pic d'affluence | cinq fois plus d'arrivées : files d'attente aux entrées |
| Incendie qui bloque une sortie | feu à 3 min près de la sortie est du centre A ; elle se bloque pendant l'évacuation, qui se termine par la sortie ouest |

Les scénarios sont dans `donnees/scenarios/`, un fichier JSON chacun (format décrit en
tête de `serveur/session.py`).

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
