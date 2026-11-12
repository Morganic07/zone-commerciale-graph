"""Conversion entre le format JSON imposé d'un centre (consigne § 2.3) et le modèle.

Python pur, sans accès au disque : la lecture des fichiers est dans `chargement.py`.
`depuis_dict` valide tout ce qu'il lit et lève ErreurFormat avec un message qui nomme
l'élément fautif ; `vers_dict` réécrit les champs dans l'ordre du format imposé, sans
ajouter les champs facultatifs absents, pour qu'un fichier se relise à l'identique.
"""

from zc.modele import (
    FUMEE_MAX,
    FUMEE_MIN,
    SENS,
    STATUTS_ARETE,
    STATUTS_NOEUD,
    TYPES,
    Arete,
    Centre,
    Noeud,
    Nombre,
)

CHAMPS_NOEUD = ("id", "type", "capacite_max", "occupation", "capteur_fumee", "niveau_fumee",
                "statut")
FACULTATIFS_NOEUD = ("x", "y", "nom")
CHAMPS_ARETE = ("source", "cible", "capacite_max", "longueur", "statut", "sens", "pmr")
FACULTATIFS_ARETE = ("largeur",)


class ErreurFormat(ValueError):
    """Fichier de centre invalide ; le message nomme l'élément et le champ fautifs."""


# --- lecture de champs typés ------------------------------------------------------------

def _objet(valeur: object, ou: str) -> dict[str, object]:
    if not isinstance(valeur, dict):
        raise ErreurFormat(f"{ou} : objet JSON attendu")
    return valeur


def _champs(d: dict[str, object], requis: tuple[str, ...], facultatifs: tuple[str, ...],
            ou: str) -> None:
    manquants = [c for c in requis if c not in d]
    if manquants:
        raise ErreurFormat(f"{ou} : champs manquants : {', '.join(manquants)}")
    inconnus = sorted(set(d) - set(requis) - set(facultatifs))
    if inconnus:
        raise ErreurFormat(f"{ou} : champs inconnus : {', '.join(inconnus)}")


def _texte(d: dict[str, object], cle: str, ou: str) -> str:
    v = d[cle]
    if not isinstance(v, str) or not v:
        raise ErreurFormat(f"{ou} : « {cle} » doit être une chaîne non vide")
    return v


def _booleen(d: dict[str, object], cle: str, ou: str) -> bool:
    v = d[cle]
    if not isinstance(v, bool):
        raise ErreurFormat(f"{ou} : « {cle} » doit être true ou false")
    return v


def _entier(d: dict[str, object], cle: str, ou: str) -> int:
    v = d[cle]
    # bool est un sous-type d'int : true passerait pour 1 sans ce test.
    if isinstance(v, bool) or not isinstance(v, int):
        raise ErreurFormat(f"{ou} : « {cle} » doit être un entier")
    return v


def _nombre(d: dict[str, object], cle: str, ou: str) -> Nombre:
    v = d[cle]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (
        float("inf"), float("-inf")
    ):
        raise ErreurFormat(f"{ou} : « {cle} » doit être un nombre fini")
    return v


def _dans(valeur: str, ensemble: frozenset[str], cle: str, ou: str) -> str:
    if valeur not in ensemble:
        raise ErreurFormat(f"{ou} : « {cle} » vaut « {valeur} », attendu parmi "
                           f"{', '.join(sorted(ensemble))}")
    return valeur


# --- nœuds et arêtes --------------------------------------------------------------------

def _noeud(brut: object, rang: int) -> Noeud:
    d = _objet(brut, f"noeuds[{rang}]")
    ou = f"nœud « {d['id']} »" if isinstance(d.get("id"), str) else f"noeuds[{rang}]"
    _champs(d, CHAMPS_NOEUD, FACULTATIFS_NOEUD, ou)
    noeud = Noeud(
        id=_texte(d, "id", ou),
        type=_dans(_texte(d, "type", ou), TYPES, "type", ou),
        capacite_max=_entier(d, "capacite_max", ou),
        occupation=_entier(d, "occupation", ou),
        capteur_fumee=_booleen(d, "capteur_fumee", ou),
        niveau_fumee=_nombre(d, "niveau_fumee", ou),
        statut=_dans(_texte(d, "statut", ou), STATUTS_NOEUD, "statut", ou),
        x=_nombre(d, "x", ou) if "x" in d else None,
        y=_nombre(d, "y", ou) if "y" in d else None,
        nom=_texte(d, "nom", ou) if "nom" in d else None,
    )
    if noeud.capacite_max <= 0:
        raise ErreurFormat(f"{ou} : capacite_max doit être strictement positive")
    if not 0 <= noeud.occupation <= noeud.capacite_max:
        raise ErreurFormat(f"{ou} : occupation ({noeud.occupation}) hors de "
                           f"[0, capacite_max = {noeud.capacite_max}]")
    if not FUMEE_MIN <= noeud.niveau_fumee <= FUMEE_MAX:
        raise ErreurFormat(f"{ou} : niveau_fumee ({noeud.niveau_fumee}) hors de "
                           f"[{FUMEE_MIN}, {FUMEE_MAX}]")
    # « sortie » est un statut réservé aux nœuds de type sortie ; une sortie peut en
    # revanche devenir enfumée ou bloquée pendant un incendie.
    if noeud.statut == "sortie" and noeud.type != "sortie":
        raise ErreurFormat(f"{ou} : le statut « sortie » est réservé aux nœuds de type sortie")
    return noeud


