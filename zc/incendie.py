"""Incendie : diffusion de la fumée dans un centre (consigne § 3, PLAN.md § 5).

Règle de diffusion de la consigne, appliquée à chaque pas à tous les nœuds du centre :

    f_v(t+1) = min(100, f_v(t) + α × Σ_{u voisin de v} (f_u(t) − f_v(t))⁺ + s_v(t))

- (x)⁺ = max(x, 0) : la fumée ne passe que d'un nœud plus enfumé vers un nœud moins
  enfumé ; elle ne diminue donc jamais.
- s_v(t) est le terme source : non nul seulement pour les nœuds en feu (les foyers).
- Les voisins sont pris sans tenir compte du sens des couloirs : la fumée ignore les
  sens uniques.
- La mise à jour est synchrone : toutes les nouvelles valeurs sont calculées à partir
  des valeurs du pas précédent, sinon l'ordre de parcours changerait le résultat.

La fumée d'une arête n'est pas stockée : c'est le maximum de ses deux extrémités (un
couloir est aussi dangereux que son bout le plus enfumé).
"""

from zc.modele import Arete, Centre

FUMEE_MAX = 100.0


def voisins_non_orientes(identifiants: list[str], aretes: list[Arete]) -> dict[str, list[str]]:
    """Pour chaque nœud, ses voisins (chacun une seule fois, même s'il y a deux couloirs
    entre eux), sans tenir compte du sens. Complexité O(V + E)."""
    voisins: dict[str, list[str]] = {}
    for identifiant in identifiants:
        voisins[identifiant] = []
    for a in aretes:
        if a.cible not in voisins[a.source]:
            voisins[a.source].append(a.cible)
        if a.source not in voisins[a.cible]:
            voisins[a.cible].append(a.source)
    return voisins


def diffuser(fumee: dict[str, float], voisins: dict[str, list[str]], alpha: float,
             sources: dict[str, float]) -> dict[str, float]:
    """Un pas de la règle de diffusion. `fumee` : niveaux au pas t ; `sources` : terme
    source s_v des nœuds en feu. Renvoie les niveaux au pas t + 1, sans modifier
    `fumee`. Complexité O(V + E)."""
    nouvelle = {}
    for v in fumee:
        apport = 0.0
        for u in voisins[v]:
            difference = fumee[u] - fumee[v]
            if difference > 0:
                apport += difference
        source = sources.get(v, 0.0)
        nouvelle[v] = min(FUMEE_MAX, fumee[v] + alpha * apport + source)
    return nouvelle


def fumee_arete(arete: Arete, fumee: dict[str, float]) -> float:
    """Fumée d'une arête : le maximum de ses deux extrémités."""
    return max(fumee[arete.source], fumee[arete.cible])


def niveau_reel(fumee: float, theta1: float, theta2: float) -> str:
    """Statut que mérite un niveau de fumée : « bloqué » au-delà de θ₂, « enfumé »
    au-delà de θ₁, « libre » sinon."""
    if fumee >= theta2:
        return "bloqué"
    if fumee >= theta1:
        return "enfumé"
    return "libre"


# Ordre de gravité, pour prendre le pire de deux statuts.
GRAVITE = {"libre": 0, "sortie": 0, "enfumé": 1, "bloqué": 2}


def pire(statut1: str, statut2: str) -> str:
    """Le plus grave de deux statuts (le premier en cas d'égalité)."""
    if GRAVITE[statut2] > GRAVITE[statut1]:
        return statut2
    return statut1


