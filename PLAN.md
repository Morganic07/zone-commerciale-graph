# PLAN — Modélisation et simulation d'un réseau de stations spatiales

Projet de théorie des graphes, 4e année. Sujet : `consignes.pdf`. Travail de groupe, rendu dans 2 à 4 semaines : rapport PDF et soutenance avec démonstration.

Ce document fixe l'architecture, les formats et les décisions de modélisation, chacune avec sa justification. Le découpage du travail est dans `AVANCEMENT.md`.

## 0. Transposition du sujet

La consigne porte sur une zone commerciale. Le groupe la transpose à un réseau de trois stations spatiales habitées, du type de l'ISS, avec l'accord de l'enseignante. La consigne le permet : les choix doivent « rester cohérents avec le socle commun et être clairement justifiés ».

**Principe : on change l'habillage, pas la structure.** Chaque élément imposé par la consigne garde un équivalent, et le rapport donne cette correspondance en toutes lettres.

| Consigne | Transposition |
|---|---|
| Zone commerciale | Réseau de trois stations en orbite |
| Centre commercial (macro-nœud) | Station |
| Zone de connexion entre centres | Tunnel de transfert pressurisé entre deux stations |
| Nœud source (quartier, parking, station de transport) | Les deux sas de chaque station : les visiteurs y arrivent en s'amarrant (décision du 2026-11-20) |
| Magasin | Module (type `module` dans les fichiers) : laboratoire, serre, observatoire, quartiers d'équipage, salon |
| Sanitaire | Module d'hygiène |
| Couloir-carrefour | Nœud de jonction (sur l'ISS, le module Unity) |
| Sortie | Sas, à la fois entrée et sortie de la station |
| Couloir, passage | Passage entre deux modules, à travers une écoutille |
| Visiteurs | Équipage, scientifiques et touristes spatiaux |
| Personne à mobilité réduite | Personne transportée sur civière (§ 4.2) |
| Propriétaires | Agences spatiales et opérateurs privés (§ 7) |

**Pourquoi des tunnels et pas des navettes entre les stations.** Une navette transporte des groupes à heures fixes : elle casserait le modèle de flux continu de la consigne (capacité par unité de temps, longueur). Un tunnel pressurisé se modélise exactement comme une zone de connexion. C'est la part fantaisiste du sujet, assumée dans le rapport.

## 1. Architecture

Trois couches, dépendantes dans un seul sens : moteur ← serveur ← page.

**Rangement par epic** (décision du 2026-11-24). Un dossier par epic, au nom importable en Python (`epic2_donnees`). Dans chaque epic, les couches gardent leurs sous-dossiers (`moteur/`, `serveur/`, `web/`, `donnees/`, `tests/`). Les fichiers qui grossissent d'epic en epic, comme `modele.py`, le serveur ou la page, restent dans l'epic où ils sont nés.

```
graph-satellites/
├── epic2_donnees/             (l'epic 1, le socle, n'a plus de dossier depuis le 2026-11-24)
│   ├── moteur/                Python pur : aucune dépendance web ni graphe
│   │   ├── modele.py          nœuds, arêtes, stations, réseau, statuts
│   │   └── chargement.py      JSON ↔ modèle (sans validation, décision du 2026-11-20)
│   ├── donnees/               stations/*.json, reseau.json, parametres.json
│   └── tests/
├── epic3_visionneuse/
│   ├── serveur/               FastAPI : expose le moteur à la page
│   ├── web/                   page : index.html, JS, CSS, vendor/cytoscape.min.js
│   └── tests/
├── epic4_algorithmes/
│   ├── moteur/
│   │   ├── navigation.py      graphe orienté de navigation : sens, filtres PMR et blocage, poids
│   │   ├── chemins.py         Dijkstra, une fonction par critère, distances d'évacuation
│   │   └── connexite.py       composantes, points d'articulation, Tarjan, graphe réduit
│   └── tests/
├── epic5_simulation/
│   ├── moteur/                simulation.py (agents, pas de temps, capacités, admission),
│   │                          demande.py, indicateurs.py (mesures, exports CSV), palette.py
│   └── donnees/               simulation.json
├── epic6_incendie/moteur/     incendie.py : diffusion, détection, effets, évacuation
├── epic7_interface/
├── epic8_proprietes/          moteur/proprietes.py (partie 4), donnees/proprietaires.json
└── epic9_rapport/             rapport.md, sources.md, figures générées, construction PDF (pandoc)
```

**Pourquoi un moteur pur.** Les algorithmes doivent être codés à la main et testés unitairement. Isolés de toute interface, ils se testent sans serveur, et le rapport peut produire ses figures en appelant directement le moteur.

**Stack.** Choix issu de la recherche d'antériorité.
- **Python ≥ 3.11.** Dépendances d'exécution : `fastapi`, `uvicorn`. Dépendances de test : `pytest`, `httpx` (pour le client de test FastAPI), `networkx`, `ruff`. `mypy` a été retiré le 2026-11-24, avec les annotations de type, jugées illisibles pour un débutant (décision de l'utilisateur).
- **`networkx` ne sert qu'aux tests**, comme oracle : il vérifie nos propres résultats. Un test garantit qu'aucun dossier `epic*/moteur/` ne l'importe.
- **Page.** Cytoscape.js (MIT), copié dans `epic3_visionneuse/web/vendor/`, sans npm ni étape de compilation. Ses nœuds composés représentent directement les macro-nœuds. Les agents sont dessinés sur un calque `<canvas>` écrit par nos soins, superposé à Cytoscape.
- **Transport.** C'est la page qui pilote l'horloge : elle demande un pas au serveur toutes les `1000 / vitesse` ms. Pause = plus de demandes ; pas à pas = une demande. Il n'y a pas de WebSocket, et la simulation reste déterministe.
- **Lancement en une commande** : `python -m serveur` depuis la racine du projet (fichier `serveur.py`, décision de l'utilisateur, 2026-11-24 ; avant : `python -m epic3_visionneuse.serveur`), puis on ouvre la page indiquée.

**Une interface qui grandit avec le moteur** (décision du 2026-11-20). Plutôt qu'une interface faite d'un bloc à la fin, une visionneuse est livrée juste après les données : elle affiche le réseau et les plans des stations, et se recharge après chaque modification d'un fichier JSON. Chaque epic suivant ajoute ensuite ce qu'il faut pour voir son travail : itinéraires et articulations, puis simulation, puis incendie. Pourquoi : un plan mal saisi ou un algorithme faux se repère bien plus vite à l'œil que dans un test. Le moteur reste pur : seuls `epic3_visionneuse/serveur/` et `epic3_visionneuse/web/` grandissent.

**Design super simple** (même décision) : une page claire et sobre, sans recherche graphique. L'ancien design system de l'autre projet n'est pas repris.

**Écartés.** Dash Cytoscape : plus maintenu depuis 2 ans. sigma.js : son rendu WebGL et sa compilation sont superflus pour 80 nœuds. vis-network : pas de nœuds composés. D3 : trop bas niveau pour le délai. NiceGUI : n'a pas de composant de graphe, il aurait fallu intégrer Cytoscape quand même.

## 2. Formats de données

### 2.1 Station

On reprend **exactement le format imposé** (section 2.3 de la consigne) : liste `noeuds` et liste `aretes`, avec les champs imposés. L'exemple de la consigne doit se charger. (La réécriture à l'identique a été abandonnée le 2026-11-24 : le programme ne réécrit jamais de fichier.)

