"""Étape c1 : fonctions de graphiques (chiffres connus des notebooks) et page Graphiques avec filtres."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from saoub.donnees import charger_persos
from saoub.effets import construire_effets
from saoub.graphiques import (carte_identite, fig_correlations, fig_effets, fig_effets_element, fig_menu_stats,
                              fig_repartition, filtrer, table_graphiques, top_flop)

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(scope="module")
def donnees():
    p = charger_persos()
    return p, construire_effets(p), table_graphiques(p, 100)


def test_chiffres_connus(donnees):
    p, eff, t = donnees
    non_free = t[~t["free"]]
    assert non_free["famille"].value_counts().to_dict() == {"physique": 117, "magique": 64}
    assert fig_correlations(non_free)[1].set_index("stat").loc["ATK", "MATK"] == pytest.approx(-0.78, abs=0.01)
    menu = fig_menu_stats(table_graphiques(p, 100)[lambda d: ~d["free"]], 100)[1].set_index("stat")
    assert menu.loc["HP", "grille"].startswith("73%")                    # 132 / 181 non-free sur la grille
    _, tab = fig_repartition(t)
    assert tab["total"].sum() == 218
    _, g = fig_effets(eff, len(t))
    assert len(g) == 59
    _, c = fig_effets_element(eff, t)
    somme = c.set_index("effet").sum(axis=1)                               # chaque perso compte une fois par effet
    assert (somme == g.set_index("effet")["persos"].reindex(somme.index)).all()


def test_filtres_et_top(donnees):
    p, eff, t = donnees
    assert len(filtrer(t, eff, offerts=False)) == 181
    feu = filtrer(t, eff, elements=["feu"], effets=["Dégâts continus"])
    assert len(feu) and (feu["element"] == "feu").all()
    assert set(feu.index) <= set(eff.loc[eff["effet"] == "Dégâts continus", "perso_id"])
    haut, bas = top_flop(t, "SPD")
    assert len(haut) >= 5 and haut["SPD"].is_monotonic_decreasing and bas["SPD"].is_monotonic_increasing


def test_carte_identite(donnees):
    _, _, t = donnees
    v = t.iloc[0][["HP", "MP", "ATK", "MATK", "DEF", "MDEF", "CRIT", "SPD"]].to_dict()
    fig, tableau, phrase = carte_identite(t, v, "test", comparer=(v, "copie"))
    assert len(tableau) == 8 and tableau["percentile"].between(0, 100).all() and "stat(s) hors" in phrase
    assert len(fig.data) == 4


def test_page_graphiques():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.switch_page("app_pages/graphiques.py").run()
    assert not at.exception, at.exception
    assert "218 perso(s)" in at.caption[0].value
    at.radio(key="g_offerts").set_value(False).run()
    assert "181 perso(s)" in at.caption[0].value
    at.multiselect(key="g_elements").set_value(["feu"])
    at.radio(key="g_niveau").set_value(120).run()
    assert not at.exception
    at.text_input(key="g_recherche").set_value("Kirito").run()          # petit groupe : avertissement, pas de plantage
    assert not at.exception
    at.text_input(key="g_recherche").set_value("zzzz").run()
    assert not at.exception and "Aucun perso" in at.warning[0].value
