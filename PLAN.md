# PLAN — Modélisation et simulation d'une zone commerciale

Projet de théorie des graphes, 4e année. Sujet : `consignes.pdf`. Binôme, rendu dans 2 à 4 semaines : rapport PDF et soutenance avec démonstration.

Ce document fixe l'architecture, les formats et les décisions de modélisation, chacune avec sa justification. Le découpage du travail est dans `AVANCEMENT.md`.

## 1. Architecture

Trois couches, dépendantes dans un seul sens : moteur ← serveur ← page.

```
zone-commerciale/
├── zc/                  moteur, Python pur : aucune dépendance web ni graphe
│   ├── modele.py        nœuds, arêtes, centres, zone, statuts
│   ├── chargement.py    JSON ↔ modèle, validation
│   ├── navigation.py    graphe orienté de navigation : sens, filtres PMR et blocage, poids
│   ├── chemins.py       Dijkstra, fonctions de coût, itinéraires, distances d'évacuation
│   ├── connexite.py     composantes, points d'articulation, Tarjan, graphe réduit
│   ├── simulation.py    agents, pas de temps, capacités, admission
│   ├── demande.py       arrivées et parcours de visite
│   ├── incendie.py      diffusion, détection, effets, évacuation
│   ├── indicateurs.py   mesures et exports CSV
│   ├── palette.py       taux d'occupation → niveau de couleur
│   └── proprietes.py    graphe des propriétés (partie 4)
├── serveur/             FastAPI : expose le moteur à la page
├── web/                 page : index.html, JS, CSS, vendor/cytoscape.min.js
├── donnees/             centres/*.json, zone.json, scenarios/*.json, parametres.json
├── tests/
└── rapport/             rapport.md, figures générées, construction PDF (pandoc)
```

**Pourquoi un moteur pur.** Les algorithmes doivent être codés à la main et testés unitairement. Isolés de toute interface, ils se testent sans serveur, et le rapport peut produire ses figures en appelant directement le moteur.

**Stack.** Choix issu de la recherche d'antériorité (étape B1).
- **Python ≥ 3.11.** Dépendances d'exécution : `fastapi`, `uvicorn`. Dépendances de test : `pytest`, `httpx` (pour le client de test FastAPI), `networkx`, `ruff`, `mypy`.
- **`networkx` ne sert qu'aux tests**, comme oracle : il vérifie nos propres résultats. Un test garantit que `zc/` ne l'importe jamais.
- **Page.** Cytoscape.js (MIT), copié dans `web/vendor/`, sans npm ni étape de compilation. Ses nœuds composés représentent directement les macro-nœuds. Les agents sont dessinés sur un calque `<canvas>` écrit par nos soins, superposé à Cytoscape.
- **Transport.** C'est la page qui pilote l'horloge : elle demande un pas au serveur toutes les `1000 / vitesse` ms. Pause = plus de demandes ; pas à pas = une demande. Il n'y a pas de WebSocket, et la simulation reste déterministe.
- **Lancement en une commande** : `python -m serveur`, puis on ouvre la page indiquée.

**Écartés.** Dash Cytoscape : plus maintenu depuis 2 ans. sigma.js : son rendu WebGL et sa compilation sont superflus pour 80 nœuds. vis-network : pas de nœuds composés. D3 : trop bas niveau pour le délai. NiceGUI : n'a pas de composant de graphe, il aurait fallu intégrer Cytoscape quand même.

## 2. Formats de données

### 2.1 Centre

On reprend **exactement le format imposé** (section 2.3 de la consigne) : liste `noeuds` et liste `aretes`, avec les champs imposés. L'exemple de la consigne doit se charger puis se réécrire à l'identique.

Champs facultatifs ajoutés, tous justifiés :
- `x`, `y` sur les nœuds : la position sur le plan, pour l'affichage ;
- `nom` sur les nœuds : un libellé lisible ;
- `largeur` sur les arêtes : prévu par la consigne, sert à dériver la capacité à partir d'un débit par mètre sourcé (§ 4.1).

**Ce qui n'entre pas dans le JSON** : les valeurs calculées (taux d'occupation, coût, trafic, fumée des arêtes). Les stocker les ferait diverger de la simulation.

### 2.2 Zone

```json
{
  "centres": [{"id": "A", "fichier": "centres/A.json", "x": 0, "y": 0}],
  "sources": [{"id": "P1", "type": "parking", "x": -300, "y": 0}],
  "connexions": [
    {"source": "P1", "cible": "A:EA", "capacite_max": 8, "longueur": 120.0,
     "statut": "libre", "sens": "bidirectionnel", "pmr": true}
  ]
}
```

