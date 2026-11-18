"""Étape b1 : traduction des listes déroulantes et page Création (simulée sans navigateur)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from saoub.interface import contraintes_depuis_choix, resume

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_contraintes_depuis_choix():
    choix = {"ATK": {"niveau": "Valeur exacte…", "egal": 2800}, "SPD": {"niveau": "Très haut (20 % les plus hauts)"},
             "HP": {"niveau": "Fourchette…", "min": 8500, "max": 7500}, "DEF": {"niveau": "Libre"}}
    c = contraintes_depuis_choix("Physique (ATK ≥ MATK)", choix)
    assert c == {"famille": "physique", "ATK": {"egal": 2800}, "SPD": {"pct_min": 80}, "HP": {"min": 7500, "max": 8500}}
    assert contraintes_depuis_choix("Au choix du moteur", {}) == {}
    params = dict(contraintes=c, imposes=["Dégâts continus"], originalite="Classique", diversifier=True, n=5)
    assert resume(params, 7) == ("graine 7 · physique, HP 7500–8500, ATK = 2800, SPD très haut · Dégâts continus · classique")


def page_creation():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.switch_page("app_pages/creation.py").run()
    assert not at.exception
    return at


def bouton(at, texte):
    return next(b for b in at.button if b.label == texte)


def test_parcours_creation():
    at = page_creation()
    assert "clique **Créer**" in at.info[0].value
    at.selectbox(key="c_famille").set_value("Physique (ATK ≥ MATK)")
    at.selectbox(key="c_niv_ATK").set_value("Valeur exacte…").run()
    at.number_input(key="c_egal_ATK").set_value(2800)
    at.selectbox(key="c_niv_SPD").set_value("Très haut (20 % les plus hauts)")
    at.multiselect(key="c_effets").set_value(["Dégâts continus"])
    bouton(at, "Créer").click().run()
    assert not at.exception
    apercu = at.dataframe[0].value
    assert len(apercu) == 5 and (apercu["ATK"] == 2800).all() and (apercu["Famille"] == "physique").all()
    assert len(at.tabs) == 5
    premier = apercu.copy()

    at.number_input(key="graine").set_value(1).run()                 # la graine relance tout de suite
    assert not at.exception and not at.dataframe[0].value.equals(premier)
    assert len(at.session_state["historique"]) == 2

    at.selectbox(key="retour_histo").set_value(1).run()              # retour au premier résultat
    assert at.session_state["graine"] == 0
    assert at.dataframe[0].value.equals(premier)


def test_contraintes_impossibles():
    at = page_creation()
    for s in ("HP", "DEF", "MDEF"):
        at.selectbox(key=f"c_niv_{s}").set_value("Fourchette…").run()
        at.number_input(key=f"c_min_{s}").set_value(at.number_input(key=f"c_max_{s}").value)
    bouton(at, "Créer").click().run()
    assert not at.exception
    assert at.error and "relâche" in at.error[0].value
