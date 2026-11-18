"""Étape a1 : la version pandas doit donner exactement les mêmes tables que la version Spark du notebook 03.
Les fichiers tests/reference/*.csv ont été produits par le notebook 03 (Spark) sur personnages_fr.json."""
import copy
from pathlib import Path

import pandas as pd
import pytest

from saoub.donnees import GRILLE_100, STATS, charger_persos, preparer_table, table_stats
from saoub.effets import (ajouter_effet_perso, charger_effets_perso, construire_effets, liste_effets,
                          phrases_a_classer, supprimer_effet_perso)

REF = Path(__file__).parent / "reference"


@pytest.fixture(scope="module")
def persos():
    return charger_persos()


@pytest.fixture(scope="module")
def df_eff(persos):
    return construire_effets(persos)


def test_effectifs(persos):
    assert len(persos) == 218
    assert sum(p["free"] for p in persos) == 37


def test_effets_identiques_a_spark(df_eff):
    cles = ["perso_id", "slot", "p", "effet"]
    ref = pd.read_csv(REF / "effets_spark.csv", encoding="utf-8")
    a = df_eff[cles].sort_values(cles).reset_index(drop=True)
    b = ref[cles].sort_values(cles).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
    assert df_eff["effet"].nunique() == 59
    assert (df_eff["effet"] == "Autre").sum() == 0


def test_table_de_travail_identique_a_spark(persos, df_eff):
    tab = preparer_table(persos, df_eff, niveau=100)
    base_ref = pd.read_csv(REF / "base_spark_100.csv", index_col="perso_id", encoding="utf-8")
    kit_ref = pd.read_csv(REF / "kit_spark_100.csv", index_col="perso_id", encoding="utf-8").astype(bool)
    pd.testing.assert_frame_equal(tab["base"].sort_index(), base_ref.sort_index(), check_dtype=False)
    kit = tab["kit"].sort_index()
    assert list(kit.columns) == list(kit_ref.columns) and kit.shape[1] == 62
    pd.testing.assert_frame_equal(kit, kit_ref.sort_index(), check_dtype=False)


def test_grille_non_free(persos, df_eff):
    base = preparer_table(persos, df_eff)["base"]
    ref = base[~base["free"]]
    attendu = {"HP": 132, "DEF": 135, "MDEF": 134, "ATK": 123, "MATK": 143}
    assert {s: int((ref[s] % pas == 0).sum()) for s, pas in GRILLE_100.items()} == attendu


def test_table_stats(persos):
    t = table_stats(persos)
    assert t.shape == (218, 32) and f"{STATS[0]}_1" in t.columns


def test_effets_personnalises(tmp_path, persos, df_eff):
    """Une phrase inconnue apparaît « à classer », puis est reconnue une fois l'effet créé."""
    chemin = tmp_path / "effets_personnalises.json"
    faux = copy.deepcopy(persos[0])
    faux["id"] = 999999999
    faux["competences"]["competence_1"]["niveaux"][-1]["description"] += " Vole 12% des MP de l'ennemi."
    eff = construire_effets([faux])
    a_classer = phrases_a_classer(eff, [faux])
    assert list(a_classer["p"]) == ["Vole N% des MP de l'ennemi"]

    connus = liste_effets(df_eff)["jeu"]
    with pytest.raises(ValueError):                                   # doublon d'un effet du jeu
        ajouter_effet_perso("dégâts continus", "Autres mécaniques", connus, chemin=chemin)
    with pytest.raises(ValueError):                                   # « se comporte comme » inconnu
        ajouter_effet_perso("Vol de MP", "Autres mécaniques", connus, se_comporte_comme="Inexistant", chemin=chemin)
    ajouter_effet_perso("Vol de MP", "Autres mécaniques", connus, se_comporte_comme="Absorption de HP",
                        phrases=a_classer["p"], chemin=chemin)
    registre = charger_effets_perso(chemin)
    assert registre[0]["nom"] == "Vol de MP"

    eff2 = construire_effets([faux], effets_perso=registre)
    assert "Vol de MP" in set(eff2["effet"]) and (eff2["effet"] == "Autre").sum() == 0
    assert set(eff2["effet"]) - {"Vol de MP"} == set(eff["effet"]) - {"Autre"}     # le reste ne bouge pas
    assert liste_effets(eff2, registre)["personnalise"] == ["Vol de MP"]

    assert supprimer_effet_perso("Vol de MP", chemin) == []