- Au chargement, chaque nœud d'un centre est **préfixé par l'identifiant du centre** (`A:S1`) : deux centres peuvent ainsi employer les mêmes noms internes sans collision.
- Une connexion relie une source, ou la **sortie** d'un centre, à une autre source ou une autre sortie. Les sorties servent d'interface entre le graphe intérieur et la zone, comme sur le whiteboard.
- Les attributs exigés par la consigne pour une connexion (capacité, longueur, accessibilité) sont `capacite_max`, `longueur` et `pmr`.
- **Vue macro** : on contracte chaque centre en un seul nœud. Elle sert à l'affichage de la zone et à la discussion du rapport.
- Les **sources** (parkings, stations, quartiers) ont une capacité illimitée. C'est d'elles que partent les visiteurs.

### 2.3 Scénarios et paramètres

- `donnees/parametres.json` : les valeurs physiques, chacune avec sa source (§ 4.1).
- `donnees/scenarios/*.json` : zone à charger, graine aléatoire, rythme d'arrivée par source, part de PMR, critère d'itinéraire et β, départs de feu (nœud et instant), α, θ₁, θ₂, δ, mode de connaissance.
- Trois scénarios de démonstration : **journée normale**, **pic d'affluence**, **incendie qui bloque une sortie**.

## 3. Algorithmes (codés à la main)

| Besoin | Algorithme | Complexité |
|---|---|---|
| Plus court chemin | Dijkstra (tas binaire), coût = `longueur` | O((V+E) log V) |
| Moins encombré | Dijkstra, coût = `longueur × (1 + β·τ_e)` | O((V+E) log V) |
| Accessible PMR | Dijkstra sur le sous-graphe des arêtes `pmr`, coût = longueur | O((V+E) log V) |
| Distances d'évacuation | Un seul Dijkstra multi-sources, lancé depuis toutes les sorties sur le graphe inversé | O((V+E) log V) |
| Connexité | Parcours en largeur | O(V+E) |
| Points d'articulation | Hopcroft–Tarjan (DFS, indices et `low`) | O(V+E) |
| Composantes fortement connexes | Tarjan, puis graphe réduit et tri topologique | O(V+E) |

- **Tous les coûts sont positifs**, condition nécessaire à Dijkstra.
- **Le graphe de navigation est orienté** : une arête `bidirectionnel` donne deux arcs, une arête `unique` un seul.
- **Les arêtes et nœuds bloqués** (statut connu) sont retirés du graphe de navigation.
- **Critère « moins encombré ».** C'est une longueur pénalisée : la foule ralentit, et β règle à quel point. Avec β = 0, on retrouve le plus court chemin.
- **Alternative écartée : le goulot le plus large.** On maximiserait la capacité restante du tronçon le plus chargé. Rejeté parce que ce critère ignore la distance et peut imposer des détours absurdes. Il est cité dans le rapport avec ce motif.
- **Une somme des τ seule est rejetée** : son résultat dépendrait du découpage des couloirs en arêtes, pas du bâtiment.
- **Itinéraire d'une région vers un centre** : depuis la source jusqu'à la sortie d'entrée du centre, sur la vue détaillée. On peut le prolonger jusqu'à un magasin.

## 4. Modèle de simulation

### 4.1 Temps et valeurs physiques

- **Δt = 1 s.** Les capacités d'arête de la consigne sont des débits (personnes par unité de temps) : une arête admet au plus `c_e · Δt` entrées par pas.
- **Valeurs physiques** : vitesse de marche d'une personne valide, vitesse PMR, débit par mètre de largeur de passage, densité maximale. Elles sont **tirées de sources publiées et citées** (réglementation de sécurité incendie des ERP, manuels d'évacuation), recherchées dans la story 2.1. Aucune valeur n'est inventée.

### 4.2 Agents (extension ⋆)

Chaque visiteur est un agent : il a un profil (valide ou PMR), une source d'origine, un centre, une liste de 1 à 3 magasins, un temps de visite aléatoire, et un itinéraire.

**Pourquoi des agents.** La consigne demande de « suivre leurs déplacements » et de calculer des itinéraires par profil. Avec des effectifs agrégés, il faudrait suivre la destination de chaque groupe. Les contraintes du modèle minimal restent respectées à l'identique.

