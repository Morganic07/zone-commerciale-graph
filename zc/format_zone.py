"""Format JSON de la zone commerciale (PLAN.md § 2.2) et sa conversion en modèle.

Python pur : les fichiers de centres sont lus par une fonction `charger` fournie par
l'appelant (`chargement.charger_zone`), ce qui garde ce module testable sans disque.

    {
      "centres": [{"id": "A", "fichier": "centres/A.json", "x": 0, "y": 0}],
      "sources": [{"id": "P1", "type": "parking", "x": -300, "y": 0}],
      "connexions": [{"source": "P1", "cible": "A:EA", "capacite_max": 8,
                      "longueur": 120.0, "statut": "libre", "sens": "bidirectionnel",
                      "pmr": true}]
    }

Une connexion a les champs d'une arête de centre ; ses extrémités sont une source ou
la sortie d'un centre, désignée « <centre>:<id> ».
"""

from collections.abc import Callable
from dataclasses import replace

from zc.format_centre import arete_depuis_dict
from zc.modele import (
    SEPARATEUR,
    TYPES_SOURCE,
    Centre,
    CentreZone,
    Source,
    Zone,
    identifiant_zone,
)
from zc.validation import (
    ErreurFormat,
    champs,
    dans,
    liste,
    nombre_facultatif,
    objet,
    texte,
)


def prefixer(centre: Centre, cid: str) -> Centre:
    """Copie du centre dont chaque identifiant de nœud devient « <cid>:<id> », pour que
    deux centres puissent employer les mêmes noms internes. Complexité O(V + E)."""
    return Centre(
        noeuds=[replace(n, id=identifiant_zone(cid, n.id)) for n in centre.noeuds],
        aretes=[replace(a, source=identifiant_zone(cid, a.source),
                        cible=identifiant_zone(cid, a.cible)) for a in centre.aretes],
    )


def _identifiant_macro(d: dict[str, object], ou: str) -> str:
    identifiant = texte(d, "id", ou)
    if SEPARATEUR in identifiant:
        raise ErreurFormat(f"{ou} : l'identifiant « {identifiant} » ne doit pas contenir "
                           f"« {SEPARATEUR} », réservé aux nœuds des centres")
    return identifiant


def _centre(brut: object, rang: int, charger: Callable[[str], Centre]) -> CentreZone:
    ou = f"centres[{rang}]"
    d = objet(brut, ou)
    champs(d, ("id", "fichier"), ("x", "y"), ou)
    cid = _identifiant_macro(d, ou)
    centre = charger(texte(d, "fichier", ou))
    return CentreZone(id=cid, centre=prefixer(centre, cid),
                      x=nombre_facultatif(d, "x", ou), y=nombre_facultatif(d, "y", ou))


def _source(brut: object, rang: int) -> Source:
    ou = f"sources[{rang}]"
    d = objet(brut, ou)
    champs(d, ("id", "type"), ("x", "y"), ou)
    return Source(id=_identifiant_macro(d, ou),
                  type=dans(texte(d, "type", ou), TYPES_SOURCE, "type", ou),
                  x=nombre_facultatif(d, "x", ou), y=nombre_facultatif(d, "y", ou))


def _verifier_extremite(extremite: str, centres: dict[str, CentreZone], sources: set[str],
                        ou: str) -> None:
    """Message explicite pour chaque façon de rater une extrémité de connexion."""
    if SEPARATEUR not in extremite:
        if extremite not in sources:
            raise ErreurFormat(f"{ou} : source « {extremite} » inconnue")
        return
    cid = extremite.split(SEPARATEUR, 1)[0]
    if cid not in centres:
        raise ErreurFormat(f"{ou} : centre « {cid} » inconnu (extrémité « {extremite} »)")
    try:
        noeud = centres[cid].centre.noeud(extremite)
    except KeyError:
        raise ErreurFormat(f"{ou} : sortie « {extremite} » inexistante dans le centre "
                           f"« {cid} »") from None
    if noeud.type != "sortie":
        raise ErreurFormat(f"{ou} : « {extremite} » n'est pas une sortie (type "
                           f"{noeud.type}) ; une connexion n'entre dans un centre que par "
                           "une sortie")


def depuis_dict(donnees: object, charger: Callable[[str], Centre]) -> Zone:
    """Valide une zone et construit le modèle ; `charger(fichier)` renvoie le centre
    décrit par le fichier, tel que cité dans « fichier ».

    Règles : identifiants de centres et de sources uniques, sans « : » ; type de source
    parmi parking, station, quartier ; chaque extrémité de connexion est une source ou
    une sortie existante d'un centre, et les deux extrémités sont dans des macro-nœuds
    distincts ; les connexions respectent les règles d'une arête.
    Complexité O(V + E) sur l'ensemble des nœuds et arêtes des centres et connexions.
    """
    racine = objet(donnees, "zone")
    champs(racine, ("centres", "sources", "connexions"), (), "zone")
    centres = [_centre(b, i, charger) for i, b in enumerate(liste(racine["centres"],
                                                                   "zone.centres"))]
    sources = [_source(b, i) for i, b in enumerate(liste(racine["sources"], "zone.sources"))]

    vus: set[str] = set()
    for identifiant in [c.id for c in centres] + [s.id for s in sources]:
        if identifiant in vus:
            raise ErreurFormat(f"identifiant de centre ou de source en double : "
                               f"« {identifiant} »")
        vus.add(identifiant)

    par_id = {c.id: c for c in centres}
    ids_sources = {s.id for s in sources}
    points = ids_sources | {n.id for c in centres for n in c.centre.noeuds
                            if n.type == "sortie"}
    connexions = []
    for i, brut in enumerate(liste(racine["connexions"], "zone.connexions")):
        ou = f"connexions[{i}]"
        d = objet(brut, ou)
        for cle in ("source", "cible"):
            if isinstance(d.get(cle), str):
                _verifier_extremite(str(d[cle]), par_id, ids_sources, ou)
        connexion = arete_depuis_dict(d, ou, points)
        # Consigne § 1 : une connexion relie des centres (ou des sources) entre eux. Deux
        # sorties d'un même centre ne forment pas une zone de connexion, et donneraient
        # une boucle dans la vue macro.
        macro = Zone.macro_noeud(connexion.source)
        if macro == Zone.macro_noeud(connexion.cible):
            raise ErreurFormat(f"{ou} : les deux extrémités sont dans le centre « {macro} » ; "
                               "une connexion relie deux centres ou sources distincts")
        connexions.append(connexion)
    return Zone(centres=centres, sources=sources, connexions=connexions)
