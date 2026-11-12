// Dessin du plan avec Cytoscape : les centres sont des nœuds composés qui contiennent
// leurs magasins, carrefours, sanitaires et sorties ; les sources sont à part.
// Les couleurs et les motifs suivent le design system de CLAUDE.md.

// Positions du JSON en mètres ; on les agrandit pour travailler avec des tailles en pixels.
const ECHELLE = 10;

// Gamme d'occupation, du niveau 1 (très faible) au niveau 5 (très élevé).
const COULEURS_NIVEAU = ["#E6E8F5", "#B4B9E1", "#7C84C9", "#4651A6", "#1D2468"];

const TRAIT = "#2B2F33";
const FOND = "#F5F7F6";
const FEU = "#C8102E";
const FUMEE = "#7A808A";
const ITINERAIRE = "#A87400";

const PICTO_SORTIE = "/web/pictos/sortie.svg";
const PICTO_FLAMME = "/web/pictos/flamme.svg";
const PICTO_CROIX = "/web/pictos/croix.svg";

const NOMS_SOURCES = {parking: "Parking", station: "Station", quartier: "Quartier"};

// Les sélecteurs sont lus dans l'ordre : un style placé plus bas l'emporte.
const STYLE_PLAN = [
  {
    selector: "node",
    style: {
      "background-color": "data(couleur)",
      "border-width": 1.5,
      "border-color": TRAIT,
      "width": 40,
      "height": 40,
      "label": "data(libelle)",
      "font-family": "Atkinson Hyperlegible, sans-serif",
      // Grand pour le vidéoprojecteur ; les libellés passent à la ligne plutôt que de
      // déborder sur le voisin (deux nœuds voisins sont à 120 px au moins).
      "font-size": 30,
      "color": TRAIT,
      "text-valign": "bottom",
      "text-margin-y": 4,
      "text-wrap": "wrap",
      "text-max-width": 110,
      "text-background-color": FOND,
      "text-background-opacity": 0.8,
    },
  },
  {
    selector: ".centre",
    style: {
      "background-color": FOND,
      "background-opacity": 0,
      "border-width": 3,
      "shape": "rectangle",
      "padding": 40,
      "font-size": 36,
      "text-max-width": 400,
      "font-weight": "bold",
      "text-valign": "top",
      "text-halign": "center",
      "text-margin-y": -8,
    },
  },
  {
    selector: ".source",
    style: {
      "shape": "round-rectangle",
      "width": 60,
      "height": 40,
      "background-color": "#FFFFFF",
      "border-width": 3,
      "font-weight": "bold",
    },
  },
  {
    selector: ".sortie",
    style: {
      "shape": "round-rectangle",
      "background-image": PICTO_SORTIE,
      "background-fit": "cover",
      "border-color": "#00873E",
    },
  },
  {
    selector: ".enfume",
    style: {
      "border-width": 6,
      "border-style": "dashed",
      "border-color": FUMEE,
    },
  },
  {
    selector: ".bloque",
    style: {
      "border-width": 9,
      "border-style": "double",
      "border-color": FEU,
      "background-image": PICTO_CROIX,
      "background-fit": "contain",
    },
  },
  {
    selector: ".sortie.bloque",
    style: {
      // Le pictogramme de sortie, et la croix par-dessus.
      "background-image": [PICTO_SORTIE, PICTO_CROIX],
      "background-fit": ["cover", "contain"],
    },
  },
  {
    selector: ".foyer",
    style: {
      "background-image": PICTO_FLAMME,
      "background-fit": "contain",
    },
  },
  {
    selector: "edge",
    style: {
      "width": 8,
      "line-color": "data(couleur)",
      "line-outline-width": 1.5,
      "line-outline-color": TRAIT,
      "curve-style": "bezier",
      "target-arrow-shape": "none",
    },
  },
  {
    // Couloir à sens unique : une flèche dans le sens autorisé.
    selector: ".sens-unique",
    style: {
      "target-arrow-shape": "triangle",
      "target-arrow-color": TRAIT,
      "arrow-scale": 1.2,
    },
  },
  {
    // Itinéraire tracé : trait épais ambre foncé ; placé avant la fumée et le blocage
    // pour que leurs motifs restent visibles par-dessus.
    selector: "edge.itineraire",
    style: {
      "width": 14,
      "line-color": ITINERAIRE,
      "line-outline-color": TRAIT,
      "z-index": 10,
    },
  },
  {
    selector: "node.itineraire",
    style: {
      "border-width": 5,
      "border-color": ITINERAIRE,
    },
  },
  {
    selector: "edge.enfume",
    style: {
      "line-style": "dashed",
      "line-dash-pattern": [14, 8],
      "line-outline-color": FUMEE,
    },
  },
  {
    selector: "edge.bloque",
    style: {
      "line-color": FEU,
      "line-style": "dashed",
      "line-dash-pattern": [3, 3],
      "line-outline-width": 0,
    },
  },
];

