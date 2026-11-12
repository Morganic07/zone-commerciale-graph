"""Lecture et écriture d'un centre au format JSON imposé (consigne § 2.3).

Ce module ne touche pas au disque : il travaille sur les données déjà lues
(dictionnaires Python). La lecture des fichiers est dans `chargement.py`.
"""

from typing import Any

from zc.modele import (
    SENS,
    STATUTS_ARETE,
    STATUTS_NOEUD,
    TYPES,
    Arete,
    Centre,
    ErreurFormat,
    Noeud,
)


def verifier_champs(d: dict[str, Any], champs: list[str], ou: str) -> None:
    """Vérifie que tous les champs obligatoires sont présents."""
    for champ in champs:
        if champ not in d:
            raise ErreurFormat(f"{ou} : champ « {champ} » manquant")


def noeud_depuis_dict(d: dict[str, Any]) -> Noeud:
    """Crée un nœud à partir de son dictionnaire, en vérifiant ses valeurs."""
    ou = f"nœud « {d.get('id')} »"
    verifier_champs(d, ["id", "type", "capacite_max", "occupation", "capteur_fumee",
                        "niveau_fumee", "statut"], ou)
    noeud = Noeud(
        id=d["id"],
        type=d["type"],
        capacite_max=d["capacite_max"],
        occupation=d["occupation"],
        capteur_fumee=d["capteur_fumee"],
        niveau_fumee=d["niveau_fumee"],
        statut=d["statut"],
        x=d.get("x"),
        y=d.get("y"),
        nom=d.get("nom"),
    )
    if noeud.type not in TYPES:
        raise ErreurFormat(f"{ou} : type « {noeud.type} » inconnu")
    if noeud.statut not in STATUTS_NOEUD:
        raise ErreurFormat(f"{ou} : statut « {noeud.statut} » inconnu")
    if noeud.capacite_max <= 0:
        raise ErreurFormat(f"{ou} : capacite_max doit être positive")
    if noeud.occupation < 0 or noeud.occupation > noeud.capacite_max:
        raise ErreurFormat(f"{ou} : occupation ({noeud.occupation}) hors de "
                           f"[0, {noeud.capacite_max}]")
    if noeud.niveau_fumee < 0 or noeud.niveau_fumee > 100:
        raise ErreurFormat(f"{ou} : niveau_fumee ({noeud.niveau_fumee}) hors de [0, 100]")
    return noeud


def arete_depuis_dict(d: dict[str, Any], ou: str) -> Arete:
    """Crée une arête à partir de son dictionnaire, en vérifiant ses valeurs.
    Les extrémités sont vérifiées par l'appelant (centre ou zone)."""
    verifier_champs(d, ["source", "cible", "capacite_max", "longueur", "statut", "sens",
                        "pmr"], ou)
    arete = Arete(
        source=d["source"],
        cible=d["cible"],
        capacite_max=d["capacite_max"],
        longueur=d["longueur"],
        statut=d["statut"],
        sens=d["sens"],
        pmr=d["pmr"],
        largeur=d.get("largeur"),
    )
    if arete.statut not in STATUTS_ARETE:
        raise ErreurFormat(f"{ou} : statut « {arete.statut} » inconnu")
    if arete.sens not in SENS:
        raise ErreurFormat(f"{ou} : sens « {arete.sens} » inconnu")
    # Une longueur nulle ou négative fausserait les plus courts chemins (Dijkstra).
    if arete.longueur <= 0 or arete.capacite_max <= 0:
        raise ErreurFormat(f"{ou} : longueur et capacite_max doivent être positives")
    return arete


def depuis_dict(donnees: dict[str, Any]) -> Centre:
    """Crée un centre à partir des données lues dans son fichier JSON.

    Vérifie : identifiants de nœuds uniques, extrémités d'arêtes existantes, valeurs
    autorisées pour type, statut et sens, occupation entre 0 et la capacité, fumée
    entre 0 et 100. Complexité O(V + E).
    """
    verifier_champs(donnees, ["noeuds", "aretes"], "centre")

    noeuds = []
    ids = set()
    for d in donnees["noeuds"]:
        noeud = noeud_depuis_dict(d)
        if noeud.id in ids:
            raise ErreurFormat(f"identifiant de nœud en double : « {noeud.id} »")
        ids.add(noeud.id)
        noeuds.append(noeud)

    aretes = []
    for i, d in enumerate(donnees["aretes"]):
        ou = f"aretes[{i}]"
        arete = arete_depuis_dict(d, ou)
        if arete.source not in ids:
            raise ErreurFormat(f"{ou} : extrémité « {arete.source} » inexistante")
        if arete.cible not in ids:
            raise ErreurFormat(f"{ou} : extrémité « {arete.cible} » inexistante")
        aretes.append(arete)

    return Centre(noeuds=noeuds, aretes=aretes)


def vers_dict(centre: Centre) -> dict[str, Any]:
    """Transforme un centre en dictionnaire, prêt à être écrit en JSON.
    Les champs facultatifs ne sont écrits que s'ils ont une valeur."""
    noeuds = []
    for n in centre.noeuds:
        d: dict[str, Any] = {
            "id": n.id,
            "type": n.type,
            "capacite_max": n.capacite_max,
            "occupation": n.occupation,
            "capteur_fumee": n.capteur_fumee,
            "niveau_fumee": n.niveau_fumee,
            "statut": n.statut,
        }
        if n.x is not None:
            d["x"] = n.x
        if n.y is not None:
            d["y"] = n.y
        if n.nom is not None:
            d["nom"] = n.nom
        noeuds.append(d)

    aretes = []
    for a in centre.aretes:
        d = {
            "source": a.source,
            "cible": a.cible,
            "capacite_max": a.capacite_max,
            "longueur": a.longueur,
            "statut": a.statut,
            "sens": a.sens,
            "pmr": a.pmr,
        }
        if a.largeur is not None:
            d["largeur"] = a.largeur
        aretes.append(d)

    return {"noeuds": noeuds, "aretes": aretes}
