// Visionneuse : demande le réseau au serveur et le dessine avec Cytoscape.
// Chaque station est une boîte (un « nœud composé ») qui contient ses nœuds.

// Mêmes couleurs que dans style.css.
const COULEURS = {
  encre: "#1F2933",
  encreDouce: "#52606D",
  trait: "#9AA5B1",
  point: "#7B8794",
  source: "#FACC15",
  bordSource: "#A16207",
  nonPmr: "#C2410C"
};

// Apparence du graphe : tous les nœuds sont des points gris, sans nom.
const STYLE = [
  {
    selector: "node",
    style: {"shape": "ellipse", "width": 14, "height": 14, "background-color": COULEURS.point}
  },
  {
    selector: ".station",
    style: {
      "label": "data(label)",
      "background-color": "#FFFFFF",
      "border-width": 1,
      "border-color": COULEURS.trait,
      "padding": 30,
      "text-valign": "top",
      "text-margin-y": -6,
      "color": COULEURS.encre,
      "font-size": 16,
      "font-weight": 600,
      "font-family": "system-ui, sans-serif"
    }
  },
  {
    // Les sas sont les nœuds sources : les visiteurs arrivent et repartent par eux.
    selector: ".source",
    style: {
      "width": 18,
      "height": 18,
      "background-color": COULEURS.source,
      "border-width": 2,
      "border-color": COULEURS.bordSource
    }
  },
  {
    selector: "edge",
    style: {"width": 2, "line-color": COULEURS.trait, "curve-style": "straight"}
  },
  {
    selector: ".tunnel",
    style: {"width": 5, "line-color": COULEURS.encreDouce}
  },
  {
    selector: ".non-pmr",
    style: {"line-style": "dashed", "line-color": COULEURS.nonPmr}
  },
  {
    // Élément écarté par la recherche : on le laisse visible, mais très pâle.
    selector: ".estompe",
    style: {"opacity": 0.12}
  },
  {
    // Nœud trouvé par son identifiant : cerclé de noir.
    selector: ".trouve",
    style: {"border-width": 3, "border-color": COULEURS.encre, "width": 22, "height": 22}
  }
];

// Le fichier du réseau, où sont décrits les tunnels.
const FICHIER_RESEAU = "donnees/reseau.json";

// Écrit « oui » ou « non » pour un booléen.
function ouiNon(valeur) {
  if (valeur) {
    return "oui";
  }
  return "non";
}

// Retire le préfixe de la station : « A:SERRE » devient « SERRE », comme dans le fichier.
function idDansLeFichier(idPrefixe, idStation) {
  return idPrefixe.substring(idStation.length + 1);
}

// Texte de l'infobulle d'un nœud : de quel nœud il s'agit, où le modifier, ses valeurs.
function decrireNoeud(noeud, station) {
  // Seul l'identifiant est affiché : c'est lui qu'on cherche dans le fichier.
  const titre = "Nœud " + idDansLeFichier(noeud.id, station.id);
  return titre + "\n"
    + "Fichier : donnees/" + station.fichier + "\n"
    + "Type : " + noeud.type + "\n"
    + "Capacité : " + noeud.capacite_max + " personnes\n"
    + "Capteur de fumée : " + ouiNon(noeud.capteur_fumee);
}

// Texte de l'infobulle d'une arête. Les tunnels gardent les identifiants préfixés,
// car c'est ainsi qu'ils sont écrits dans reseau.json.
function decrireArete(titre, fichier, arete) {
  let texte = titre + "\n"
    + "Fichier : " + fichier + "\n"
    + "Longueur : " + arete.longueur + " m\n";
  if (arete.largeur !== undefined) {
    texte = texte + "Largeur : " + arete.largeur + " m\n";
  }
  return texte
    + "Capacité : " + arete.capacite_max + " personnes par seconde\n"
    + "Accessible en fauteuil : " + ouiNon(arete.pmr);
}