def _arete(brut: object, rang: int, ids: set[str]) -> Arete:
    ou = f"aretes[{rang}]"
    d = _objet(brut, ou)
    _champs(d, CHAMPS_ARETE, FACULTATIFS_ARETE, ou)
    arete = Arete(
        source=_texte(d, "source", ou),
        cible=_texte(d, "cible", ou),
        capacite_max=_nombre(d, "capacite_max", ou),
        longueur=_nombre(d, "longueur", ou),
        statut=_dans(_texte(d, "statut", ou), STATUTS_ARETE, "statut", ou),
        sens=_dans(_texte(d, "sens", ou), SENS, "sens", ou),
        pmr=_booleen(d, "pmr", ou),
        largeur=_nombre(d, "largeur", ou) if "largeur" in d else None,
    )
    ou = f"arête {arete.source} → {arete.cible}"
    for extremite in (arete.source, arete.cible):
        if extremite not in ids:
            raise ErreurFormat(f"{ou} : extrémité « {extremite} » inexistante")
    if arete.source == arete.cible:
        raise ErreurFormat(f"{ou} : une arête ne peut pas relier un nœud à lui-même")
    for cle in ("capacite_max", "longueur", "largeur"):
        valeur = getattr(arete, cle)
        if valeur is not None and valeur <= 0:
            raise ErreurFormat(f"{ou} : {cle} doit être strictement positive")
    return arete


def depuis_dict(donnees: object) -> Centre:
    """Valide le contenu décodé d'un fichier de centre et construit le modèle.

    Règles : champs imposés présents et sans champ inconnu ; identifiants de nœuds
    uniques ; extrémités d'arêtes existantes et distinctes ; type, statut et sens dans
    leurs ensembles ; 0 ≤ occupation ≤ capacite_max ; niveau_fumee dans [0, 100] ;
    capacités et longueurs strictement positives. Complexité O(V + E).
    """
    racine = _objet(donnees, "centre")
    _champs(racine, ("noeuds", "aretes"), (), "centre")
    noeuds_bruts, aretes_brutes = racine["noeuds"], racine["aretes"]
    if not isinstance(noeuds_bruts, list) or not isinstance(aretes_brutes, list):
        raise ErreurFormat("centre : « noeuds » et « aretes » doivent être des listes")
    noeuds = [_noeud(b, i) for i, b in enumerate(noeuds_bruts)]
    ids: set[str] = set()
    for n in noeuds:
        if n.id in ids:
            raise ErreurFormat(f"identifiant de nœud en double : « {n.id} »")
        ids.add(n.id)
    aretes = [_arete(b, i, ids) for i, b in enumerate(aretes_brutes)]
    return Centre(noeuds=noeuds, aretes=aretes)


def vers_dict(centre: Centre) -> dict[str, object]:
    """Réécrit un centre au format imposé, champs dans l'ordre de la consigne, champs
    facultatifs seulement s'ils sont renseignés."""
    noeuds: list[dict[str, object]] = []
    for n in centre.noeuds:
        d: dict[str, object] = {c: getattr(n, c) for c in CHAMPS_NOEUD}
        d.update({c: getattr(n, c) for c in FACULTATIFS_NOEUD if getattr(n, c) is not None})
        noeuds.append(d)
    aretes: list[dict[str, object]] = []
    for a in centre.aretes:
        d = {c: getattr(a, c) for c in CHAMPS_ARETE}
        d.update({c: getattr(a, c) for c in FACULTATIFS_ARETE if getattr(a, c) is not None})
        aretes.append(d)
    return {"noeuds": noeuds, "aretes": aretes}
