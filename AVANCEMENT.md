# AVANCEMENT

Une case ne se coche qu'une fois **tout vert** : tests et lint passent (le typage `mypy` est retiré le 2026-11-24 avec les annotations de type, décision de l'utilisateur), `/but-for-real` a été mené à son terme sans objection restante, et `/run` a été passé dès que la story a quelque chose à lancer.

Les epics sont des lots séquentiels. L'interface grandit au fil du projet (décision du 2026-11-20) : une visionneuse est livrée juste après les données (epic 3), puis chaque epic, des algorithmes à l'incendie, se termine par sa story d'affichage, qui complète `epic3_visionneuse/serveur/` et `epic3_visionneuse/web/`. Les fichiers sont rangés par epic (décision du 2026-11-24, voir `PLAN.md` § 1) : une story écrit ses fichiers neufs dans le dossier de son epic. Le sigle ⋆ marque une extension, à sacrifier en premier en cas de retard (`PLAN.md` § 8).

Sujet transposé : un réseau de trois stations spatiales à la place d'une zone commerciale (`PLAN.md` § 0). Les sections de la consigne restent les mêmes.

Correspondance avec la consigne :
- section 1 → epics 2, 3, 4 ;
- section 2 → epics 2, 5 ;
- section 3 → epic 6 ;
- section 4 → epic 8, exercice de réflexion dont les réponses sont rédigées dans le rapport (une story par question) ;
- section 5 → toutes les epics, l'interface dans les epics 3 à 7, et l'epic 9 pour le rapport.

## Epic 1 — Socle

- [x] **1.1 Squelette du projet.** `pyproject.toml` (dépendances d'exécution et de test), paquets `moteur/` (sans `__init__.py`, décision du 2026-11-20 ; `serveur/` arrive à la story 3.1). Le `README.md` est reporté à la story 7.1.
  *Critère :* `pytest`, `ruff check .` et `mypy` passent ; un test (`epic1_socle/tests/test_dependances.py`) échoue si un module d'un `epic*/moteur/` importe `networkx`, `fastapi` ou `uvicorn`. Ce test a été supprimé le 2026-11-24 (décision de l'utilisateur) : la règle reste, mais plus aucun test ne la vérifie.

## Epic 2 — Données

- [x] **2.1 Valeurs physiques.** `epic2_donnees/donnees/parametres.json` (vitesse d'une personne valide, vitesse d'une personne en fauteuil roulant, débit par mètre de largeur de passage, surface par personne) et `epic9_rapport/sources.md`. Les stations ont une gravité artificielle : les valeurs sont terrestres.
  *Critère :* chaque valeur cite son organisme ou son document, avec l'année, ou bien est marquée « hypothèse » avec son raisonnement (vérifié à la relecture : le programme ne contrôle pas les données, décision du 2026-11-20) ; le fichier se charge. La fonction de lecture (`charger_parametres`), que seuls les tests utilisaient, est retirée le 2026-11-24 : elle reviendra avec la simulation (epic 5), qui en aura besoin.
- [x] **2.2 Modèle et format station.** Modèle de données, lecture et écriture JSON au format imposé.
  *Critère :* l'exemple de la consigne se charge et se réécrit à l'identique, champs facultatifs compris. Pas de validation des données (décision du 2026-11-20). Depuis le 2026-11-24, seuls `x` et `y` sont conservés : `nom` et `largeur` sont ignorés à la lecture (code simplifié). L'écriture d'un fichier de station (`ecrire_station`), qui ne servait qu'au test de réécriture, est retirée le même jour : seule la lecture reste.
- [x] **2.3 Format réseau.** Chargement de `reseau.json`, préfixage des identifiants par station, rattachement des tunnels aux sas, vue macro (fonction `vue_macro` retirée le 2026-11-24 : seuls les tests l'utilisaient ; l'affichage regroupe déjà les nœuds par station avec Cytoscape).
  *Critère :* un réseau de test se charge ; les identifiants sont préfixés par station ; les tunnels relient des sorties ou des sources ; la vue macro compte un nœud par station et par source. Pas de validation des données (décision du 2026-11-20).
