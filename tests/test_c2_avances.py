"""Étape c2 : analyses avancées (mêmes calculs que le notebook 01) et onglet Avancé."""
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from saoub.donnees import STATS, charger_persos, preparer_table
from saoub.effets import construire_effets
from saoub.graphiques import table_graphiques
from saoub.graphiques_avances import (construire_espace, fig_acp, fig_complexite, fig_dendrogramme, fig_offre_demande,
                                      fig_triangles, fig_voisins, kit_par_slots, preparer_acp, table_budget_stats,
                                      table_complexite, table_offre_demande)

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SLOTS_1_3 = ["competence_1", "competence_2", "competence_3"]


@pytest.fixture(scope="module")
def d():
    p = charger_persos(); e = construire_effets(p); t = table_graphiques(p, 100)
    return dict(p=p, e=e, kit=preparer_table(p, e)["kit"], nf=t[~t["free"]])


def test_acp(d):
    a = preparer_acp(d["nf"])
    assert a["var"].sum() == pytest.approx(1) and a["var"][0] >= a["var"][1]
    assert (a["load"].sum() >= 0).all()                         # axes orientés « stats hautes = positif »
    fig, charges, eta = fig_acp(a)
    assert eta.set_index("catégorie").loc["famille", "eta² PC1"] >= 0


def test_voisins_et_groupes(d):
    esp = construire_espace(d["nf"], kit_par_slots(d["kit"], d["e"], SLOTS_1_3, d["nf"].index))
    assert esp["med_nn"] < esp["med_paires"]                     # un voisin est plus proche qu'un perso au hasard
    pid = d["nf"].index[0]
    _, t = fig_voisins(esp, pid, 5)
    assert len(t) == 5 and t["distance"].is_monotonic_increasing
    assert d["nf"].loc[pid, "nom_complet"] not in set(t["voisin"])
    _, tab, groupe = fig_dendrogramme(esp, 8)
    assert tab["persos"].sum() == 181 and groupe.nunique() == 8 and tab["persos"].is_monotonic_decreasing


def test_offre_demande(d):
    od = table_offre_demande(d["p"], set(d["nf"].index), 100)
    assert len(od) == 181
    _, _, r = fig_offre_demande(od)
    ligne = r.set_index("état").loc["Dégâts continus"]
    assert ligne["fournit_seul"] + ligne["les_deux"] == od["F_0"].sum()


def test_complexite_et_triangles(d):
    st = table_complexite(d["nf"], d["e"])
    assert st["n_effets"].min() >= 0 and abs(st["puissance"].mean()) < 1e-9
    _, _, res = fig_complexite(st)
    assert (res["bas"] <= res["rho"]).all() and (res["rho"] <= res["haut"]).all()
    b = table_budget_stats(d["nf"])
    assert np.allclose(b[["part_Attaque", "part_Défense", "part_Tempo"]].sum(axis=1), 1)
    f1, f2, resume = fig_triangles(d["nf"], d["e"])
    assert len(resume) == 6


def test_onglet_avance():
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.switch_page("app_pages/graphiques.py").run()
    assert not at.exception, at.exception
    at.radio(key="g_offerts").set_value(False).run()
    at.slider(key="g_vois_poids").set_value(1.0).run()
    at.slider(key="g_dendro_n").set_value(4).run()
    assert not at.exception
    at.multiselect(key="g_elements").set_value(["feu"]).run()                 # 25 à 31 persos : tout doit marcher
    assert not at.exception
    at.text_input(key="g_recherche").set_value("Kirito").run()               # petit groupe : message, pas de plantage
    assert not at.exception