// Transforme une arête du réseau en arête Cytoscape. Les classes choisissent son style.
function creerArete(arete, genre, infos) {
  let classes = genre;
  if (!arete.pmr) {
    classes = classes + " non-pmr";
  }
  return {
    data: {
      id: arete.source + " vers " + arete.cible,
      source: arete.source,
      target: arete.cible,
      infos: infos,
      pmr: arete.pmr
    },
    classes: classes
  };
}

// Construit la liste des éléments à dessiner : stations, nœuds, arêtes, tunnels.
function creerElements(reseau) {
  const elements = [];

  for (const station of reseau.stations) {
    elements.push({data: {id: station.id, label: "Station " + station.id}, classes: "station"});

    for (const noeud of station.noeuds) {
      // Les sas (type « sortie ») sont les nœuds sources : ils sont dessinés en jaune.
      let classe = "";
      if (noeud.type === "sortie") {
        classe = "source";
      }
      // La position d'un nœud est donnée dans le plan de sa station :
      // on la décale de la position de la station dans le réseau.
      // idFichier, type et capteur servent à la recherche.
      elements.push({
        data: {
          id: noeud.id,
          parent: station.id,
          infos: decrireNoeud(noeud, station),
          idFichier: idDansLeFichier(noeud.id, station.id),
          type: noeud.type,
          capteur: noeud.capteur_fumee
        },
        position: {x: station.x + noeud.x, y: station.y + noeud.y},
        classes: classe
      });
    }

    for (const arete of station.aretes) {
      const titre = "Arête " + idDansLeFichier(arete.source, station.id)
        + " – " + idDansLeFichier(arete.cible, station.id);
      const infos = decrireArete(titre, "donnees/" + station.fichier, arete);
      elements.push(creerArete(arete, "arete", infos));
    }
  }

  for (const tunnel of reseau.connexions) {
    const titre = "Tunnel " + tunnel.source + " – " + tunnel.cible;
    elements.push(creerArete(tunnel, "tunnel", decrireArete(titre, FICHIER_RESEAU, tunnel)));
  }

  return elements;
}

// Affiche l'infobulle de l'élément survolé, à côté de la souris.
function afficherInfobulle(evenement) {
  const element = evenement.target;
  // Les boîtes des stations n'ont pas d'infobulle : seuls les nœuds et les arêtes en ont.
  if (element.hasClass("station")) {
    return;
  }
  const bulle = document.getElementById("infobulle");
  bulle.textContent = element.data("infos");
  bulle.style.left = (evenement.renderedPosition.x + 16) + "px";
  bulle.style.top = (evenement.renderedPosition.y + 16) + "px";
  bulle.hidden = false;
}

function cacherInfobulle() {
  document.getElementById("infobulle").hidden = true;
}

// Vrai si le nœud correspond à tous les critères de recherche remplis.
// Un critère vide (« tous », « peu importe ») laisse passer tous les nœuds.
function noeudCorrespond(noeud, idCherche, type, capteur) {
  if (idCherche !== "" && noeud.data("idFichier").toUpperCase() !== idCherche) {
    return false;
  }
  if (type !== "" && noeud.data("type") !== type) {
    return false;
  }
  if (capteur === "avec" && !noeud.data("capteur")) {
    return false;
  }
  if (capteur === "sans" && noeud.data("capteur")) {
    return false;
  }
  return true;
}

// Vrai si l'arête correspond au critère « accessible en fauteuil ».
function areteCorrespond(arete, pmr) {
  if (pmr === "oui" && !arete.data("pmr")) {
    return false;
  }
  if (pmr === "non" && arete.data("pmr")) {
    return false;
  }
  return true;
}

