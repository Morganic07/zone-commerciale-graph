# Sources des valeurs physiques

Les valeurs du modèle sont dans `donnees/parametres.json`, que le chargement refuse si une valeur n'a pas sa source et son année. Ce document justifie chaque choix.

| Paramètre | Valeur | Source |
|---|---|---|
| `vitesse_marche` | 1,34 m/s | Weidmann (1993) |
| `vitesse_pmr` | 0,69 m/s | Boyce, Shields et Silcock (1999) |
| `debit_specifique_max` | 1,316 pers/(m·s) | Méthode SFPE, via Thunderhead Engineering (2024) |
| `densite_max` | 5,4 pers/m² | Weidmann (1993) |

## Justifications

**`vitesse_marche` — 1,34 m/s.** Vitesse libre moyenne des piétons dans la revue de littérature de Weidmann, où les vitesses observées vont de 0,97 à 1,65 m/s. C'est la valeur de référence des modèles de flux piétons. Boyce et al. (1999) mesurent 1,25 m/s chez les personnes non handicapées de leur échantillon : l'écart reste dans la plage de Weidmann.

**`vitesse_pmr` — 0,69 m/s.** Vitesse moyenne sur plan horizontal des utilisateurs de fauteuil roulant manuel **sans assistance**, mesurée sur un couloir de 50 m. Parmi les profils de Boyce et al., c'est le plus contraignant pour la circulation en fauteuil : un fauteuil électrique va à 0,89 m/s, un fauteuil manuel poussé par un accompagnant à 1,30 m/s. Seul le déambulateur est plus lent (0,57 m/s), mais il ne correspond pas au profil « fauteuil » que la consigne associe aux arêtes `pmr`. Le tableau de ces valeurs est reproduit à l'identique dans Lee (2018), tableau 2.1.

**`debit_specifique_max` — 1,316 pers/(m·s).** Débit maximal par mètre de largeur utile d'une porte selon la méthode SFPE, telle qu'appliquée et vérifiée par le logiciel d'évacuation Pathfinder. Il sert à dériver la capacité `capacite_max` d'une arête à partir de sa `largeur`, comme la consigne le suggère. Limite connue : Gwynne et al. (2009) montrent que le rapport linéaire entre largeur et débit est une simplification, plutôt optimiste.

**`densite_max` — 5,4 pers/m².** Densité de blocage de Weidmann, au-delà de laquelle la foule ne progresse plus. Elle borne l'occupation physiquement possible d'un nœud ou d'une arête.

## Références

- U. Weidmann, *Transporttechnik der Fussgänger*, Schriftenreihe des IVT, ETH Zürich, 1993. https://research-collection.ethz.ch/handle/20.500.11850/242008
- K. E. Boyce, T. J. Shields, G. W. H. Silcock, « Toward the Characterization of Building Occupancies for Fire Safety Engineering: Capabilities of Disabled People Moving Horizontally and on an Incline », *Fire Technology* 35(1), 51–67, 1999. doi:10.1023/A:1015339216366
- S. Y. Lee, *Verification and Validation of buildingEXODUS based on the Walking Speed of People with Disabilities (PWD)*, Universiti Sains Malaysia, 2018, tableau 2.1. http://eprints.usm.my/52910/
- Thunderhead Engineering, *Pathfinder Verification and Validation*, 2024. https://www.thunderheadeng.com/docs/2024-1/pathfinder/verification-validation/
- S. M. V. Gwynne, J. Kratchman, E. D. Kuligowski, J. A. Milke, « Questioning the linear relationship between doorway width and achievable flow rate », *Fire Safety Journal* 44(1), 80–87, 2009. https://www.nist.gov/node/633016
