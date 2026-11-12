# AVANCEMENT

Une case ne se coche qu'une fois **tout vert** : tests, lint et typage passent, `/but-for-real` a été mené à son terme sans objection restante, et `/run` a été passé dès que la story a quelque chose à lancer.

Les epics sont des lots séquentiels, dont les fichiers ne se recouvrent pas. Le sigle ⋆ marque une extension, à sacrifier en premier en cas de retard (`PLAN.md` § 8).

Correspondance avec la consigne :
- section 1 → epics 2, 3, 6 ;
- section 2 → epics 2, 4, 6 ;
- section 3 → epic 5 ;
- section 4 → epic 7 ;
- section 5 → toutes les epics, et l'epic 8 pour le rapport.

## Epic 1 — Socle

- [x] **1.1 Squelette du projet.** `pyproject.toml` (dépendances d'exécution et de test), paquets `zc/` et `serveur/` vides, `README.md` avec l'installation et le lancement.
  *Critère :* `pytest`, `ruff check .` et `mypy zc serveur` passent ; un test échoue si un module de `zc/` importe `networkx`, `fastapi` ou `uvicorn`.

## Epic 2 — Données

- [x] **2.1 Valeurs physiques sourcées.** `donnees/parametres.json` (vitesse valide, vitesse PMR, débit par mètre de largeur, densité maximale) et `rapport/sources.md`.
  *Critère :* chaque valeur cite son organisme ou son texte, avec l'année ; le chargement refuse une valeur dont la source est absente.
- [x] **2.2 Modèle et format centre.** Modèle de données, lecture et écriture JSON au format imposé, validation.
  *Critère :* l'exemple de la consigne se charge et se réécrit à l'identique. Un test par règle de validation : identifiants uniques ; extrémités existantes ; `type`, `statut` et `sens` dans leurs ensembles ; `occupation ≤ capacite_max` ; `niveau_fumee ∈ [0, 100]`.
- [x] **2.3 Format zone.** Chargement de `zone.json`, préfixage des identifiants par centre, rattachement des connexions aux sorties, vue macro.
  *Critère :* une zone de test se charge ; une connexion vers une sortie inexistante, ou vers un nœud qui n'est pas une sortie, produit une erreur explicite ; la vue macro compte un nœud par centre et par source.
- [x] **2.4 Plan de test du centre détaillé.** Proposition de plan (figure dans `rapport/`) et `donnees/centres/A.json`. Ce plan est **provisoire** : il sert à implémenter la suite ; le plan définitif est la story 2.6.
  *Critère :* un test vérifie la liste des cas de `PLAN.md` § 6 (sorties, magasins, cycle, goulot, arête non PMR contournable, sens unique, nœuds sans capteur).
- [x] **2.5 Centres simples et zone complète.** `B.json`, `C.json` et `zone.json` : 3 centres, au moins 3 sources.
  *Critère :* tout se charge ; le graphe de navigation complet est fortement connexe, vérifié avec `networkx`.
- [ ] **2.6 Plan définitif du centre A, dessiné par le binôme.** Remplace le plan de test par le plan dessiné par le groupe (consigne § 5), à faire quand le reste est implémenté.
  *Critère :* `tests/test_plan_A.py` passe sur le nouveau `A.json` ; la figure `rapport/figures/plan_A.svg` est régénérée et la notice `rapport/plan_centre_A.md` décrit le nouveau plan ; `donnees/zone.json` est mis à jour si les identifiants des sorties de A changent (il relie la zone à `A:EO` et `A:EE`) ; tous les tests du projet passent encore.

## Epic 3 — Algorithmes

- [x] **3.1 Graphe de navigation.** Arcs orientés selon `sens`, filtre PMR, retrait des éléments bloqués, poids selon le critère.
  *Critère :* une arête `unique` donne un seul arc, une arête `bidirectionnel` en donne deux ; aucun arc non PMR dans la vue PMR ; aucun élément bloqué.
- [ ] **3.2 Dijkstra et les trois fonctions de coût.** Plus court, moins encombré (`longueur × (1 + β·τ)`), PMR ; reconstruction du chemin ; complexité indiquée dans la docstring.
  *Critère :* distances identiques à celles de `networkx` sur 50 graphes aléatoires (graine fixée) et sur la zone ; β = 0 redonne le plus court chemin ; une destination inaccessible renvoie « aucun chemin ».
- [ ] **3.3 Itinéraire d'une région vers un centre.** De la source à la sortie d'entrée du centre, avec un prolongement possible jusqu'à un magasin, pour chacun des trois critères.
  *Critère :* sur la zone complète, le chemin PMR n'emprunte aucune arête non PMR et son coût est supérieur ou égal à celui du plus court chemin.
- [ ] **3.4 Distances d'évacuation.** Dijkstra multi-sources depuis toutes les sorties, sur le graphe inversé.
  *Critère :* pour chaque nœud, la distance obtenue égale le minimum des distances calculées sortie par sortie.
- [ ] **3.5 Connexité, articulations, composantes fortement connexes.** Parcours en largeur, Hopcroft–Tarjan, Tarjan, graphe réduit et tri topologique.
  *Critère :* résultats identiques à `connected_components`, `articulation_points`, `strongly_connected_components` et `condensation` de `networkx`, sur 50 graphes aléatoires.

## Epic 4 — Simulation

- [ ] **4.1 Pas de temps et contraintes.** Agents dans un nœud, sur une arête ou en attente ; avancée à vitesse `v·Δt` ; admission tirée au sort avec une graine.
  *Critère :* sur 1000 pas, `o_v ≤ c_v` et `φ_e ≤ c_e·Δt` sont vrais à chaque pas ; deux exécutions avec la même graine donnent le même état.
- [ ] **4.2 Demande.** Arrivées par source, choix d'un centre puis de 1 à 3 magasins, visite aléatoire, retour ; part de PMR.
  *Critère :* conservation (créés = présents + repartis) à chaque pas ; la part de PMR observée est conforme au paramètre, à une tolérance près.
- [ ] **4.3 Routage des agents.** Critère « moins encombré » par défaut, contrainte PMR, recalcul quand l'objectif ou le graphe change.
  *Critère :* aucun agent PMR ne se trouve jamais sur une arête non PMR ; un agent se réoriente quand son arête suivante devient indisponible.
- [ ] **4.4 Taux d'occupation et palette.** `τ_v`, `τ_e = φ_e / (c_e·Δt)`, niveau 1 à 5 avec les bornes 0,2 / 0,4 / 0,6 / 0,8.
  *Critère :* tests aux bornes exactes (0,2 → niveau 2, etc.) ; la file d'attente au bout d'une arête est exposée à part.
- [ ] **4.5 Indicateurs de fréquentation.** Occupation moyenne et maximale, temps de trajet moyen, goulots ; export CSV.
  *Critère :* sur un scénario minimal calculé à la main, les valeurs exportées sont exactes.

## Epic 5 — Incendie

- [ ] **5.1 Diffusion de la fumée.** Règle de la consigne (α, terme source), voisins non orientés ; fumée d'arête = maximum de ses extrémités.
  *Critère :* sur un graphe de 4 nœuds, les valeurs des trois premiers pas sont égales à un calcul fait à la main ; la fumée ne dépasse jamais 100 ; elle ne diminue jamais ; un scénario à deux départs de feu simultanés à t = 0 se diffuse depuis les deux.
- [ ] **5.2 Détection.** Seuils θ₁ et θ₂, retard δ pour les nœuds sans capteur ; état réel et statut connu séparés.
  *Critère :* un nœud avec capteur change de statut au pas où il franchit le seuil ; un nœud sans capteur change exactement δ pas plus tard.
- [ ] **5.3 Effets sur la circulation.** Vitesse et capacité réduites par la fumée ; éléments bloqués retirés du graphe de navigation ; règle de la moitié pour les personnes engagées sur une arête qui se bloque.
  *Critère :* une personne à 40 % de l'arête fait demi-tour, une personne à 60 % continue ; la vitesse et le débit baissent quand la fumée augmente.
- [ ] **5.4 Évacuation.** Alarme, cible = sortie la plus proche, recalcul à chaque mise à jour, sauvés, piégés, charge par sortie, courbe d'évacuation.
  *Critère :* sur le scénario « incendie qui bloque une sortie », la sortie bloquée ne reçoit plus personne après son blocage ; à la fin, sauvés + piégés = présents au déclenchement.
- [ ] **5.5 ⋆ Modes de connaissance global et local.** Paramètre de scénario, comparaison des temps d'évacuation.
  *Critère :* sur un même incendie avec un nœud sans capteur placé sur le chemin d'évacuation, les deux modes donnent des résultats différents, et ces résultats sont exportés.

## Epic 6 — Interface web

À précéder de l'étape C du workflow (design), dont le résultat est figé dans `CLAUDE.md`.

- [ ] **6.1 Serveur.** FastAPI : liste et chargement des scénarios, état, pas, paramètres, feu, itinéraire. Lancement par `python -m serveur`.
  *Critère :* un test par route avec le client de test ; une requête invalide reçoit une erreur 4xx explicite.
- [ ] **6.2 Affichage du graphe.** Cytoscape : zone et centres en nœuds composés, positions du plan, palette à 5 niveaux, bordure et icône pour la fumée et le blocage, légende.
  *Critère :* `/run` : le scénario « journée normale » s'affiche ; les couleurs changent d'un pas à l'autre ; un nœud enfumé se distingue sans recourir à la couleur.
- [ ] **6.3 Lecture et calque d'agents.** Mode automatique, pas à pas, vitesse réglable ; agents dessinés sur un `<canvas>` qui suit le zoom et le déplacement de la vue.
  *Critère :* `/run` sur « pic d'affluence » : l'animation reste fluide (sinon, bascule vers un compteur par nœud et par arête, décision consignée) ; pause et pas à pas fonctionnent.
- [ ] **6.4 Interactions.** Réglage des paramètres, choix du scénario, ⋆ feu au clic, tracé d'un itinéraire avec son coût selon le critère choisi.
  *Critère :* `/run` : chaque contrôle agit sur la simulation ; l'itinéraire tracé est le même que celui que renvoie le moteur.
- [ ] **6.5 Scénarios de démonstration.** Journée normale, pic d'affluence, incendie qui bloque une sortie.
  *Critère :* sur une machine propre, l'installation et le lancement en suivant le README suffisent ; les trois scénarios se jouent jusqu'au bout sans erreur.

## Epic 7 — Graphe des propriétés

En attente de `proprietaires.json`, à demander à l'enseignant.

- [ ] **7.1 Format et analyse de G_P.** Chargement, connexité et composantes, vérification de la propriété de clique et de la borne, points d'articulation (centres, puis propriétaires dans le graphe biparti).
  *Critère :* sur un jeu d'essai conçu à la main, résultats identiques à `networkx` et borne vérifiée ; une fois le vrai fichier reçu, les résultats sont produits sur lui.
- [ ] **7.2 G⃗_P et graphe réduit.** Définition de « majoritaire » fixée d'après le fichier, sans arc d'un centre vers lui-même, Tarjan, graphe réduit, sources, puits, chaînes de contrôle.
  *Critère :* le graphe réduit est vérifié acyclique ; les sources, les puits et la plus longue chaîne sont identiques à ceux calculés par `networkx`.

## Epic 8 — Rapport

- [ ] **8.1 Chaîne de production.** `rapport/rapport.md`, scripts qui génèrent les figures, construction du PDF par pandoc.
  *Critère :* une seule commande produit `rapport/build/rapport.pdf` avec ses figures ; le dépôt est poussé sur un dépôt distant accessible au correcteur, et le rapport en donne le lien (livrable de la consigne § 5).
- [ ] **8.2 Modélisation.** Formats, plan du bâtiment, palette et seuils justifiés, choix des agents.
  *Critère :* chaque écart à la consigne est justifié en toutes lettres (agents, palette à 5 niveaux, champs ajoutés).
- [ ] **8.3 Algorithmes.** Fonctions de coût, complexités, alternative écartée pour « moins encombré ».
  *Critère :* chaque algorithme a sa complexité justifiée ; les trois critères d'itinéraire sont illustrés sur un même trajet.
- [ ] **8.4 Incendie.** Règles et paramètres justifiés ; réponses aux trois questions imposées, appuyées sur les indicateurs.
  *Critère :* chaque question a une réponse argumentée et chiffrée.
- [ ] **8.5 Propriétés.** Preuve de la clique et de la borne, résultats sur le fichier fourni, interprétation des articulations et de la structure de G⃗_P.
  *Critère :* les preuves sont complètes ; les résultats correspondent à ceux de l'epic 7.