**Valeurs de `type` : un seul écart à la consigne** (décision du 2026-11-20). `type` vaut `module`, `sanitaire`, `carrefour` ou `sortie` : la valeur `module` remplace le `magasin` de la consigne, plus réaliste dans une station spatiale. Les trois autres valeurs sont celles de la consigne. Le programme ne valide pas les valeurs : un fichier au format de la consigne (avec `magasin`) se charge toujours, mais ses magasins ne seront pas reconnus comme des modules à visiter. **Écart à justifier dans le rapport** (story 9.2).

Champs facultatifs ajoutés, tous justifiés :
- `x`, `y` sur les nœuds : la position sur le plan, pour l'affichage ;
- `nom` sur les nœuds : retiré du programme (décision du 2026-11-24, code simplifié) ; un nœud se désigne par son identifiant (`A4`) ;
- `largeur` sur les arêtes : prévu par la consigne comme facultatif, mais ni lu ni écrit par le programme (décision du 2026-11-24, code simplifié) : un fichier qui le contient se charge, le champ est ignoré. La capacité `capacite_max` est donnée directement. Elle a été calculée comme largeur × débit par mètre (§ 4.1), avec 1,2 m pour un sas, 1 m pour un passage ordinaire, 0,8 m pour un goulot et 0,6 m pour un passage non PMR ; le rapport garde ce calcul.

