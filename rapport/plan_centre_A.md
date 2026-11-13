# Plan de test du centre détaillé A

> **Plan provisoire.** Ce plan sert à implémenter et tester la simulation. Ce n'est pas le plan définitif : celui-ci sera dessiné par le binôme (story 2.6 d'`AVANCEMENT.md`), puis remplacera `donnees/centres/A.json` et cette figure.

![Plan du centre A](figures/plan_A.svg)

Centre de plain-pied d'environ 170 m × 60 m (38 nœuds, agrandi à la story 2.7) : une allée principale est–ouest de cinq places, une galerie au nord et une galerie au sud de quatre nœuds chacune, reliées à l'allée en zigzag, 20 magasins, 2 sanitaires, et une issue de secours au sud en plus des deux sorties. L'issue de secours n'est reliée à aucune connexion de la zone, et au centre par un seul couloir (vers `S2`) : on ne peut ni entrer par elle ni la traverser, mais on évacue par elle. Les données sont dans `donnees/centres/A.json` ; la figure se régénère avec la commande ci-dessous, depuis la racine du projet et avec l'environnement `.venv` activé (le script importe le moteur `zc`, installé par `pip install -e ".[test]"`, voir le README) :

```bash
python rapport/dessiner_plan.py donnees/centres/A.json rapport/figures/plan_A.svg
```

Après toute modification du JSON, relancer `pytest tests/test_plan_A.py` : il vérifie que le plan contient toujours chacun des cas ci-dessous. Le plan définitif devra lui aussi les contenir.

## Les cas couverts (PLAN.md § 6)

| Cas demandé | Où dans le plan |
|---|---|
| 2 sorties sur des côtés opposés | `EO` à l'ouest, `EE` à l'est ; plus l'issue de secours `ES` au sud |
| Au moins 6 magasins et 1 sanitaire | `M1` à `M20`, sanitaires `SA1` et `SA2` |
| Un cycle, donc des chemins alternatifs | chaque triangle `Cx – Nx – Cy` ou `Cx – Sx – Cy`, et les deux galeries entières |
| Un goulot sur un passage fréquenté | `C5 – C6` : 1,2 m de large (un kiosque rétrécit l'allée), sur le plus court chemin entre les deux sorties |
| Une arête non PMR, contournable | `N2 – N3` : marches. Un fauteuil passe par `N2 – C5 – N3` (48,2 m au lieu de 36 m) |
| Une arête à sens unique | `C1 → S1` : on entre dans la galerie sud par l'ouest seulement |
| 2 nœuds sans capteur, dont un sur un chemin d'évacuation | `C1`, `N4`, `S3`, `SA1` et `SA2`. `C1` est sur le chemin des magasins de l'ouest vers la sortie `EO` |
| Un feu possible près d'une sortie | `M18` (presse) est à deux couloirs de `EO`, `M19` (pharmacie) à deux couloirs de `EE` ; le scénario de démonstration allume `C3`, voisin de `EE` |

## Dimensions

- **Longueur** d'un couloir : distance entre ses deux extrémités sur le plan.
- **Capacité** d'un couloir : sa largeur × 1,316 personnes par mètre et par seconde (débit maximal SFPE, voir `sources.md`). Largeurs : 4 m pour l'allée principale, 3 m pour les galeries, 2,4 m pour les portes de sortie et l'entrée de la restauration, 1,8 m pour les autres entrées de magasin, 1,2 m pour le goulot et l'accès aux sanitaires.
- **Capacité** d'un nœud : hypothèse de dimensionnement, de 15 personnes (sanitaires) à 300 (sorties), selon la taille du lieu. À justifier ou ajuster dans le rapport.
