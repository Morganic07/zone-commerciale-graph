"""Lecture d'une zone commerciale au format JSON (PLAN.md § 2.2).

    {
      "centres": [{"id": "A", "fichier": "centres/A.json", "x": 0, "y": 0}],
      "sources": [{"id": "P1", "type": "parking", "x": -300, "y": 0}],
      "connexions": [{"source": "P1", "cible": "A:EA", "capacite_max": 8,
                      "longueur": 120.0, "statut": "libre", "sens": "bidirectionnel",
                      "pmr": true}]
    }

Une connexion a les mêmes champs qu'une arête. Ses extrémités sont une source (« P1 »)
ou la sortie d'un centre (« A:EA »). Ce module ne touche pas au disque : les centres
sont lus par `chargement.py` et passés en paramètre.
"""

import copy
from typing import Any

from zc.format_centre import arete_depuis_dict, verifier_champs
from zc.modele import (
    SEPARATEUR,
    TYPES_SOURCE,
    Centre,
    CentreZone,
    ErreurFormat,
    Noeud,
    Source,
    Zone,
    macro_noeud,
)


def prefixer(centre: Centre, id_centre: str) -> Centre:
    """Renvoie une copie du centre où chaque identifiant devient « A:S1 ».
    Ainsi, deux centres peuvent utiliser les mêmes noms de nœuds."""
    nouveau = Centre(noeuds=[], aretes=[])
    for n in centre.noeuds:
        copie_noeud = copy.copy(n)
        copie_noeud.id = id_centre + SEPARATEUR + n.id
        nouveau.noeuds.append(copie_noeud)
    for a in centre.aretes:
        copie_arete = copy.copy(a)
        copie_arete.source = id_centre + SEPARATEUR + a.source
        copie_arete.cible = id_centre + SEPARATEUR + a.cible
        nouveau.aretes.append(copie_arete)
    return nouveau


def verifier_extremite(extremite: str, ids_sources: list[str], ids_centres: list[str],
                       noeuds: dict[str, Noeud], ou: str) -> None:
    """Vérifie qu'une extrémité de connexion est une source ou la sortie d'un centre."""
    if SEPARATEUR not in extremite:
        if extremite not in ids_sources:
            raise ErreurFormat(f"{ou} : source « {extremite} » inconnue")
        return
    id_centre = macro_noeud(extremite)
    if id_centre not in ids_centres:
        raise ErreurFormat(f"{ou} : centre « {id_centre} » inconnu")
    if extremite not in noeuds:
        raise ErreurFormat(f"{ou} : sortie « {extremite} » inexistante dans le centre "
                           f"« {id_centre} »")
    noeud = noeuds[extremite]
    if noeud.type != "sortie":
        raise ErreurFormat(f"{ou} : « {extremite} » n'est pas une sortie (type "
                           f"{noeud.type}) ; une connexion entre dans un centre par une sortie")


def depuis_dict(donnees: dict[str, Any], centres_lus: dict[str, Centre]) -> Zone:
    """Crée la zone à partir des données de son fichier JSON.

    `centres_lus` associe chaque nom de fichier de centre au centre déjà lu.
    Vérifie : identifiants de centres et de sources uniques et sans « : », type de
    source connu, extrémités de connexions valides. Complexité O(V + E).
    """
    verifier_champs(donnees, ["centres", "sources", "connexions"], "zone")
    zone = Zone(centres=[], sources=[], connexions=[])
    identifiants = []

    for d in donnees["centres"]:
        verifier_champs(d, ["id", "fichier"], "centre de la zone")
        if SEPARATEUR in d["id"]:
            raise ErreurFormat(f"centre « {d['id']} » : « {SEPARATEUR} » interdit "
                               "dans un identifiant")
        centre = prefixer(centres_lus[d["fichier"]], d["id"])
        zone.centres.append(CentreZone(id=d["id"], centre=centre,
                                       x=d.get("x"), y=d.get("y")))
        identifiants.append(d["id"])

    for d in donnees["sources"]:
        verifier_champs(d, ["id", "type"], "source")
        if SEPARATEUR in d["id"]:
            raise ErreurFormat(f"source « {d['id']} » : « {SEPARATEUR} » interdit "
                               "dans un identifiant")
        if d["type"] not in TYPES_SOURCE:
            raise ErreurFormat(f"source « {d['id']} » : type « {d['type']} » inconnu")
        zone.sources.append(Source(id=d["id"], type=d["type"], x=d.get("x"), y=d.get("y")))
        identifiants.append(d["id"])

    # Un même identifiant ne peut pas servir deux fois (centre ou source).
    deja_vus = set()
    for identifiant in identifiants:
        if identifiant in deja_vus:
            raise ErreurFormat(f"identifiant de centre ou de source en double : "
                               f"« {identifiant} »")
        deja_vus.add(identifiant)

    # Tous les nœuds de tous les centres, rangés par identifiant pour les retrouver vite.
    noeuds = {}
    for c in zone.centres:
        for n in c.centre.noeuds:
            noeuds[n.id] = n
    ids_sources = [s.id for s in zone.sources]
    ids_centres = [c.id for c in zone.centres]

    for i, d in enumerate(donnees["connexions"]):
        ou = f"connexions[{i}]"
        connexion = arete_depuis_dict(d, ou)
        verifier_extremite(connexion.source, ids_sources, ids_centres, noeuds, ou)
        verifier_extremite(connexion.cible, ids_sources, ids_centres, noeuds, ou)
        zone.connexions.append(connexion)

    return zone
