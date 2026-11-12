"""Story 5.1 : diffusion de la fumée (règle de la consigne), fumée des arêtes."""

from pathlib import Path

import pytest

from zc.chargement import charger_zone
from zc.incendie import Incendie, diffuser, fumee_arete, voisins_non_orientes
from zc.modele import Arete, Centre, Noeud

RACINE = Path(__file__).resolve().parent.parent


def chemin_de_4(sens_bc: str = "bidirectionnel") -> Centre:
    """A – B – C – D, tous les nœuds à 0 de fumée."""
    noeuds = []
    for identifiant in ["A", "B", "C", "D"]:
        noeuds.append(Noeud(id=identifiant, type="carrefour", capacite_max=10, occupation=0,
                            capteur_fumee=True, niveau_fumee=0.0, statut="libre"))
    aretes = []
    for u, v in [("A", "B"), ("B", "C"), ("C", "D")]:
        sens = sens_bc if (u, v) == ("B", "C") else "bidirectionnel"
        aretes.append(Arete(source=u, cible=v, capacite_max=2.0, longueur=5.0,
                            statut="libre", sens=sens, pmr=True))
    return Centre(noeuds=noeuds, aretes=aretes)


def test_trois_premiers_pas_calcules_a_la_main() -> None:
    # α = 0,5 ; foyer A, s = 10 par pas.
    # t1 : A = 0 + 0 + 10 = 10 ; les autres restent à 0.
    # t2 : A = 10 + 0 + 10 = 20 ; B = 0 + 0,5 × (10 − 0) = 5.
    # t3 : A = 30 ; B = 5 + 0,5 × (20 − 5) = 12,5 ; C = 0 + 0,5 × (5 − 0) = 2,5 ; D = 0.
    centre = chemin_de_4()
    incendie = Incendie(centre, alpha=0.5, foyers={"A": 10.0})
    attendus = [
        {"A": 10.0, "B": 0.0, "C": 0.0, "D": 0.0},
        {"A": 20.0, "B": 5.0, "C": 0.0, "D": 0.0},
        {"A": 30.0, "B": 12.5, "C": 2.5, "D": 0.0},
    ]
    for attendu in attendus:
        incendie.pas()
        assert incendie.niveaux() == pytest.approx(attendu)


def test_fumee_d_une_arete_est_le_maximum_de_ses_extremites() -> None:
    centre = chemin_de_4()
    incendie = Incendie(centre, alpha=0.5, foyers={"A": 10.0})
    for _ in range(3):
        incendie.pas()
    fumee = incendie.niveaux()
    assert fumee_arete(centre.aretes[0], fumee) == 30.0  # A – B : max(30 ; 12,5)
    assert fumee_arete(centre.aretes[2], fumee) == 2.5   # C – D : max(2,5 ; 0)


def test_jamais_plus_de_100_et_jamais_de_baisse() -> None:
    centre = chemin_de_4()
    incendie = Incendie(centre, alpha=0.8, foyers={"A": 30.0})
    avant = incendie.niveaux()
    for _ in range(200):
        incendie.pas()
        apres = incendie.niveaux()
        for v in apres:
            assert apres[v] <= 100.0
            assert apres[v] >= avant[v]
        avant = apres
    assert avant == {"A": 100.0, "B": 100.0, "C": 100.0, "D": 100.0}


def test_deux_foyers_simultanes() -> None:
    # Foyers à A et D dès t = 0 : la fumée part des deux bouts et C est touché au
    # deuxième pas, ce qu'un seul foyer en A ne ferait qu'au troisième.
    centre = chemin_de_4()
    incendie = Incendie(centre, alpha=0.5, foyers={"A": 10.0, "D": 10.0})
    incendie.pas()
    assert incendie.niveaux() == pytest.approx({"A": 10.0, "B": 0.0, "C": 0.0, "D": 10.0})
    incendie.pas()
    assert incendie.niveaux() == pytest.approx({"A": 20.0, "B": 5.0, "C": 5.0, "D": 20.0})


def test_la_fumee_ignore_les_sens_uniques() -> None:
    # B → C à sens unique, foyer en D : la fumée remonte quand même de C vers B.
    centre = chemin_de_4(sens_bc="unique")
    incendie = Incendie(centre, alpha=0.5, foyers={"D": 10.0})
    for _ in range(3):
        incendie.pas()
    assert incendie.niveaux()["B"] > 0


def test_mise_a_jour_synchrone() -> None:
    # Chaîne A – B – C, A à 40. En synchrone, C ne voit que l'ancienne valeur de B (0) :
    # il reste à 0. Une mise à jour non synchrone lui ferait déjà recevoir la fumée que B
    # vient de prendre (B = 20, donc C = 10).
    aretes = []
    for u, v in [("A", "B"), ("B", "C")]:
        aretes.append(Arete(source=u, cible=v, capacite_max=1.0, longueur=1.0,
                            statut="libre", sens="bidirectionnel", pmr=True))
    voisins = voisins_non_orientes(["A", "B", "C"], aretes)
    attendu = {"A": 40.0, "B": 20.0, "C": 0.0}
    assert diffuser({"A": 40.0, "B": 0.0, "C": 0.0}, voisins, 0.5, {}) == attendu
    # L'ordre des nœuds ne change rien.
    assert diffuser({"C": 0.0, "B": 0.0, "A": 40.0}, voisins, 0.5, {}) == attendu


def test_couloirs_paralleles_comptent_une_seule_fois() -> None:
    aretes = []
    for _ in range(2):
        aretes.append(Arete(source="A", cible="B", capacite_max=1.0, longueur=1.0,
                            statut="libre", sens="bidirectionnel", pmr=True))
    assert voisins_non_orientes(["A", "B"], aretes) == {"A": ["B"], "B": ["A"]}


def test_sur_un_centre_de_la_zone() -> None:
    zone = charger_zone(RACINE / "donnees" / "zone.json")
    centre = zone.centres[0].centre
    foyer = centre.noeuds[0].id
    incendie = Incendie(centre, alpha=0.3, foyers={foyer: 20.0})
    for _ in range(50):
        incendie.pas()
    fumee = incendie.niveaux()
    assert fumee[foyer] == 100.0
    touches = 0
    for v in fumee:
        if fumee[v] > 0:
            touches += 1
    assert touches > 1


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.2, 1.5])
def test_alpha_hors_de_0_1_refuse(alpha: float) -> None:
    with pytest.raises(ValueError, match="α"):
        Incendie(chemin_de_4(), alpha=alpha, foyers={"A": 10.0})


def test_foyer_inconnu_refuse() -> None:
    with pytest.raises(ValueError, match="Z"):
        Incendie(chemin_de_4(), alpha=0.5, foyers={"Z": 10.0})
