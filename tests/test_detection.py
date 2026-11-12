"""Story 5.2 : détection (seuils θ₁ et θ₂, retard δ sans capteur), état réel et statut
connu séparés."""

import pytest

from zc.incendie import Incendie, niveau_reel
from zc.modele import Arete, Centre, Noeud
from zc.navigation import graphe_du_centre


def chemin_de_5(sans_capteur: list[str]) -> Centre:
    """A – B – C – D – E (sortie), foyer prévu en A."""
    noeuds = []
    for identifiant in ["A", "B", "C", "D", "E"]:
        est_sortie = identifiant == "E"
        noeuds.append(Noeud(id=identifiant, type="sortie" if est_sortie else "carrefour",
                            capacite_max=10, occupation=0,
                            capteur_fumee=identifiant not in sans_capteur,
                            niveau_fumee=0.0, statut="sortie" if est_sortie else "libre"))
    aretes = []
    for u, v in [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")]:
        aretes.append(Arete(source=u, cible=v, capacite_max=2.0, longueur=5.0,
                            statut="libre", sens="bidirectionnel", pmr=True))
    return Centre(noeuds=noeuds, aretes=aretes)


def suivre(centre: Centre, incendie: Incendie, noeud: str,
           pas: int) -> tuple[dict[str, int], dict[str, int]]:
    """Pour un nœud : le pas où sa fumée réelle franchit chaque seuil, et le pas où son
    statut connu change."""
    reel: dict[str, int] = {}
    connu: dict[str, int] = {}
    n = centre.noeud(noeud)
    for _ in range(pas):
        incendie.pas()
        etat = niveau_reel(n.niveau_fumee, incendie.theta1, incendie.theta2)
        if etat != "libre" and etat not in reel:
            reel[etat] = incendie.t
            if etat == "bloqué" and "enfumé" not in reel:
                reel["enfumé"] = incendie.t
        if n.statut in ("enfumé", "bloqué") and n.statut not in connu:
            connu[n.statut] = incendie.t
            if n.statut == "bloqué" and "enfumé" not in connu:
                connu["enfumé"] = incendie.t
    return reel, connu


def test_avec_capteur_le_statut_change_au_pas_du_franchissement() -> None:
    centre = chemin_de_5(sans_capteur=[])
    incendie = Incendie(centre, alpha=0.4, foyers={"A": 8.0}, theta1=30, theta2=70, delai=5)
    reel, connu = suivre(centre, incendie, "C", 120)
    assert set(reel) == {"enfumé", "bloqué"}
    assert connu == reel


def test_sans_capteur_le_statut_change_exactement_delta_pas_plus_tard() -> None:
    centre = chemin_de_5(sans_capteur=["C"])
    incendie = Incendie(centre, alpha=0.4, foyers={"A": 8.0}, theta1=30, theta2=70, delai=5)
    reel, connu = suivre(centre, incendie, "C", 120)
    assert set(reel) == {"enfumé", "bloqué"}
    assert connu["enfumé"] == reel["enfumé"] + 5
    assert connu["bloqué"] == reel["bloqué"] + 5


def test_etat_reel_et_statut_connu_separes() -> None:
    # Pendant le retard δ, C est réellement enfumé mais l'alarme l'ignore encore.
    centre = chemin_de_5(sans_capteur=["C"])
    incendie = Incendie(centre, alpha=0.4, foyers={"A": 8.0}, theta1=30, theta2=70, delai=5)
    c = centre.noeud("C")
    vu_l_ecart = False
    for _ in range(120):
        incendie.pas()
        if c.niveau_fumee >= 30 and c.statut == "libre":
            vu_l_ecart = True
    assert vu_l_ecart


def test_le_graphe_de_navigation_suit_le_statut_connu() -> None:
    centre = chemin_de_5(sans_capteur=["C"])
    incendie = Incendie(centre, alpha=0.4, foyers={"A": 8.0}, theta1=30, theta2=70, delai=5)
    c = centre.noeud("C")
    while c.statut != "bloqué":
        incendie.pas()
        # Tant que C n'est pas connu comme bloqué, il reste dans le graphe, même
        # réellement au-delà de θ₂.
        if c.statut != "bloqué":
            assert "C" in graphe_du_centre(centre, "court")
    assert "C" not in graphe_du_centre(centre, "court")


def test_statut_des_couloirs_le_pire_des_extremites() -> None:
    centre = chemin_de_5(sans_capteur=[])
    incendie = Incendie(centre, alpha=0.4, foyers={"A": 8.0}, theta1=30, theta2=70, delai=0)
    for _ in range(200):
        incendie.pas()
        statuts = {}
        for n in centre.noeuds:
            statuts[n.id] = n.statut
        for a in centre.aretes:
            pires = [statuts[a.source], statuts[a.cible]]
            if "bloqué" in pires:
                assert a.statut == "bloqué"
            elif "enfumé" in pires:
                assert a.statut == "enfumé"
            else:
                assert a.statut == "libre"


def test_l_incendie_ne_rouvre_jamais_un_passage_ferme_au_depart() -> None:
    # Le couloir D – E et le nœud D sont fermés dès le départ ; la fumée arrive en D et
    # le rend « enfumé » avant « bloqué » : D doit rester bloqué tout du long.
    centre = chemin_de_5(sans_capteur=[])
    centre.aretes[3].statut = "bloqué"
    centre.noeud("D").statut = "bloqué"
    incendie = Incendie(centre, alpha=0.4, foyers={"A": 8.0}, theta1=30, theta2=70, delai=0)
    for _ in range(200):
        incendie.pas()
        assert centre.aretes[3].statut == "bloqué"
        assert centre.noeud("D").statut == "bloqué"


def test_une_sortie_garde_son_statut_tant_qu_elle_n_est_pas_enfumee() -> None:
    centre = chemin_de_5(sans_capteur=[])
    incendie = Incendie(centre, alpha=0.4, foyers={"A": 8.0}, theta1=30, theta2=70, delai=0)
    e = centre.noeud("E")
    incendie.pas()
    assert e.statut == "sortie"
    for _ in range(300):
        incendie.pas()
    assert e.statut == "bloqué"  # une sortie peut finir bloquée


@pytest.mark.parametrize("theta1, theta2, delai", [(70, 30, 5), (0, 50, 5), (30, 120, 5),
                                                   (30, 70, -1)])
def test_parametres_invalides(theta1: float, theta2: float, delai: int) -> None:
    with pytest.raises(ValueError):
        Incendie(chemin_de_5([]), alpha=0.4, foyers={"A": 8.0}, theta1=theta1,
                 theta2=theta2, delai=delai)
