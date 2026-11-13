// Calque des agents : un <canvas> posé sur le plan Cytoscape. Chaque agent est un point
// graphite (creux s'il est à mobilité réduite). Entre deux pas, les points glissent de leur
// ancienne position à la nouvelle, pour que l'animation reste fluide.

const RAYON_AGENT = 2;  // points de 4 px, quelle que soit l'échelle
const ECART_DANS_NOEUD = 9;  // écart entre agents regroupés sur un même nœud (unités du plan)

const calque = {
  canvas: null,
  cy: null,
  avant: {},  // id de l'agent → position au pas précédent {x, y, pmr}
  apres: {},  // id de l'agent → position au pas courant
  debut: 0,  // instant où le glissement a commencé (ms)
  duree: 0,  // durée du glissement (ms)
};

function creerCalque(canvas, cy) {
  calque.canvas = canvas;
  calque.cy = cy;
  // Le calque suit la vue : on redessine quand on zoome, qu'on déplace le plan ou que la
  // fenêtre change de taille.
  cy.on("viewport resize", dessinerAgents);
  window.addEventListener("resize", dessinerAgents);
}

// Position d'un agent dans le repère du plan (celui des positions Cytoscape).
// `rang` : combien d'agents sont déjà placés sur ce nœud, pour les étaler en spirale
// autour du nœud au lieu de les empiler.
function positionAgent(agent, rang) {
  const depuis = calque.cy.getElementById(agent.depuis).position();
  if (agent.vers !== null) {
    const vers = calque.cy.getElementById(agent.vers).position();
    return {
      x: depuis.x + (vers.x - depuis.x) * agent.avancee,
      y: depuis.y + (vers.y - depuis.y) * agent.avancee,
    };
  }
  const angle = rang * 2.4;  // angle d'or, en radians : la spirale reste régulière
  const distance = ECART_DANS_NOEUD * Math.sqrt(rang);
  return {
    x: depuis.x + distance * Math.cos(angle),
    y: depuis.y + distance * Math.sin(angle),
  };
}

// Nouvel état reçu : les agents glisseront pendant `duree` ms vers leur nouvelle position.
function placerAgents(etat, duree) {
  const rangs = {};
  const positions = {};
  for (const agent of etat.agents) {
    let rang = 0;
    if (agent.vers === null) {
      if (rangs[agent.depuis] === undefined) {
        rangs[agent.depuis] = 0;
      }
      rang = rangs[agent.depuis];
      rangs[agent.depuis] = rang + 1;
    }
    const position = positionAgent(agent, rang);
    position.pmr = agent.pmr;
    positions[agent.id] = position;
  }
  // Le point de départ du glissement est la position affichée en ce moment.
  calque.avant = positionsAffichees();
  calque.apres = positions;
  calque.debut = performance.now();
  calque.duree = duree;
  requestAnimationFrame(animer);
}

// Les positions telles qu'elles sont dessinées à cet instant (glissement en cours compris).
function positionsAffichees() {
  const t = avancementDuGlissement();
  const positions = {};
  for (const id in calque.apres) {
    const fin = calque.apres[id];
    const debut = calque.avant[id];
    if (debut === undefined) {
      positions[id] = fin;
    } else {
      positions[id] = {
        x: debut.x + (fin.x - debut.x) * t,
        y: debut.y + (fin.y - debut.y) * t,
        pmr: fin.pmr,
      };
    }
  }
  return positions;
}

// Entre 0 (début du glissement) et 1 (agents arrivés).
function avancementDuGlissement() {
  if (calque.duree <= 0) {
    return 1;
  }
  const t = (performance.now() - calque.debut) / calque.duree;
  return Math.min(1, t);
}

function animer() {
  dessinerAgents();
  if (avancementDuGlissement() < 1) {
    requestAnimationFrame(animer);
  }
}

function effacerAgents() {
  calque.avant = {};
  calque.apres = {};
  dessinerAgents();
}

function dessinerAgents() {
  const canvas = calque.canvas;
  // Le canvas prend la taille de son conteneur (et la densité de pixels de l'écran).
  const ratio = window.devicePixelRatio || 1;
  const largeur = canvas.clientWidth;
  const hauteur = canvas.clientHeight;
  if (canvas.width !== Math.round(largeur * ratio)) {
    canvas.width = Math.round(largeur * ratio);
  }
  if (canvas.height !== Math.round(hauteur * ratio)) {
    canvas.height = Math.round(hauteur * ratio);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, largeur, hauteur);

  // Passage du repère du plan au repère de l'écran : zoom puis déplacement de la vue.
  const zoom = calque.cy.zoom();
  const pan = calque.cy.pan();
  const positions = positionsAffichees();

  ctx.fillStyle = TRAIT;
  ctx.strokeStyle = TRAIT;
  ctx.lineWidth = 1.5;
  for (const id in positions) {
    const p = positions[id];
    const x = p.x * zoom + pan.x;
    const y = p.y * zoom + pan.y;
    ctx.beginPath();
    ctx.arc(x, y, RAYON_AGENT, 0, 2 * Math.PI);
    if (p.pmr) {
      ctx.stroke();
    } else {
      ctx.fill();
    }
  }
}