class Incendie:
    """Un incendie dans un centre : un ou plusieurs foyers allumés à t = 0, la fumée qui
    se diffuse, et sa détection.

    On distingue l'état réel et le statut connu (PLAN.md § 5.2) :
    - l'état réel est `niveau_fumee`, la fumée qui agit sur les gens ;
    - le statut connu est `statut`, ce que l'alarme sait du nœud ; c'est lui que lit le
      graphe de navigation pour calculer les chemins.
    Un nœud passe « enfumé » au-delà de θ₁ et « bloqué » au-delà de θ₂ : tout de suite
    s'il a un capteur, δ pas plus tard sinon. Le statut connu d'un couloir est le pire
    des statuts connus de ses deux extrémités.
    """

    def __init__(self, centre: Centre, alpha: float, foyers: dict[str, float],
                 theta1: float = 30.0, theta2: float = 70.0, delai: int = 5) -> None:
        """`alpha` : coefficient de diffusion, dans ]0, 1[ (consigne) ; `foyers` : pour
        chaque nœud en feu, la fumée qu'il produit à chaque pas (terme source s_v) ;
        `theta1` < `theta2` : seuils « enfumé » et « bloqué » ; `delai` : retard de
        détection δ, en pas, des nœuds sans capteur. Les valeurs par défaut sont à
        justifier dans le rapport."""
        if not 0 < alpha < 1:
            raise ValueError(f"α doit être dans ]0, 1[, reçu {alpha}")
        if not 0 < theta1 < theta2 <= FUMEE_MAX:
            raise ValueError(f"il faut 0 < θ₁ < θ₂ ≤ 100, reçu θ₁ = {theta1}, θ₂ = {theta2}")
        if delai < 0:
            raise ValueError(f"le retard δ doit être positif ou nul, reçu {delai}")
        identifiants = []
        for n in centre.noeuds:
            identifiants.append(n.id)
        for foyer in foyers:
            if foyer not in identifiants:
                raise ValueError(f"le foyer « {foyer} » n'est pas un nœud du centre")
        self.centre = centre
        self.alpha = alpha
        self.foyers = foyers
        self.theta1 = theta1
        self.theta2 = theta2
        self.delai = delai
        self.voisins = voisins_non_orientes(identifiants, centre.aretes)
        self.t = 0  # nombre de pas écoulés depuis le départ du feu
        # Pour chaque nœud, le pas où sa fumée réelle a franchi chaque seuil.
        self.franchissements: dict[str, dict[str, int]] = {}
        for identifiant in identifiants:
            self.franchissements[identifiant] = {}
        # Statuts d'origine (« sortie », « libre », ou un passage déjà fermé). L'incendie
        # ne fait que les aggraver : il ne rouvre jamais un passage fermé au départ.
        self.statut_initial: dict[str, str] = {}
        for n in centre.noeuds:
            self.statut_initial[n.id] = n.statut
        self.statut_initial_aretes: list[str] = []
        for a in centre.aretes:
            self.statut_initial_aretes.append(a.statut)

    def niveaux(self) -> dict[str, float]:
        """Niveau de fumée actuel de chaque nœud."""
        fumee = {}
        for n in self.centre.noeuds:
            fumee[n.id] = n.niveau_fumee
        return fumee

    def pas(self) -> None:
        """Un pas de diffusion (état réel), puis la détection (statuts connus)."""
        self.t += 1
        nouvelle = diffuser(self.niveaux(), self.voisins, self.alpha, self.foyers)
        for n in self.centre.noeuds:
            n.niveau_fumee = nouvelle[n.id]
        self.detecter()

    def detecter(self) -> None:
        """Met à jour le statut connu des nœuds, puis celui des couloirs."""
        for n in self.centre.noeuds:
            # On note le pas où la fumée réelle franchit chaque seuil (une seule fois :
            # la fumée ne baisse jamais).
            reel = niveau_reel(n.niveau_fumee, self.theta1, self.theta2)
            vus = self.franchissements[n.id]
            if reel in ("enfumé", "bloqué") and "enfumé" not in vus:
                vus["enfumé"] = self.t
            if reel == "bloqué" and "bloqué" not in vus:
                vus["bloqué"] = self.t

            retard = 0
            if not n.capteur_fumee:
                retard = self.delai
            detecte = "libre"
            if "enfumé" in vus and self.t >= vus["enfumé"] + retard:
                detecte = "enfumé"
            if "bloqué" in vus and self.t >= vus["bloqué"] + retard:
                detecte = "bloqué"
            n.statut = pire(self.statut_initial[n.id], detecte)

        statuts = {}
        for n in self.centre.noeuds:
            statuts[n.id] = n.statut
        for i in range(len(self.centre.aretes)):
            a = self.centre.aretes[i]
            statut = pire(statuts[a.source], statuts[a.cible])
            statut = pire(self.statut_initial_aretes[i], statut)
            if statut == "sortie":
                statut = "libre"  # « sortie » n'est pas un statut d'arête
            a.statut = statut