**Ce qui n'entre pas dans le JSON** : les valeurs calculées (taux d'occupation, coût, trafic, fumée des arêtes). Les stocker les ferait diverger de la simulation.

### 2.2 Réseau

```json
{
  "stations": [{"id": "A", "fichier": "stations/A.json", "x": 0, "y": 0}],
  "sources": [],
  "connexions": [
    {"source": "A:SAS2", "cible": "B:SAS1", "capacite_max": 1.64, "longueur": 350.0,
     "statut": "libre", "sens": "bidirectionnel", "pmr": true}
  ]
}
```

- Ce fichier n'est pas imposé par la consigne : ses noms suivent le sujet transposé.
- Au chargement, chaque nœud d'une station est **préfixé par l'identifiant de la station** (`A:LAB1`) : deux stations peuvent ainsi employer les mêmes noms internes sans collision.
- Une connexion (un tunnel) relie le **sas** d'une station au sas d'une autre. Les sas servent d'interface entre le graphe intérieur et le réseau.
- Les attributs exigés par la consigne pour une connexion (capacité, longueur, accessibilité) sont `capacite_max`, `longueur` et `pmr`.
- **Vue macro** : on contracte chaque station en un seul nœud. Elle sert à l'affichage du réseau, où Cytoscape regroupe les nœuds d'une station dans une boîte, et à la discussion du rapport. Aucune fonction du moteur ne la calcule (retirée le 2026-11-24, faute d'usage hors des tests).
- **Les nœuds sources sont les sas** (décision du 2026-11-20) : chaque station a deux sas, par lesquels les visiteurs arrivent de l'extérieur en s'amarrant, et par lesquels ils repartent. La liste `sources` reste dans le format, vide : le réseau n'a pas de point d'arrivée à part.
- **Toutes les arêtes sont bidirectionnelles** dans nos plans (même décision). Le champ `sens` reste dans le format imposé. Le graphe de navigation et les itinéraires savent traiter une arête `unique`, mais pas les distances d'évacuation : elles comptent sur des arêtes bidirectionnelles pour se passer du graphe inversé (décision de l'utilisateur, 2026-11-24). Un plan avec une arête `unique` fausserait l'évacuation.

### 2.3 Réglages de la simulation et paramètres

- `epic2_donnees/donnees/parametres.json` : les valeurs physiques, chacune avec sa source ou sa justification (§ 4.1).
- `epic5_simulation/donnees/simulation.json` : réglages de départ (graine aléatoire, rythme d'arrivée par source, part de PMR, durée des visites, β).
- La page démarre une simulation unique, dont l'affluence se règle au curseur (visiteurs par minute pour tout le réseau, répartis entre les sas dans les proportions de départ). Le feu se déclenche au clic, avec α, θ₁, θ₂, δ et le mode de connaissance réglés dans le panneau.

## 3. Algorithmes (codés à la main)

| Besoin | Algorithme | Complexité |
|---|---|---|
| Plus court chemin | Dijkstra (recherche du plus proche dans une liste), coût = `longueur` | O(V² + E) |
| Moins encombré | Dijkstra, coût = `longueur × (1 + β·τ_e)` | O(V² + E) |
| Accessible PMR | Dijkstra sur le sous-graphe des arêtes `pmr`, coût = longueur | O(V² + E) |
| Distances d'évacuation | Un seul Dijkstra multi-sources, lancé depuis toutes les sorties (graphe non inversé : toutes les arêtes sont bidirectionnelles) | O(V² + E) |
| Connexité | Parcours en largeur | O(V+E) |
| Points d'articulation | Hopcroft–Tarjan (DFS, indices et `low`) | O(V+E) |
| Composantes fortement connexes | Tarjan, puis graphe réduit et tri topologique | O(V+E) |

- **Tous les coûts sont positifs**, condition nécessaire à Dijkstra.
- **Dijkstra sans tas** (décision du 2026-11-24, code simplifié) : à chaque tour, on cherche le nœud le plus proche en parcourant la liste des nœuds à traiter. C'est O(V² + E) au lieu de O((V+E) log V) avec un tas binaire, mais le réseau ne compte que quelques dizaines de nœuds, et le code se lit sans connaître le module `heapq`. Le rapport le justifie.
- **Le graphe de navigation est orienté** : une arête `bidirectionnel` donne deux arcs, une arête `unique` un seul.
- **Les arêtes et nœuds bloqués** (statut connu) sont retirés du graphe de navigation.
- **Critère « moins encombré ».** C'est une longueur pénalisée : la foule ralentit, et β règle à quel point. Avec β = 0, on retrouve le plus court chemin.
- **Alternative écartée : le goulot le plus large.** On maximiserait la capacité restante du tronçon le plus chargé. Rejeté parce que ce critère ignore la distance et peut imposer des détours absurdes. Il est cité dans le rapport avec ce motif.
- **Une somme des τ seule est rejetée** : son résultat dépendrait du découpage des passages en arêtes, pas de la station.
- **Itinéraire d'une région vers une station** (question 2 de la consigne) : une région est un sas, et on entre dans une station par l'un de ses sas. L'itinéraire est donc calculé de nœud à nœud, du sas de départ au sas d'arrivée choisi, par les trois fonctions de `chemins.py`. Le choix automatique du meilleur sas d'entrée, prévu par la story 4.3, est écarté le 2026-11-24 (décision de l'utilisateur) : la destination d'un visiteur est un lieu précis, pas une station abstraite. Motif complet dans `AVANCEMENT.md` (4.3) et `epic9_rapport/ecarts.md`.

