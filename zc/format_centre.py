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
)
from zc.validation import (
    ErreurFormat,
    booleen,
    champs,
    dans,
    entier,
    liste,
    nombre,
    nombre_facultatif,
    objet,
    texte,
)

__all__ = ["ErreurFormat", "arete_depuis_dict", "depuis_dict", "vers_dict"]

CHAMPS_NOEUD = ("id", "type", "capacite_max", "occupation", "capteur_fumee", "niveau_fumee",
                "statut")
FACULTATIFS_NOEUD = ("x", "y", "nom")
CHAMPS_ARETE = ("source", "cible", "capacite_max", "longueur", "statut", "sens", "pmr")
FACULTATIFS_ARETE = ("largeur",)


def _noeud(brut: object, rang: int) -> Noeud:
    d = objet(brut, f"noeuds[{rang}]")
    ou = f"nœud « {d['id']} »" if isinstance(d.get("id"), str) else f"noeuds[{rang}]"
    champs(d, CHAMPS_NOEUD, FACULTATIFS_NOEUD, ou)
    noeud = Noeud(
        id=texte(d, "id", ou),
        type=dans(texte(d, "type", ou), TYPES, "type", ou),
        capacite_max=entier(d, "capacite_max", ou),
        occupation=entier(d, "occupation", ou),
        capteur_fumee=booleen(d, "capteur_fumee", ou),
        niveau_fumee=nombre(d, "niveau_fumee", ou),
        statut=dans(texte(d, "statut", ou), STATUTS_NOEUD, "statut", ou),
        x=nombre_facultatif(d, "x", ou),
        y=nombre_facultatif(d, "y", ou),
        nom=texte(d, "nom", ou) if "nom" in d else None,
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


def arete_depuis_dict(brut: object, ou: str, extremites: set[str]) -> Arete:
    """Lit et valide une arête (couloir d'un centre ou connexion de la zone) dont les
    deux extrémités doivent appartenir à `extremites`, et être distinctes."""
    d = objet(brut, ou)
    champs(d, CHAMPS_ARETE, FACULTATIFS_ARETE, ou)
    arete = Arete(
        source=texte(d, "source", ou),
        cible=texte(d, "cible", ou),
        capacite_max=nombre(d, "capacite_max", ou),
        longueur=nombre(d, "longueur", ou),
        statut=dans(texte(d, "statut", ou), STATUTS_ARETE, "statut", ou),
        sens=dans(texte(d, "sens", ou), SENS, "sens", ou),
        pmr=booleen(d, "pmr", ou),
        largeur=nombre_facultatif(d, "largeur", ou),
    )
    ou = f"{ou} ({arete.source} → {arete.cible})"
    for extremite in (arete.source, arete.cible):
        if extremite not in extremites:
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
    racine = objet(donnees, "centre")
    champs(racine, ("noeuds", "aretes"), (), "centre")
    noeuds = [_noeud(b, i) for i, b in enumerate(liste(racine["noeuds"], "centre.noeuds"))]
    ids: set[str] = set()
    for n in noeuds:
        if n.id in ids:
            raise ErreurFormat(f"identifiant de nœud en double : « {n.id} »")
        ids.add(n.id)
    aretes = [arete_depuis_dict(b, f"aretes[{i}]", ids)
              for i, b in enumerate(liste(racine["aretes"], "centre.aretes"))]
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