- [x] **2.4 Plan de la station détaillée A, dessiné par le groupe.** Plan dessiné (figure dans `epic9_rapport/`), `epic2_donnees/donnees/stations/A.json` et une notice qui situe chaque cas demandé sur le plan.
  *Critère :* `epic2_donnees/tests/test_plan_A.py` vérifie la liste des cas de `PLAN.md` § 6 (sas, modules, cycle, goulot, arête non PMR contournable, nœuds sans capteur).
- [x] **2.5 Stations simples et réseau complet.** `B.json`, `C.json` et `reseau.json` : 3 stations reliées par des tunnels entre leurs sas ; les sas sont les nœuds sources (décision du 2026-11-20). En attendant le plan du groupe, A est un plan provisoire.
  *Critère :* tout se charge ; B et C ont au moins 12 nœuds et 2 sorties ; le graphe de navigation complet est fortement connexe, vérifié avec `networkx`.

## Epic 3 — Visionneuse

Pour voir les plans et le réseau dès maintenant. Design **super simple** (décision du 2026-11-20) : l'ancien design system n'est pas repris. Avant la story 3.2, proposer le choix entre `frontend-design` et `ui-ux-pro-max` (règle globale de design).

- [x] **3.1 Serveur minimal.** FastAPI : une route qui renvoie le réseau chargé (stations, nœuds, arêtes, sources, tunnels, positions), une route qui relit les fichiers JSON, et la page servie. Lancement par `python -m serveur`, depuis la racine (fichier `serveur.py` ; c'était `python -m epic3_visionneuse.serveur` jusqu'au 2026-11-24, renommé à la demande de l'utilisateur).
  *Critère :* un test par route avec le client de test ; `python -m serveur` démarre et la page s'ouvre.
- [x] **3.2 Affichage du réseau et des plans.** Cytoscape : stations en nœuds composés, positions du plan, tous les nœuds en points gris sans nom (décision du 2026-11-20), arêtes non PMR distinguées, tunnels, bouton « Recharger ».
  *Critère :* `/run` : le réseau complet s'affiche ; après une modification d'un fichier JSON, « Recharger » met l'affichage à jour ; une arête non PMR et un tunnel se reconnaissent grâce à la légende.

## Epic 4 — Algorithmes

- [x] **4.1 Graphe de navigation.** Arcs orientés selon `sens`, filtre PMR, retrait des éléments bloqués, poids selon le critère.
  *Critère :* une arête `unique` donne un seul arc, une arête `bidirectionnel` en donne deux ; aucun arc non PMR dans la vue PMR ; aucun élément bloqué.
- [x] **4.2 Dijkstra et les trois fonctions de coût.** Plus court, moins encombré (`longueur × (1 + β·τ)`), PMR ; reconstruction du chemin ; complexité indiquée dans la docstring.
  *Critère :* distances identiques à celles de `networkx` sur 50 graphes aléatoires (graine fixée) et sur le réseau ; β = 0 redonne le plus court chemin ; une destination inaccessible renvoie « aucun chemin ».
- **4.3 Itinéraire d'une région vers une station — écartée** (décision de l'utilisateur, 2026-11-24). Prévu : d'un sas d'arrivée au meilleur sas d'entrée de la station visée, choisi automatiquement, avec un prolongement possible jusqu'à un module. Motif : la 4.2 répond déjà à la question 2 de la consigne, puisqu'une région est un sas et qu'on entre dans une station par ses sas ; l'itinéraire « région → station » est donc un itinéraire de sas à sas, que les trois fonctions de `chemins.py` calculent. Seul le choix automatique du sas d'entrée est abandonné : la destination d'un visiteur est un lieu précis (sas ou module), pas une station abstraite. Le prolongement jusqu'à un module n'était pas demandé par la consigne. Le critère prévu (chemin PMR sans arête interdite, coût au moins égal au plus court, sur le réseau complet) est déjà vérifié par les tests de la 4.2. Écart à justifier dans le rapport (9.2), voir `epic9_rapport/ecarts.md`.
  *Critère :* sur le réseau complet, le chemin PMR n'emprunte aucune arête non PMR et son coût est supérieur ou égal à celui du plus court chemin.