## 4. Modèle de simulation

### 4.1 Temps et valeurs physiques

- **Δt = 1 s.** Les capacités d'arête de la consigne sont des débits (personnes par unité de temps) : une arête admet au plus `c_e · Δt` entrées par pas.
- **Valeurs physiques**, toutes propres à l'apesanteur : la marche et les débits de foule au sol ne s'appliquent pas.
  - vitesse de déplacement d'une personne valide, qui se tire le long des mains courantes ;
  - vitesse d'une personne transportée sur civière ;
  - débit de passage par mètre de largeur d'écoutille ;
  - volume habitable par personne, d'où la capacité des modules.
- **Où les chercher** (story 2.1) : documentation de la NASA sur la conception des habitats spatiaux et les dimensions des écoutilles et passages de l'ISS, publications de l'ESA, retours d'expérience des équipages.
- **Règle** : chaque valeur cite sa source. Quand aucune source publiée n'existe (le débit à travers une écoutille, probablement), la valeur est marquée **hypothèse** dans `parametres.json`, avec son raisonnement (un ordre de grandeur tiré d'une valeur sourcée). Le rapport liste ces hypothèses à part. Aucune valeur n'est donnée sans l'une ou l'autre.

### 4.2 Agents (extension ⋆)

Chaque visiteur est un agent : il a un profil (valide ou PMR), un sas d'arrivée, une station, une liste de 1 à 3 modules, un temps de visite aléatoire, et un itinéraire.

**Pourquoi des agents.** La consigne demande de « suivre leurs déplacements » et de calculer des itinéraires par profil. Avec des effectifs agrégés, il faudrait suivre la destination de chaque groupe. Les contraintes du modèle minimal restent respectées à l'identique.