**États d'un agent :**
1. **Dans un nœud**, où il compte dans l'occupation `o_v`.
2. **Sur une arête**, avec sa position (en mètres) depuis l'extrémité de départ.
3. **En attente au bout d'une arête**, parce qu'il a été refusé à l'entrée du nœud suivant.

**Un pas de temps se déroule ainsi :**
1. Les arrivées sont générées aux sources, au rythme fixé par le scénario.
2. Les agents sur une arête avancent de `v · Δt`, où `v` dépend du profil et de la fumée.
3. Les agents arrivés au bout d'une arête demandent à entrer dans le nœud. Ce nœud offre `c_v − o_v` places. Les candidats sont **tirés au sort** avec le générateur du scénario (graine fixée, donc rejouable). Les refusés attendent et réessaient au pas suivant.
4. Les agents qui quittent un nœud prennent l'arête suivante de leur itinéraire, dans la limite de `c_e · Δt` entrées par pas.
5. Les indicateurs sont mis à jour.

**Invariants vérifiés à chaque pas** par les tests : `o_v ≤ c_v` et `φ_e ≤ c_e · Δt`. **Conservation** : agents créés = agents présents + agents repartis + agents sauvés.

**Demande** : arrivée à une source, choix d'un centre puis de 1 à 3 magasins, visite d'une durée aléatoire, retour à la source d'origine. La part de PMR est réglable.

**Routage** : par défaut, le critère « moins encombré ». Un agent PMR n'emprunte que des arêtes `pmr`. L'itinéraire est recalculé quand l'objectif change ou que le graphe de navigation est modifié.

### 4.3 Taux d'occupation et couleurs

- **Taux d'un nœud** : `τ_v = o_v / c_v`.
- **Taux d'une arête** : `τ_e = φ_e / (c_e · Δt)`, la définition de la consigne, où `φ_e` est le nombre d'entrées sur l'arête pendant le pas. La contrainte de débit en découle directement.
- **Limite assumée, à discuter dans le rapport.** Une arête saturée en aval, où plus personne n'entre, paraît peu chargée. La file d'attente au bout de l'arête est donc affichée à part.
- **Palette à 5 niveaux partout**, bornes 0,2 / 0,4 / 0,6 / 0,8. Les seuils imposés de 0,4 et 0,8 tombent sur des bornes : la lecture vert / orange / rouge de la consigne reste possible. Le dégradé répond à la palette « graduelle » de la zone.
- Les couleurs sont choisies à l'étape C (design), avec un contrôle de lisibilité pour les daltoniens.
- **La fumée et le blocage** passent par un autre canal que la couleur (bordure, icône), pour ne jamais être confondus avec l'occupation.

## 5. Incendie

Il est limité à un centre. Un agent qui atteint une sortie est **sauvé** et quitte la simulation.

### 5.1 Diffusion de la fumée

On applique la règle de la consigne :

`f_v(t+1) = min(100, f_v(t) + α Σ_{u ∈ N(v)} (f_u(t) − f_v(t))⁺ + s_v(t))`

- `N(v)` désigne les voisins **non orientés** : la fumée ignore le sens de circulation.
- `s_v > 0` seulement pour les nœuds en feu.
- La règle ne fait qu'augmenter la fumée, qui finit à 100 partout où elle diffuse. Le rapport le signale.
- **Fumée d'une arête** = le maximum de ses deux extrémités : un couloir est aussi dangereux que son bout le plus enfumé. Le format JSON n'a pas besoin d'être étendu.

### 5.2 Détection

On distingue l'**état réel** et le **statut connu** :
- L'**état réel** est le niveau de fumée. C'est lui qui agit sur la vitesse et sur la capacité.
- Le **statut connu** est `enfumé` au-delà de θ₁ et `bloqué` au-delà de θ₂. C'est lui qui sert au calcul des chemins.
- Un nœud **avec capteur** met à jour son statut connu immédiatement.
- Un nœud **sans capteur** le met à jour δ pas après le franchissement du seuil.

### 5.3 Effets (réponses aux questions du rapport)

- **La fumée réduit à la fois la vitesse et la capacité**, en proportion de son niveau. Moins de visibilité veut dire moins de vitesse, donc moins de débit. Les coefficients sont justifiés dans le rapport.
- **Une personne engagée sur une arête qui devient bloquée** continue si elle a dépassé la moitié, et fait demi-tour sinon. Dans les deux cas, elle recalcule ensuite son chemin.
- **La connaissance des occupants** est un paramètre, comparé dans le rapport :
  - **global** : chacun connaît l'état réel de tout le bâtiment ;
  - **local** : chacun connaît les statuts détectés (capteurs et retard δ) et la fumée réelle de son nœud et de ses voisins.