- [x] **4.4 Distances d'évacuation.** Dijkstra multi-sources depuis toutes les sorties. Sans graphe inversé (décision du 2026-11-24) : toutes nos arêtes sont bidirectionnelles, le coût de la sortie vers un nœud est donc celui du nœud vers la sortie.
  *Critère :* pour chaque nœud, la distance obtenue égale le minimum des distances calculées sortie par sortie.


## Epic 5 — Simulation

- [ ] **5.1 Pas de temps et contraintes.** Agents dans un nœud, sur une arête ou en attente ; avancée à vitesse `v·Δt` ; admission tirée au sort avec une graine.
  *Critère :* sur 1000 pas, `o_v ≤ c_v` et `φ_e ≤ c_e·Δt` sont vrais à chaque pas ; deux exécutions avec la même graine donnent le même état.
- [ ] **5.2 Demande.** Arrivées par les sas, choix d'une station puis de 1 à 3 modules, visite aléatoire, retour ; part de PMR.
  *Critère :* conservation (créés = présents + repartis) à chaque pas ; la part de PMR observée est conforme au paramètre, à une tolérance près.
- [ ] **5.3 Routage des agents.** Critère « moins encombré » par défaut, contrainte PMR, recalcul quand l'objectif ou le graphe change.
  *Critère :* aucun agent PMR ne se trouve jamais sur une arête non PMR ; un agent se réoriente quand son arête suivante devient indisponible.
- [ ] **5.4 Taux d'occupation et palette.** `τ_v`, `τ_e = φ_e / (c_e·Δt)`, niveau 1 à 5 avec les bornes 0,2 / 0,4 / 0,6 / 0,8.
  *Critère :* tests aux bornes exactes (0,2 → niveau 2, etc.) ; la file d'attente au bout d'une arête est exposée à part.
- [ ] **5.5 Indicateurs de fréquentation.** Occupation moyenne et maximale, temps de trajet moyen, goulots ; export CSV.
  *Critère :* sur une simulation minimale calculée à la main, les valeurs exportées sont exactes.
- [ ] **5.6 Lecture de la simulation.** Routes (pas, recommencer, affluence) et affichage : lecture automatique, pas à pas, pause, vitesse, « Recommencer », curseur d'affluence, couleur d'occupation à 5 niveaux et sa légende.
  *Critère :* `/run` : les couleurs changent d'un pas à l'autre ; pause, pas à pas et « Recommencer » fonctionnent ; le curseur change le nombre d'arrivées.
- [ ] **5.7 ⋆ Calque d'agents.** Agents dessinés sur un `<canvas>` qui suit le zoom et le déplacement de la vue.
  *Critère :* `/run` avec l'affluence au maximum : l'animation reste fluide (sinon, bascule vers un compteur par nœud et par arête, décision consignée).

## Epic 6 — Incendie

- [ ] **6.1 Diffusion de la fumée.** Règle de la consigne (α, terme source), voisins non orientés ; fumée d'arête = maximum de ses extrémités.
  *Critère :* sur un graphe de 4 nœuds, les valeurs des trois premiers pas sont égales à un calcul fait à la main ; la fumée ne dépasse jamais 100 ; elle ne diminue jamais ; deux départs de feu simultanés à t = 0 se diffusent depuis les deux.
- [ ] **6.2 Détection.** Seuils θ₁ et θ₂, retard δ pour les nœuds sans capteur ; état réel et statut connu séparés.
  *Critère :* un nœud avec capteur change de statut au pas où il franchit le seuil ; un nœud sans capteur change exactement δ pas plus tard.