**Accessibilité en apesanteur** (définition validée par l'enseignante). Il n'y a ni escalier ni fauteuil roulant dans une station. Le profil « à mobilité réduite » désigne une personne qui ne se déplace pas seule : un blessé ou un malade transporté sur civière. Une arête est `pmr: false` quand une civière n'y passe pas : écoutille trop étroite, passage coudé, ou passage encombré d'équipements. Un tel passage reste praticable par une personne valide.

**États d'un agent :**
1. **Dans un nœud**, où il compte dans l'occupation `o_v`.
2. **Sur une arête**, avec sa position (en mètres) depuis l'extrémité de départ.
3. **En attente au bout d'une arête**, parce qu'il a été refusé à l'entrée du nœud suivant.

**Un pas de temps se déroule ainsi :**
1. Les arrivées sont générées aux sas, au rythme fixé par l'affluence réglée.
2. Les agents sur une arête avancent de `v · Δt`, où `v` dépend du profil et de la fumée.
3. Les agents arrivés au bout d'une arête demandent à entrer dans le nœud. Ce nœud offre `c_v − o_v` places. Les candidats sont **tirés au sort** avec le générateur de la simulation (graine fixée, donc rejouable). Les refusés attendent et réessaient au pas suivant.
4. Les agents qui quittent un nœud prennent l'arête suivante de leur itinéraire, dans la limite de `c_e · Δt` entrées par pas.
5. Les indicateurs sont mis à jour.

**Invariants vérifiés à chaque pas** par les tests : `o_v ≤ c_v` et `φ_e ≤ c_e · Δt`. **Conservation** : agents créés = agents présents + agents repartis + agents sauvés.

**Demande** : arrivée à un sas, choix d'une station puis de 1 à 3 modules, visite d'une durée aléatoire, départ par un sas. La part de PMR est réglable.

**Routage** : par défaut, le critère « moins encombré ». Un agent PMR n'emprunte que des arêtes `pmr`. L'itinéraire est recalculé quand l'objectif change ou que le graphe de navigation est modifié.

### 4.3 Taux d'occupation et couleurs

- **Taux d'un nœud** : `τ_v = o_v / c_v`.
- **Taux d'une arête** : `τ_e = φ_e / (c_e · Δt)`, la définition de la consigne, où `φ_e` est le nombre d'entrées sur l'arête pendant le pas. La contrainte de débit en découle directement.
- **Limite assumée, à discuter dans le rapport.** Une arête saturée en aval, où plus personne n'entre, paraît peu chargée. La file d'attente au bout de l'arête est donc affichée à part.
- **Palette à 5 niveaux partout**, bornes 0,2 / 0,4 / 0,6 / 0,8. Les seuils imposés de 0,4 et 0,8 tombent sur des bornes : la lecture vert / orange / rouge de la consigne reste possible. Le dégradé répond à la palette « graduelle » demandée pour les connexions.
- Les couleurs sont choisies avec la story d'affichage de la simulation (5.6), avec un contrôle de lisibilité pour les daltoniens.
- **La fumée et le blocage** passent par un autre canal que la couleur (bordure, icône), pour ne jamais être confondus avec l'occupation.

## 5. Incendie

Il est limité à une station. Un agent qui atteint un sas est **sauvé** et quitte la simulation : il a quitté la station en feu, vers un tunnel ou un vaisseau amarré. C'est la procédure réelle de l'ISS, où l'équipage se regroupe dans les vaisseaux amarrés. Le rapport peut citer l'incendie de la station Mir en 1997.

### 5.1 Diffusion de la fumée

On applique la règle de la consigne :

`f_v(t+1) = min(100, f_v(t) + α Σ_{u ∈ N(v)} (f_u(t) − f_v(t))⁺ + s_v(t))`

- `N(v)` désigne les voisins **non orientés** : la fumée ignore le sens de circulation.
- `s_v > 0` seulement pour les nœuds en feu.
- La règle ne fait qu'augmenter la fumée, qui finit à 100 partout où elle diffuse. Le rapport le signale.
- **Fumée d'une arête** = le maximum de ses deux extrémités : un passage est aussi dangereux que son bout le plus enfumé. Le format JSON n'a pas besoin d'être étendu.
- **Limite à discuter dans le rapport** : en apesanteur, il n'y a pas de convection et la fumée suit la ventilation. La règle de la consigne, symétrique, ne le représente pas. Une diffusion orientée selon la ventilation est une extension possible, non prévue.

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
  - **global** : chacun connaît l'état réel de toute la station ;
  - **local** : chacun connaît les statuts détectés (capteurs et retard δ) et la fumée réelle de son nœud et de ses voisins.

### 5.4 Évacuation

- **Déclenchement** : à la première détection, tous les agents de la station passent en évacuation.
- **Cible** : la sortie la plus proche, obtenue par le Dijkstra multi-sources (§ 3).
- **Recalcul** à chaque mise à jour du graphe de navigation.
- **Agent piégé** : un agent qui n'a plus aucun chemin vers une sortie (distance infinie).
- **Station fermée** : à l'alarme, la station en feu ne reçoit plus personne. Ses nœuds, sauf ses sorties, sont retirés des trajets des visiteurs : qui allait y entrer fait demi-tour au sas et repart, qui ne faisait que la traverser la contourne. Sauvés, piégés, courbe et charge des sorties ne portent donc que sur les présents à l'alarme : sauvés + piégés = présents.

**Indicateurs :**
- temps d'évacuation total, et courbe des personnes encore à bord ;
- nombre de personnes piégées ;
- charge de chaque sortie ;
- hors incendie : occupation moyenne et maximale, temps de trajet moyen, goulots récurrents.

Tous s'exportent en CSV pour le rapport.

## 6. Plan des stations

**Le plan de la station détaillée A est dessiné par le groupe** (consigne § 5). Une station est en trois dimensions, mais son plan est dessiné à plat (positions `x`, `y`) : seules comptent les liaisons entre modules, pas leur disposition dans l'espace. Les arêtes non PMR viennent d'écoutilles étroites ou de passages encombrés (§ 4.2).

Le plan de A doit contenir, et un test le vérifie :
- au moins 2 sas (sorties, qui sont aussi les points d'arrivée), situés aux deux extrémités de la station ;
- au moins 6 modules (type `module`) et 1 module d'hygiène (type `sanitaire`) ;
- au moins un cycle, pour qu'il existe des chemins alternatifs ;
- au moins un goulot : une écoutille étroite sur un passage fréquenté ;
- au moins une arête non PMR, contournable par un chemin PMR plus long ;
- au moins 2 nœuds sans capteur, dont un sur un chemin d'évacuation ;
- un départ de feu possible près d'une sortie, pour la démonstration.

Toutes les arêtes sont bidirectionnelles, et il n'y a pas de capsule de sauvetage (décision du 2026-11-20).

Les deux stations simples, B et C, comptent au moins 12 nœuds et 2 sas chacune. Chacune des trois stations a au moins 2 passages non PMR, tous contournables : le réseau entier reste accessible en fauteuil (décision du 2026-11-20). Le réseau comporte 3 stations, reliées par des tunnels entre leurs sas ; les sas sont les nœuds sources.

## 7. Graphe des propriétés (partie 4)

**`proprietaires.json` est écrit par le groupe**, à la demande de l'enseignante.

**Problème : avec 3 stations, G_P n'a que 3 sommets.** Connexité, cliques et articulations y deviennent triviales, et la partie 4 ne démontrerait rien. Décision : le fichier décrit une **flotte plus large**, d'une douzaine de stations en orbite, dont les 3 simulées. La partie 4 est une analyse du réseau de propriété, indépendante de la simulation : elle n'a pas besoin des plans des autres stations.

**Contenu du fichier :**
- les propriétaires : agences spatiales (NASA, ESA, Roscosmos, JAXA, CSA…) et opérateurs privés ;
- les stations ;
- les parts de chaque propriétaire dans chaque station, en pourcentage, dont la somme vaut 100 par station.

« Majoritaire » veut alors dire strictement plus de 50 %.

**Le jeu de données est construit pour que chaque question ait une réponse intéressante**, et le rapport le dit :
- au moins deux composantes connexes, ou une seule composante justifiée ;
- au moins une station articulation, et un propriétaire articulation ;
- dans G⃗_P, au moins un cycle de contrôle (donc une composante fortement connexe de plus d'un sommet) et une chaîne de contrôle de longueur au moins 3.

Ce qui est prévu :
- **Connexité de G_P** par parcours en largeur, avec ses composantes.
- **Preuve que les stations d'un même propriétaire forment une clique**, d'où la borne `|E_P| ≤ Σ_p C(k_p, 2)`.
- **Points d'articulation** (Hopcroft–Tarjan), à deux niveaux :
  - les stations articulation de G_P ;
  - les propriétaires articulation, dans le graphe biparti propriétaires–stations. La disparition d'un propriétaire retire une clique d'arêtes et non un sommet de G_P : c'est pourquoi il faut ce second graphe.
- **G⃗_P**, sans les arcs d'une station vers elle-même, puis ses composantes fortement connexes (Tarjan) et son graphe réduit.
  - Le graphe réduit est toujours acyclique : la réponse découle d'un théorème. L'analyse porte donc sur sa structure : sources, puits, chaînes de contrôle (plus long chemin dans l'ordre topologique).

## 8. Priorités en cas de retard

On sacrifie dans cet ordre :
1. la comparaison des modes global et local ;
2. le feu déclenché au clic ;
3. les agents, remplacés par des effectifs, ce qui reste le modèle minimal imposé.

Le socle commun de la consigne passe toujours en premier.

## 9. Rapport

Il est rédigé en Markdown dans `epic9_rapport/`, converti en PDF par pandoc. Figures et tableaux sont générés par des scripts qui appellent le moteur.

Il contient :
- la transposition du sujet et sa table de correspondance (§ 0) ;
- la justification de chaque choix ;
- les fonctions de coût et les complexités ;
- les preuves (clique, borne) ;
- les sources des valeurs physiques, et la liste des hypothèses ;
e- les réponses aux trois questions de l'incendie, appuyées sur des résultats chiffrés ;
- les résultats de la partie 4.
