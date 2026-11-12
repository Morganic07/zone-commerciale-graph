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


class Incendie:
    """Un incendie dans un centre : un ou plusieurs foyers allumés à t = 0, et la fumée
    qui se diffuse à chaque appel de `pas()` dans le champ `niveau_fumee` des nœuds."""

    def __init__(self, centre: Centre, alpha: float, foyers: dict[str, float]) -> None:
        """`alpha` : coefficient de diffusion, dans ]0, 1[ (consigne) ; `foyers` : pour
        chaque nœud en feu, la fumée qu'il produit à chaque pas (terme source s_v)."""
        if not 0 < alpha < 1:
            raise ValueError(f"α doit être dans ]0, 1[, reçu {alpha}")
        identifiants = []
        for n in centre.noeuds:
            identifiants.append(n.id)
        for foyer in foyers:
            if foyer not in identifiants:
                raise ValueError(f"le foyer « {foyer} » n'est pas un nœud du centre")
        self.centre = centre
        self.alpha = alpha
        self.foyers = foyers
        self.voisins = voisins_non_orientes(identifiants, centre.aretes)

    def niveaux(self) -> dict[str, float]:
        """Niveau de fumée actuel de chaque nœud."""
        fumee = {}
        for n in self.centre.noeuds:
            fumee[n.id] = n.niveau_fumee
        return fumee

    def pas(self) -> None:
        """Un pas de diffusion, écrit dans `niveau_fumee` de chaque nœud du centre."""
        nouvelle = diffuser(self.niveaux(), self.voisins, self.alpha, self.foyers)
        for n in self.centre.noeuds:
            n.niveau_fumee = nouvelle[n.id]