### 5.4 Évacuation

- **Déclenchement** : à la première détection, tous les agents du centre passent en évacuation.
- **Cible** : la sortie la plus proche, obtenue par le Dijkstra multi-sources (§ 3).
- **Recalcul** à chaque mise à jour du graphe de navigation.
- **Agent piégé** : un agent qui n'a plus aucun chemin vers une sortie (distance infinie).
- **Centre fermé** (décidé à la story 6.5) : à l'alarme, le centre en feu ne reçoit plus personne. Ses nœuds, sauf ses sorties, sont retirés des trajets des visiteurs : qui allait y entrer fait demi-tour à la porte et rentre à sa source, qui ne faisait que le traverser le contourne. Sauvés, piégés, courbe et charge des sorties ne portent donc que sur les présents à l'alarme : sauvés + piégés = présents.

**Indicateurs :**
- temps d'évacuation total, et courbe des personnes encore à l'intérieur ;
- nombre de personnes piégées ;
- charge de chaque sortie ;
- hors incendie : occupation moyenne et maximale, temps de trajet moyen, goulots récurrents.

Tous s'exportent en CSV pour le rapport.

## 6. Plan du bâtiment

**Le centre détaillé est de plain-pied.** Il n'y a donc pas d'ascenseur, et les arêtes non PMR viennent de marches ou de passages étroits. Le plan est proposé, puis redessiné et ajusté par le binôme.

Il doit contenir, et un test le vérifie :
- au moins 2 sorties, situées sur deux côtés opposés ;
- au moins 6 magasins et 1 sanitaire ;
- au moins un cycle, pour qu'il existe des chemins alternatifs ;
- au moins un goulot : un couloir de faible capacité sur un passage fréquenté ;
- au moins une arête non PMR, contournable par un chemin PMR plus long ;
- au moins une arête à sens unique ;
- au moins 2 nœuds sans capteur, dont un sur un chemin d'évacuation ;
- un départ de feu possible près d'une sortie, pour le scénario de démonstration.

Les deux centres simples se limitent à 4 à 6 nœuds et 2 sorties chacun. La zone comporte 3 centres et au moins 3 sources : parking, station, quartier.

## 7. Graphe des propriétés (partie 4)

`proprietaires.json` **n'est pas encore fourni** : il faut le demander à l'enseignant. Son contenu décide de la définition de « majoritaire » ; avec des parts en pourcentage, ce serait strictement plus de 50 %. En attendant, cette partie est planifiée en dernier.

Ce qui est prévu :
- **Connexité de G_P** par parcours en largeur, avec ses composantes.
- **Preuve que les centres d'un même propriétaire forment une clique**, d'où la borne `|E_P| ≤ Σ_p C(k_p, 2)`.
- **Points d'articulation** (Hopcroft–Tarjan), à deux niveaux :
  - les centres articulation de G_P ;
  - les propriétaires articulation, dans le graphe biparti propriétaires–centres. La disparition d'un propriétaire retire une clique d'arêtes et non un sommet de G_P : c'est pourquoi il faut ce second graphe.
- **G⃗_P**, sans les arcs d'un centre vers lui-même, puis ses composantes fortement connexes (Tarjan) et son graphe réduit.
  - Le graphe réduit est toujours acyclique : la réponse découle d'un théorème. L'analyse porte donc sur sa structure : sources, puits, chaînes de contrôle (plus long chemin dans l'ordre topologique).

## 8. Priorités en cas de retard

On sacrifie dans cet ordre :
1. la comparaison des modes global et local ;
2. le feu déclenché au clic ;
3. les agents, remplacés par des effectifs, ce qui reste le modèle minimal imposé.

Le socle commun de la consigne passe toujours en premier.

## 9. Rapport

Il est rédigé en Markdown dans `rapport/`, converti en PDF par pandoc. Figures et tableaux sont générés par des scripts qui appellent le moteur.

Il contient :
- la justification de chaque choix ;
- les fonctions de coût et les complexités ;
- les preuves (clique, borne) ;
- les sources des valeurs physiques ;
- les réponses aux trois questions de l'incendie, appuyées sur des résultats chiffrés ;
- les résultats de la partie 4.
