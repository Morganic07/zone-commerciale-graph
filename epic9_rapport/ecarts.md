# Écarts à la consigne et parties écartées

Notes à reprendre dans le rapport (story 9.2), au fil des décisions. Chaque écart garde sa date et son motif.

## Itinéraire d'une région vers une station : pas de choix automatique du sas d'entrée

*Décision du 2026-11-24 (story 4.3 écartée).*

**Consigne (section 1, question 2).** « Trouver un itinéraire optimal d'une région vers un centre commercial », pour trois critères : le plus court, le moins encombré, accessible PMR, avec pour chacun la fonction de coût et la complexité.

**Ce qui est fait.** Dans notre transposition, une région est un sas (les visiteurs s'amarrent à une station par ses sas), et un centre commercial est une station, dans laquelle on entre par l'un de ses sas. L'itinéraire d'une région vers une station est donc un itinéraire d'un sas vers un sas de la station visée. Les trois fonctions de `epic4_algorithmes/moteur/chemins.py` (`plus_court_chemin`, `chemin_le_moins_encombre`, `chemin_pmr`) le calculent par l'algorithme de Dijkstra, avec leur fonction de coût et leur complexité, et la visionneuse le trace.

**Ce qui est écarté, et pourquoi.** Nous avions prévu de choisir automatiquement le meilleur sas d'entrée de la station visée, et de prolonger l'itinéraire jusqu'à un module. Nous y renonçons :
- la destination d'un visiteur est un lieu précis, un sas ou un module, et non une station abstraite : c'est ce lieu qu'on donne comme arrivée ;
- le prolongement jusqu'à un module n'est pas demandé par la consigne ;
- les trois critères, leurs fonctions de coût et leur complexité restent traités en entier.
