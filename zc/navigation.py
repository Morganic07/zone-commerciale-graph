"""Graphe de navigation : le graphe orienté que les algorithmes de chemins parcourent.

À partir des nœuds et des arêtes (d'un centre ou de toute la zone), on construit une
liste d'adjacence : pour chaque nœud, la liste des arcs qui en partent. On y applique :

- le sens : une arête « bidirectionnel » donne deux arcs, une arête « unique » un seul,
  de `source` vers `cible` ;
- les blocages : un nœud ou une arête au statut « bloqué » est retiré ;
- le critère d'itinéraire, qui fixe le poids de chaque arc (PLAN.md § 3) :
    « court »    : poids = longueur ;
    « encombre » : poids = longueur × (1 + β × τ), la foule ralentit ;
    « pmr »      : poids = longueur, et seules les arêtes praticables en fauteuil restent.
"""

from dataclasses import dataclass

from zc.modele import Arete, Centre, Zone

CRITERES = ["court", "encombre", "pmr"]


@dataclass
class Arc:
    """Un arc du graphe de navigation : on peut aller de `depart` à `arrivee`."""

    depart: str
    arrivee: str
    poids: float
    arete: Arete  # l'arête d'origine (capacité, statut, etc.)


def poids(arete: Arete, critere: str, beta: float) -> float:
    """Poids d'une arête selon le critère d'itinéraire. Toujours positif si la longueur
    l'est, ce qui est nécessaire pour Dijkstra."""
    if critere == "encombre":
        return arete.longueur * (1 + beta * arete.taux)
    return arete.longueur


def construire(identifiants: list[str], aretes: list[Arete], bloques: set[str],
               critere: str, beta: float = 0.0) -> dict[str, list[Arc]]:
    """Construit la liste d'adjacence du graphe de navigation.

    `identifiants` : tous les nœuds du graphe ; `bloques` : ceux qu'il faut retirer.
    Complexité O(V + E) pour V nœuds et E arêtes.
    """
    if critere not in CRITERES:
        raise ValueError(f"critère « {critere} » inconnu, attendu parmi {CRITERES}")
    # Avec β < 0, la foule raccourcirait le trajet et les poids pourraient devenir
    # négatifs : Dijkstra donnerait alors des chemins faux.
    if beta < 0:
        raise ValueError(f"β doit être positif ou nul, reçu {beta}")

    graphe: dict[str, list[Arc]] = {}
    for identifiant in identifiants:
        if identifiant not in bloques:
            graphe[identifiant] = []

    for a in aretes:
        if a.statut == "bloqué":
            continue
        if critere == "pmr" and not a.pmr:
            continue
        if a.source not in graphe or a.cible not in graphe:
            continue  # une extrémité est bloquée
        p = poids(a, critere, beta)
        graphe[a.source].append(Arc(a.source, a.cible, p, a))
        if a.sens == "bidirectionnel":
            graphe[a.cible].append(Arc(a.cible, a.source, p, a))
    return graphe


def graphe_du_centre(centre: Centre, critere: str, beta: float = 0.0) -> dict[str, list[Arc]]:
    """Graphe de navigation d'un seul centre."""
    identifiants = []
    bloques = set()
    for n in centre.noeuds:
        identifiants.append(n.id)
        if n.statut == "bloqué":
            bloques.add(n.id)
    return construire(identifiants, centre.aretes, bloques, critere, beta)


def graphe_de_la_zone(zone: Zone, critere: str, beta: float = 0.0,
                      fermes: set[str] | None = None) -> dict[str, list[Arc]]:
    """Graphe de navigation de toute la zone : nœuds des centres, sources, couloirs et
    connexions. Les sources ne sont jamais bloquées. `fermes` : nœuds retirés en plus des
    nœuds bloqués (ceux d'un centre en feu, fermé aux visiteurs)."""
    identifiants = []
    bloques = set()
    if fermes is not None:
        for identifiant in fermes:
            bloques.add(identifiant)
    aretes = []
    for c in zone.centres:
        for n in c.centre.noeuds:
            identifiants.append(n.id)
            if n.statut == "bloqué":
                bloques.add(n.id)
        for a in c.centre.aretes:
            aretes.append(a)
    for s in zone.sources:
        identifiants.append(s.id)
    for a in zone.connexions:
        aretes.append(a)
    return construire(identifiants, aretes, bloques, critere, beta)
