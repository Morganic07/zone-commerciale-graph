// La page : choix du scénario, bandeau, et dialogue avec le serveur (serveur/app.py).

const plan = creerPlan(document.getElementById("graphe"));
let scenarios = [];

// Appelle le serveur ; en cas d'erreur, lève une Error avec le message du serveur.
async function appeler(methode, adresse) {
  let reponse;
  try {
    reponse = await fetch(adresse, {method: methode});
  } catch (erreur) {
    throw new Error("Le serveur ne répond pas : relancer « python -m serveur ».");
  }
  const contenu = await reponse.json();
  if (!reponse.ok) {
    throw new Error(contenu.detail);
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

async function charger() {
  const choisi = document.getElementById("scenario").value;
  try {
    const etat = await appeler("POST", "/api/scenarios/" + choisi);
    construirePlan(plan, etat);
    mettreAJourBandeau(etat);
    document.getElementById("un-pas").disabled = false;
    afficherMessage("");
  } catch (erreur) {
    afficherMessage(erreur.message);
  }
}

async function avancerDUnPas() {
  try {
    const etat = await appeler("POST", "/api/pas?nombre=1");
    mettreAJourPlan(plan, etat);
    mettreAJourBandeau(etat);
    afficherMessage("");
  } catch (erreur) {
    afficherMessage(erreur.message);
  }
}

async function demarrer() {
  document.getElementById("un-pas").disabled = true;
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
    construirePlan(plan, etat);
    mettreAJourBandeau(etat);
    document.getElementById("un-pas").disabled = false;
  } catch (erreur) {
    afficherMessage("Choisir un scénario, puis « Charger ».");
  }
}

document.getElementById("scenario").addEventListener("change", afficherDescription);
document.getElementById("charger").addEventListener("click", charger);
document.getElementById("un-pas").addEventListener("click", avancerDUnPas);
demarrer();
