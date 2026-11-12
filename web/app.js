// La page : choix du scénario, bandeau, et dialogue avec le serveur (serveur/app.py).

const plan = creerPlan(document.getElementById("graphe"));
let scenarios = [];
const VALEUR_REFUSEE = "valeur refusée";

// Appelle le serveur, avec un corps JSON facultatif ; en cas d'erreur, lève une Error
// avec le message du serveur.
async function appeler(methode, adresse, corps) {
  const options = {method: methode};
  if (corps !== undefined) {
    options.headers = {"Content-Type": "application/json"};
    options.body = JSON.stringify(corps);
  }
  let reponse;
  try {
    reponse = await fetch(adresse, options);
  } catch (erreur) {
    throw new Error("Le serveur ne répond pas : relancer « python -m serveur ».");
  }
  const contenu = await reponse.json();
  if (!reponse.ok) {
    // Nos erreurs ont un message en français ; celles de la validation automatique
    // (valeur hors bornes) sont une liste, on renvoie alors un message générique.
    if (typeof contenu.detail === "string") {
      throw new Error(contenu.detail);
    }
    throw new Error(VALEUR_REFUSEE);
  }
  return contenu;
}

function afficherMessage(texte) {
  document.getElementById("message").textContent = texte;
}

// 754 s → « 00:12:34 ».
function formaterHeure(secondes) {
  const total = Math.floor(secondes);
  const heures = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const reste = total % 60;
  return String(heures).padStart(2, "0") + ":" + String(minutes).padStart(2, "0") + ":"
    + String(reste).padStart(2, "0");
}

// Le bandeau passe au rouge dès que l'alarme est déclenchée.
function mettreAJourBandeau(etat) {
  document.getElementById("horloge").textContent = formaterHeure(etat.temps);
  const bandeau = document.getElementById("bandeau");
  const texte = document.getElementById("etat-alarme");
  if (etat.alarme !== null && etat.alarme.debut !== null) {
    bandeau.classList.add("alarme");
    texte.textContent = "Évacuation en cours, centre " + etat.alarme.centre + " : "
      + etat.alarme.sauves + " sauvés, " + etat.alarme.pieges + " piégés";
  } else {
    bandeau.classList.remove("alarme");
    if (etat.alarme !== null) {
      texte.textContent = "Feu dans le centre " + etat.alarme.centre + ", pas encore détecté";
    } else {
      texte.textContent = "Fonctionnement normal";
    }
  }
}

function afficherDescription() {
  const choisi = document.getElementById("scenario").value;
  for (const scenario of scenarios) {
    if (scenario.id === choisi) {
      document.getElementById("description").textContent = scenario.description;
    }
  }
}

// Affiche un nouvel état ; les agents glissent vers leur place pendant `duree` ms.
function afficherEtat(etat, duree) {
  mettreAJourPlan(plan, etat);
  mettreAJourBandeau(etat);
  placerAgents(etat, duree);
}

// Augmente à chaque chargement : une réponse demandée avant le dernier chargement
// (pas en cours au moment du clic sur « Charger ») ne doit pas être affichée.
let numeroDeScenario = 0;

// Un scénario vient d'être chargé (ou repris) : on redessine tout.
function afficherNouveauScenario(etat) {
  numeroDeScenario = numeroDeScenario + 1;
  construirePlan(plan, etat);
  remplirReglages(etat);
  remplirItineraire(etat);
  effacerAgents();
  afficherEtat(etat, 0);
  activerLecture(true);
}

async function charger() {
  pause();
  const choisi = document.getElementById("scenario").value;
  try {
    const etat = await appeler("POST", "/api/scenarios/" + choisi);
    afficherNouveauScenario(etat);
    afficherMessage("");
  } catch (erreur) {
    afficherMessage(erreur.message);
  }
}

// --- Lecture --------------------------------------------------------------------------
// C'est la page qui fait avancer l'horloge : en lecture, elle demande des pas au serveur
// à la vitesse choisie. Pause = plus de demandes ; pas à pas = une seule demande.

