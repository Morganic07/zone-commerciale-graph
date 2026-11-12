// Interactions avec la simulation : réglages, feu au clic, tracé d'un itinéraire.
// Les fonctions `appeler`, `afficherEtat`, `afficherMessage` et l'objet `plan` sont
// dans app.js.

// --- Réglages -------------------------------------------------------------------------
// Chaque champ porte la classe « reglage » et a pour id le nom du réglage côté serveur.
// Un changement est envoyé tout de suite ; si le serveur le refuse, le champ reprend la
// valeur en vigueur et le message dit quoi corriger.

function remplirReglages(etat) {
  for (const champ of document.querySelectorAll(".reglage")) {
    champ.value = etat.reglages[champ.id];
  }
}

async function changerReglage(evenement) {
  const champ = evenement.target;
  const corps = {};
  if (champ.value === "") {
    // Un champ vidé vaudrait 0 sans prévenir : on le refuse.
    afficherMessage(champ.dataset.aide);
    reafficherReglages();
    return;
  }
  if (champ.type === "number") {
    corps[champ.id] = Number(champ.value);
  } else {
    corps[champ.id] = champ.value;
  }
  try {
    const etat = await appeler("PUT", "/api/reglages", corps);
    remplirReglages(etat);
    afficherMessage("");
  } catch (erreur) {
    if (erreur.message === VALEUR_REFUSEE) {
      afficherMessage(champ.dataset.aide);
    } else {
      afficherMessage(erreur.message);
    }
    reafficherReglages();
  }
}

// Réaffiche les réglages en vigueur, le champ refusé compris.
async function reafficherReglages() {
  try {
    remplirReglages(await appeler("GET", "/api/etat"));
  } catch (erreur) {
    // Pas de scénario ou serveur arrêté : le message affiché le dit déjà.
  }
}

// --- Feu au clic ----------------------------------------------------------------------

function basculerModeFeu() {
  const bouton = document.getElementById("mode-feu");
  if (bouton.getAttribute("aria-pressed") === "true") {
    bouton.setAttribute("aria-pressed", "false");
    afficherMessage("");
  } else {
    bouton.setAttribute("aria-pressed", "true");
    afficherMessage("Déclencher un feu : cliquer sur un nœud d'un centre.");
  }
}

async function cliquerSurUnNoeud(evenement) {
  const bouton = document.getElementById("mode-feu");
  if (bouton.getAttribute("aria-pressed") !== "true") {
    return;
  }
  const noeud = evenement.target;
  if (noeud.hasClass("centre") || noeud.hasClass("source")) {
    afficherMessage("Le feu ne prend que dans un centre : cliquer sur un magasin, "
      + "un carrefour, un sanitaire ou une sortie.");
    return;
  }
  bouton.setAttribute("aria-pressed", "false");
  try {
    const etat = await appeler("POST", "/api/feu", {noeud: noeud.id()});
    afficherEtat(etat, 0);
    afficherMessage("Feu allumé : " + noeud.data("libelle") + ".");
  } catch (erreur) {
    afficherMessage(erreur.message);
  }
}

// --- Itinéraire -----------------------------------------------------------------------

// Remplit une liste déroulante ; `choix` : liste de [valeur, texte].
function remplirListe(liste, choix) {
  liste.innerHTML = "";
  for (const paire of choix) {
    const option = document.createElement("option");
    option.value = paire[0];
    option.textContent = paire[1];
    liste.appendChild(option);
  }
}

// Noeuds du dernier scénario chargé, pour proposer les magasins du centre choisi.
let noeudsDuScenario = [];

function remplirItineraire(etat) {
  noeudsDuScenario = etat.noeuds;
  const departs = [];
  for (const source of etat.sources) {
    departs.push([source.id, NOMS_SOURCES[source.type] + " " + source.id]);
  }
  remplirListe(document.getElementById("depart"), departs);

  const vus = [];
  const centres = [];
  for (const noeud of etat.noeuds) {
    if (!vus.includes(noeud.centre)) {
      vus.push(noeud.centre);
      centres.push([noeud.centre, "Centre " + noeud.centre]);
    }
  }
  remplirListe(document.getElementById("centre"), centres);
  remplirMagasins();
  effacer();
}

// Les magasins du centre choisi ; l'identifiant attendu par le serveur est sans le
// préfixe du centre (« M4 » pour « A:M4 »).
function remplirMagasins() {
  const centre = document.getElementById("centre").value;
  const magasins = [["", "Aucun : s'arrêter à l'entrée"]];
  for (const noeud of noeudsDuScenario) {
    if (noeud.centre === centre && noeud.type === "magasin") {
      const court = noeud.id.split(":")[1];
      let nom = noeud.nom;
      if (nom === null) {
        nom = court;
      }
      magasins.push([court, nom]);
    }
  }
  remplirListe(document.getElementById("magasin"), magasins);
}

const UNITES_CRITERE = {
  court: "m",
  encombre: "m pondérés par la foule",
  pmr: "m, praticables en fauteuil",
};

async function tracer() {
  const critere = document.getElementById("critere").value;
  let adresse = "/api/itineraire?source=" + document.getElementById("depart").value
    + "&centre=" + document.getElementById("centre").value + "&critere=" + critere;
  const magasin = document.getElementById("magasin").value;
  if (magasin !== "") {
    adresse = adresse + "&magasin=" + magasin;
  }
  const resultat = document.getElementById("resultat-itineraire");
  try {
    const itineraire = await appeler("GET", adresse);
    if (itineraire.cout === null) {
      effacerItineraire(plan);
      resultat.textContent = "Aucun itinéraire possible : passages bloqués ou sens interdits.";
      return;
    }
    tracerItineraire(plan, itineraire.chemin, itineraire.aretes);
    resultat.textContent = "Coût : " + itineraire.cout + " " + UNITES_CRITERE[critere]
      + ", en " + itineraire.aretes.length + " couloirs.";
    afficherMessage("");
  } catch (erreur) {
    afficherMessage(erreur.message);
  }
}

function effacer() {
  effacerItineraire(plan);
  document.getElementById("resultat-itineraire").textContent = "";
}

// Appelé une fois, au démarrage de la page.
function brancherInteractions() {
  for (const champ of document.querySelectorAll(".reglage")) {
    champ.addEventListener("change", changerReglage);
  }
  document.getElementById("mode-feu").addEventListener("click", basculerModeFeu);
  plan.on("tap", "node", cliquerSurUnNoeud);
  document.getElementById("centre").addEventListener("change", remplirMagasins);
  document.getElementById("tracer").addEventListener("click", tracer);
  document.getElementById("effacer").addEventListener("click", effacer);
}
