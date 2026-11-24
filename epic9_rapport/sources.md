# Sources des valeurs physiques

Les valeurs sont dans `donnees/parametres.json`. Chacune cite une source datée, ou bien
est marquée « hypothèse » avec son raisonnement ; le programme refuse de charger une
valeur qui n'a ni l'un ni l'autre.

Hypothèse de modélisation : les stations ont une gravité artificielle. Les occupants se
déplacent donc comme sur Terre, et les valeurs viennent des études de foule et de
mobilité au sol. Une personne à mobilité réduite est une personne en fauteuil roulant.

## Valeurs sourcées

| Paramètre | Valeur | Source |
|---|---|---|
| Vitesse d'une personne valide | 1,34 m/s | Weidmann (1993) |
| Vitesse d'une personne en fauteuil roulant | 0,67 m/s | Huang et al. (2025) |
| Débit maximal par mètre de largeur | 1,37 personne/(m·s) | Green Guide, 5e édition (2008) |
| Surface minimale par personne | 0,25 m² | Green Guide, 5e édition (2008) |

### Vitesse d'une personne valide : 1,34 m/s

U. Weidmann, *Transporttechnik der Fussgänger*, Institut für Verkehrsplanung, ETH Zürich,
Schriftenreihe Nr. 90, 1993.
<https://research-collection.ethz.ch/handle/20.500.11850/242008>

Vitesse moyenne de marche libre, compilée à partir de nombreuses études ; écart-type
d'environ 0,26 m/s.

### Vitesse d'une personne en fauteuil roulant : 0,67 m/s

Y. Huang, C. Shi, S. Dong, S. Zhang, L. Xu, G. Nian, « Measuring spatial accessibility
for wheelchair users: A case study in a Chinese campus », *PLoS One* 20(12), e0335663,
2025. <https://doi.org/10.1371/journal.pone.0335663>

Vitesse moyenne mesurée sur 30 participants en fauteuil roulant manuel, sans aide, sur
un chemin plat. Les fauteuils électriques n'étaient pas étudiés.

### Débit maximal par mètre de largeur : 1,37 personne/(m·s)

*Guide to Safety at Sports Grounds* (« Green Guide »), 5e édition, Department for
Culture, Media and Sport, Royaume-Uni, 2008.

82 personnes par mètre de largeur et par minute sur un passage plat, soit
82 / 60 ≈ 1,37 personne par mètre et par seconde.

### Surface minimale par personne : 0,25 m²

Même source. 4 personnes par mètre carré est la densité maximale retenue pour une foule
en mouvement, soit 1 / 4 = 0,25 m² par personne. C'est un plafond de sécurité : un module
rempli à cette densité est bondé.

**À vérifier dans l'original** : les deux valeurs du Green Guide ont été relevées dans la
thèse de G. K. Still, qui le cite (<https://gkstill.com/CV/PhD/Chapter3.html>), et non
dans le guide lui-même.

## Hypothèses

Aucune pour l'instant.