- [ ] **6.3 Effets sur la circulation.** Vitesse et capacité réduites par la fumée ; éléments bloqués retirés du graphe de navigation ; règle de la moitié pour les personnes engagées sur une arête qui se bloque.
  *Critère :* une personne à 40 % de l'arête fait demi-tour, une personne à 60 % continue ; la vitesse et le débit baissent quand la fumée augmente.
- [ ] **6.4 Évacuation.** Alarme, station fermée, cible = sas le plus proche, recalcul à chaque mise à jour, sauvés, piégés, charge par sortie, courbe d'évacuation.
  *Critère :* avec un feu allumé près d'un sas, ce sas ne reçoit plus personne après son blocage ; à la fin, sauvés + piégés = présents au déclenchement.
- [ ] **6.5 ⋆ Modes de connaissance global et local.** Paramètre de la simulation, comparaison des temps d'évacuation.
  *Critère :* sur un même incendie avec un nœud sans capteur placé sur le chemin d'évacuation, les deux modes donnent des résultats différents, et ces résultats sont exportés.
- [ ] **6.6 Affichage de l'incendie.** Routes et affichage : fumée et blocage montrés autrement que par la couleur (bordure, icône), réglage de α, θ₁, θ₂ et δ, ⋆ feu au clic, évacuation visible.
  *Critère :* `/run` : un nœud enfumé et un nœud bloqué se distinguent sans recourir à la couleur ; un feu allumé se propage à l'écran et les occupants rejoignent les sorties.

## Epic 7 — Interface finale

- [ ] **7.1 Indicateurs et démonstration.** Rangée d'indicateurs (visiteurs, occupation maximale, sauvés, piégés, durée d'évacuation) et courbe des personnes encore à bord ; `README.md` avec l'installation, le lancement et la démonstration.
  *Critère :* sur une machine propre, l'installation et le lancement en suivant le README suffisent ; une journée calme, l'affluence au maximum, puis un feu allumé près d'un sas se jouent jusqu'au bout sans erreur dans la console ; les indicateurs suivent la simulation.

## Epic 8 — Graphe des propriétés

`proprietaires.json` est écrit par le groupe (`PLAN.md` § 7).