let enLecture = false;
let minuterie = null;
let numeroDeLecture = 0;

function activerLecture(scenarioCharge) {
  document.getElementById("lancer").disabled = !scenarioCharge || enLecture;
  document.getElementById("pause").disabled = !scenarioCharge || !enLecture;
  document.getElementById("un-pas").disabled = !scenarioCharge;
}

// Demande `nombre` pas au serveur et affiche le résultat. Renvoie false en cas d'erreur
// (la lecture s'arrête alors).
async function avancer(nombre, duree) {
  const scenario = numeroDeScenario;
  try {
    const etat = await appeler("POST", "/api/pas?nombre=" + nombre);
    if (scenario !== numeroDeScenario) {
      return true;  // réponse de l'ancien scénario : on l'ignore, ce n'est pas une erreur
    }
    // On n'efface pas le message ici : pendant la lecture, il disparaîtrait en 100 ms
    // (« Feu allumé », ou un refus du serveur, ne serait jamais lu).
    afficherEtat(etat, duree);
    return true;
  } catch (erreur) {
    afficherMessage(erreur.message);
    return false;
  }
}

// `numero` : la lecture à laquelle appartient cette boucle. Après une pause puis une
// relance, l'ancienne boucle (dont une demande était peut-être en cours) s'arrête seule.
async function boucleDeLecture(numero) {
  if (!enLecture || numero !== numeroDeLecture) {
    return;
  }
  // Au plus 10 demandes par seconde : aux grandes vitesses, chaque demande fait
  // plusieurs pas (× 60 : 6 pas toutes les 100 ms).
  const vitesse = Number(document.getElementById("vitesse").value);
  const nombre = Math.max(1, Math.round(vitesse / 10));
  const delai = 1000 * nombre / vitesse;
  const debut = performance.now();
  const reussi = await avancer(nombre, delai);
  if (numero !== numeroDeLecture) {
    return;  // une autre lecture a été lancée pendant la demande
  }
  if (!reussi) {
    pause();
    return;
  }
  // Le temps de la demande est déjà écoulé : on attend seulement le reste.
  const ecoule = performance.now() - debut;
  minuterie = setTimeout(boucleDeLecture, Math.max(0, delai - ecoule), numero);
}

function lancer() {
  afficherMessage("");
  enLecture = true;
  numeroDeLecture = numeroDeLecture + 1;
  activerLecture(true);
  boucleDeLecture(numeroDeLecture);
}

function pause() {
  enLecture = false;
  clearTimeout(minuterie);
  activerLecture(plan.nodes().length > 0);
}

function pasAPas() {
  pause();
  afficherMessage("");
  avancer(1, 300);
}

async function demarrer() {
  activerLecture(false);
  creerCalque(document.getElementById("agents"), plan);
  brancherInteractions();
  try {
    scenarios = await appeler("GET", "/api/scenarios");
  } catch (erreur) {
    afficherMessage(erreur.message);
    return;
  }
  const liste = document.getElementById("scenario");
  for (const scenario of scenarios) {
    const option = document.createElement("option");
    option.value = scenario.id;
    option.textContent = scenario.nom;
    liste.appendChild(option);
  }
  afficherDescription();

  // La police doit être chargée avant que Cytoscape écrive les libellés sur son canvas.
  await document.fonts.load("16px 'Atkinson Hyperlegible'");
  await document.fonts.load("bold 16px 'Atkinson Hyperlegible'");

  // Si un scénario tourne déjà (page rechargée), on le reprend où il en est.
  try {
    const etat = await appeler("GET", "/api/etat");
    liste.value = etat.scenario;
    afficherDescription();
    afficherNouveauScenario(etat);
  } catch (erreur) {
    afficherMessage("Choisir un scénario, puis « Charger ».");
  }
}

document.getElementById("scenario").addEventListener("change", afficherDescription);
document.getElementById("charger").addEventListener("click", charger);
document.getElementById("lancer").addEventListener("click", lancer);
document.getElementById("pause").addEventListener("click", pause);
document.getElementById("un-pas").addEventListener("click", pasAPas);
demarrer();