function creerPlan(conteneur) {
  return cytoscape({
    container: conteneur,
    style: STYLE_PLAN,
    layout: {name: "preset"},
    minZoom: 0.1,
    maxZoom: 4,
    // Le plan n'est pas modifiable à la souris : on ne déplace pas les magasins.
    autoungrabify: true,
    boxSelectionEnabled: false,
  });
}

// Construit tous les éléments à partir d'un état : appelé au chargement d'un scénario.
function construirePlan(cy, etat) {
  const elements = [];
  const centres = [];
  for (const noeud of etat.noeuds) {
    if (!centres.includes(noeud.centre)) {
      centres.push(noeud.centre);
      elements.push({
        group: "nodes",
        data: {id: "centre-" + noeud.centre, libelle: "Centre " + noeud.centre},
        classes: "centre",
      });
    }
  }
  for (const noeud of etat.noeuds) {
    let libelle = noeud.nom;
    if (libelle === null) {
      libelle = noeud.id;
    }
    elements.push({
      group: "nodes",
      data: {id: noeud.id, parent: "centre-" + noeud.centre, libelle: libelle,
             couleur: COULEURS_NIVEAU[0]},
      position: {x: noeud.x * ECHELLE, y: noeud.y * ECHELLE},
      classes: noeud.type,  // « sortie » donne le pictogramme vert
    });
  }
  for (const source of etat.sources) {
    elements.push({
      group: "nodes",
      data: {id: source.id, libelle: NOMS_SOURCES[source.type] + " " + source.id,
             couleur: "#FFFFFF"},
      position: {x: source.x * ECHELLE, y: source.y * ECHELLE},
      classes: "source",
    });
  }
  for (const arete of etat.aretes) {
    let classes = "";
    if (arete.sens === "unique") {
      classes = "sens-unique";
    }
    elements.push({
      group: "edges",
      data: {id: "arete-" + arete.id, source: arete.source, target: arete.cible,
             couleur: COULEURS_NIVEAU[0]},
      classes: classes,
    });
  }
  cy.elements().remove();
  cy.add(elements);
  mettreAJourPlan(cy, etat);
  cy.fit(undefined, 30);
}

// Surligne un itinéraire : ses nœuds et les couloirs (numéros) qu'il emprunte.
function tracerItineraire(cy, chemin, aretes) {
  effacerItineraire(cy);
  for (const id of chemin) {
    cy.getElementById(id).addClass("itineraire");
  }
  for (const numero of aretes) {
    cy.getElementById("arete-" + numero).addClass("itineraire");
  }
}

function effacerItineraire(cy) {
  cy.elements().removeClass("itineraire");
}

// Met à jour les couleurs et les motifs à chaque pas, sans reconstruire le plan.
function mettreAJourPlan(cy, etat) {
  let foyers = [];
  if (etat.alarme !== null) {
    foyers = etat.alarme.foyers;
  }
  cy.batch(function () {
    for (const noeud of etat.noeuds) {
      const element = cy.getElementById(noeud.id);
      element.data("couleur", COULEURS_NIVEAU[noeud.niveau - 1]);
      element.toggleClass("enfume", noeud.statut === "enfumé");
      element.toggleClass("bloque", noeud.statut === "bloqué");
      element.toggleClass("foyer", foyers.includes(noeud.id));
    }
    for (const arete of etat.aretes) {
      const element = cy.getElementById("arete-" + arete.id);
      element.data("couleur", COULEURS_NIVEAU[arete.niveau - 1]);
      element.toggleClass("enfume", arete.statut === "enfumé");
      element.toggleClass("bloque", arete.statut === "bloqué");
    }
  });
}