**Un exercice de réflexion, pas un livrable de code** (décision de l'utilisateur, 2026-11-26). La section 4 de la consigne pose des questions de théorie des graphes. On y répond par écrit dans le rapport, avec des démonstrations et des justifications appuyées sur `proprietaires.json`. Les livrables de la consigne (§ 5) n'exigent pas de code pour cette partie. **On peut s'aider de code** pour calculer ou vérifier les réponses sur le fichier : un petit script dans `epic8_proprietes/`, qui peut utiliser `networkx`. Ce script n'entre ni dans le moteur ni dans l'application. Chaque story ci-dessous produit sa réponse rédigée dans `epic9_rapport/`.

Ces stories n'ont ni tests ni `/run` : on en coche une quand sa réponse est rédigée et vérifiée, et que `/but-for-real` a été mené à son terme.

Une story par question de la consigne (§ 4) :

| Story | Question de la consigne |
|---|---|
| 8.1 | aucune : prépare les « données fournies » dont parlent les questions 1, 3 et 4 |
| 8.2 | Q1 — G_P est-il connexe ? ses composantes connexes |
| 8.3 | Q2 — les centres d'un même propriétaire forment une clique ; borne sur le nombre d'arêtes |
| 8.4 | Q3 — points d'articulation de G_P et leur interprétation |
| 8.5 | Q4 — G⃗_P, son graphe réduit, acyclicité, sources, puits, chaînes de contrôle |

- [ ] **8.1 Jeu de données des propriétaires.** `epic8_proprietes/donnees/proprietaires.json` : une douzaine de stations (dont A, B et C), des agences spatiales et des opérateurs privés, les parts en pourcentage. Le fichier est relu à la main, pas validé par du code. Une notice dans `epic9_rapport/` explique comment il a été construit.
  *Critère :* les parts de chaque station font 100 % ; le fichier donne une réponse intéressante à chaque question (`PLAN.md` § 7) : au moins une station articulation et un propriétaire articulation dans G_P, et dans G⃗_P au moins une composante fortement connexe de plus d'un sommet et une chaîne de contrôle de longueur au moins 3.
- [ ] **8.2 Q1 — Connexité de G_P.** Construire G_P (une arête entre deux stations qui ont un propriétaire en commun), le dessiner, dire s'il est connexe et donner ses composantes connexes.
  *Critère :* la réponse est justifiée sur les données (dessin de G_P à l'appui) ; les composantes sont vérifiées, à la main ou par le script.
- [ ] **8.3 Q2 — Clique et borne.** Démontrer que les stations d'un même propriétaire forment une clique dans G_P, en déduire la borne `|E_P| ≤ Σ_p C(k_p, 2)` (k_p = nombre de stations du propriétaire p) et l'appliquer au fichier.
  *Critère :* la preuve est complète ; elle explique pourquoi la borne est une inégalité et non une égalité (deux propriétaires peuvent produire la même arête) ; le nombre réel d'arêtes de G_P est comparé à la borne.
- [ ] **8.4 Q3 — Points d'articulation.** Les stations articulation de G_P, puis les propriétaires articulation, dans le graphe biparti propriétaires–stations (`PLAN.md` § 7) ; dire ce que la disparition de chacun scinde.
  *Critère :* chaque articulation est trouvée et interprétée en une phrase ; la liste est vérifiée, à la main ou par le script.
- [ ] **8.5 Q4 — G⃗_P et graphe réduit.** Construire G⃗_P (arc c1 → c2 si le propriétaire majoritaire de c1, strictement plus de 50 %, a une part dans c2 ; pas d'arc d'une station vers elle-même), ses composantes fortement connexes, puis son graphe réduit. Dire s'il est acyclique et décrire sa structure : sources, puits, chaînes de contrôle.
  *Critère :* l'acyclicité du graphe réduit est justifiée par le théorème (elle est toujours vraie) ; les composantes, les sources, les puits et la plus longue chaîne de contrôle sont identifiés et vérifiés, à la main ou par le script.

## Epic 9 — Rapport

- [ ] **9.1 Chaîne de production.** `epic9_rapport/rapport.md`, scripts qui génèrent les figures, construction du PDF par pandoc.
  *Critère :* une seule commande produit `epic9_rapport/build/rapport.pdf` avec ses figures ; le dépôt est poussé sur un dépôt distant accessible au correcteur, et le rapport en donne le lien (livrable de la consigne § 5).
- [ ] **9.2 Modélisation.** Transposition du sujet et sa table de correspondance, formats, plan des stations, accessibilité, palette et seuils justifiés, choix des agents.
  *Critère :* chaque écart à la consigne est justifié en toutes lettres (sujet transposé, agents, palette à 5 niveaux, champs ajoutés, type `module` au lieu de `magasin`, sas comme nœuds sources, définition de l'accessibilité) ; les hypothèses sur les valeurs physiques sont listées à part.
- [ ] **9.3 Algorithmes.** Fonctions de coût, complexités, alternative écartée pour « moins encombré ».
  *Critère :* chaque algorithme a sa complexité justifiée ; les trois critères d'itinéraire sont illustrés sur un même trajet.
- [ ] **9.4 Incendie.** Règles et paramètres justifiés, limite de la diffusion symétrique de la fumée ; réponses aux trois questions imposées, appuyées sur les indicateurs.
  *Critère :* chaque question a une réponse argumentée et chiffrée.
- [ ] **9.5 Propriétés.** Assembler dans le rapport les réponses rédigées aux stories 8.1 à 8.5 : construction du jeu de données, puis une réponse par question de la section 4 de la consigne.
  *Critère :* chacune des quatre questions de la section 4 a sa réponse, dans l'ordre de la consigne ; les résultats correspondent à ceux de l'epic 8.