// Estompe tout ce qui ne correspond pas à la recherche. Les boîtes des stations restent.
function appliquerFiltres() {
  const idCherche = document.getElementById("filtre-id").value.trim().toUpperCase();
  const type = document.getElementById("filtre-type").value;
  const capteur = document.getElementById("filtre-capteur").value;
  const pmr = document.getElementById("filtre-pmr").value;
  const filtreSurLesNoeuds = idCherche !== "" || type !== "" || capteur !== "";

  let nombreTrouves = 0;
  let dernierTrouve = null;
  for (const noeud of cy.nodes()) {
    if (noeud.hasClass("station")) {
      continue;
    }
    noeud.removeClass("trouve");
    if (noeudCorrespond(noeud, idCherche, type, capteur)) {
      noeud.removeClass("estompe");
      nombreTrouves = nombreTrouves + 1;
      dernierTrouve = noeud;
    } else {
      noeud.addClass("estompe");
    }
  }

  for (const arete of cy.edges()) {
    let visible = areteCorrespond(arete, pmr);
    // Quand on cherche des nœuds, une arête n'est montrée que si ses deux bouts le sont.
    if (filtreSurLesNoeuds) {
      if (arete.source().hasClass("estompe") || arete.target().hasClass("estompe")) {
        visible = false;
      }
    }
    if (visible) {
      arete.removeClass("estompe");
    } else {
      arete.addClass("estompe");
    }
  }

  // Message sous la recherche, et zoom sur le nœud cherché par son identifiant.
  let message = "";
  if (idCherche !== "" && nombreTrouves === 0) {
    message = "Aucun nœud " + idCherche + " ne correspond.";
  } else if (idCherche !== "") {
    dernierTrouve.addClass("trouve");
    // On centre la vue sur le nœud, avec un zoom modéré pour garder sa station visible.
    cy.zoom(1.2);
    cy.center(dernierTrouve);
  } else if (filtreSurLesNoeuds && nombreTrouves === 0) {
    message = "Aucun nœud ne correspond.";
  } else if (filtreSurLesNoeuds && nombreTrouves === 1) {
    message = "1 nœud correspond.";
  } else if (filtreSurLesNoeuds) {
    message = nombreTrouves + " nœuds correspondent.";
  }
  document.getElementById("message-filtre").textContent = message;
}

function empecherEnvoi(evenement) {
  evenement.preventDefault();
}

// « Tout afficher » vide les champs (bouton de type reset), puis on réapplique.
function toutAfficher() {
  // Le formulaire se vide juste après le clic : on attend qu'il l'ait fait.
  setTimeout(appliquerFiltres, 0);
  // Et on revient à la vue d'ensemble du réseau.
  cy.fit(undefined, 40);
}


// Remplace tout le dessin par le réseau reçu, puis cadre la vue.
function dessiner(cy, reseau) {
  cy.elements().remove();
  cy.add(creerElements(reseau));
  cy.fit(undefined, 40);
  // Après un rechargement, la recherche en cours s'applique au nouveau dessin.
  appliquerFiltres();
}

const cy = cytoscape({
  container: document.getElementById("graphe"),
  style: STYLE,
  layout: {name: "preset"},
  minZoom: 0.2,
  maxZoom: 4
});

async function chargerReseau() {
  const reponse = await fetch("/api/reseau");
  dessiner(cy, await reponse.json());
}

async function rechargerReseau() {
  const reponse = await fetch("/api/recharger", {method: "POST"});
  dessiner(cy, await reponse.json());
}

// L'infobulle suit la souris tant qu'elle est sur un nœud ou une arête.
cy.on("mouseover mousemove", "node, edge", afficherInfobulle);
cy.on("mouseout", "node, edge", cacherInfobulle);
// Cytoscape ne prévient pas quand la souris quitte le graphe directement depuis un élément.
document.getElementById("graphe").addEventListener("mouseleave", cacherInfobulle);

document.getElementById("recharger").addEventListener("click", rechargerReseau);

// La recherche s'applique dès qu'on tape ou qu'on change un critère.
document.getElementById("filtre-id").addEventListener("input", appliquerFiltres);
document.getElementById("filtre-type").addEventListener("change", appliquerFiltres);
document.getElementById("filtre-capteur").addEventListener("change", appliquerFiltres);
document.getElementById("filtre-pmr").addEventListener("change", appliquerFiltres);
document.getElementById("tout-afficher").addEventListener("click", toutAfficher);
// Entrée dans le champ de recherche ne doit pas recharger la page.
document.getElementById("filtres").addEventListener("submit", empecherEnvoi);
chargerReseau();
