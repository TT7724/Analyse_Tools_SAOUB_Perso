"""Étape a3 : mêmes alertes et même fiche exportée que le notebook 03 (tests/reference/validation_export_notebook.json)."""
import json
from pathlib import Path

import pytest

from saoub.creation import preparer_tout
from saoub.effets import ajouter_effet_perso, charger_effets_perso, liste_effets
from saoub.export import (ajouter_au_fichier, charger_nouveaux, en_texte_json, fiche_perso, id_libre, importer_persos)
from saoub.moteur_kit import ajuster_moteur_kit
from saoub.validation import valider_perso

REF = json.load(open(Path(__file__).parent / "reference" / "validation_export_notebook.json", encoding="utf-8"))


@pytest.fixture(scope="module")
def tout(tmp_path_factory):
    return preparer_tout(chemin_effets_perso=tmp_path_factory.mktemp("registre") / "effets_personnalises.json")


def test_alertes_identiques(tout):
    for cas, attendu in zip(REF["cas"], REF["alertes"]):
        assert valider_perso(tout["moteur"], tout["moteur_kit"], cas)["alertes"] == attendu


def test_rapport_complet(tout):
    r = valider_perso(tout["moteur"], tout["moteur_kit"], REF["cas"][0])
    assert list(r["stats"]["stat"]) == ["HP", "MP", "ATK", "MATK", "DEF", "MDEF", "CRIT", "SPD"]
    assert r["famille"] == "physique" and 0 < r["distance"] < 1 and len(r["kit"]) == 5


def test_fiche_identique(tout):
    fiche = fiche_perso(REF["cas"][0], tout["persos"], 999000002, "Eugeo", "[pas bo]", "feu", "Épée", parametres=dict(graine=0))
    assert fiche == REF["fiche"]


def test_fichier_et_ids(tmp_path, tout):
    chemin = tmp_path / "personage_new.json"
    assert id_libre(tout["persos"], chemin) == 999000001
    fiche = fiche_perso(REF["cas"][0], tout["persos"], 999000001, "Test", "[t]", "feu", "Épée")
    ajouter_au_fichier(fiche, chemin)
    assert id_libre(tout["persos"], chemin) == 999000002                    # l'id suivant est proposé
    with pytest.raises(ValueError):
        ajouter_au_fichier(fiche, chemin)                                    # doublon refusé...
    ajouter_au_fichier(fiche, chemin, remplacer=True)                        # ...sauf si on remplace
    assert charger_nouveaux(chemin)["nb_personnages"] == 1
    with pytest.raises(ValueError):
        fiche_perso(REF["cas"][0], tout["persos"], tout["persos"][0]["id"], "X", "[x]", "feu", "Épée")   # id du jeu
    with pytest.raises(ValueError):
        fiche_perso(REF["cas"][0], tout["persos"], 999000005, "X", "[x]", "plasma", "Épée")              # élément


def test_import(tout):
    fiche = fiche_perso(REF["cas"][0], tout["persos"], 999000002, "Eugeo", "[pas bo]", "feu", "Épée")
    assert importer_persos(en_texte_json(fiche))[0]["stats"] == REF["cas"][0]["stats"]
    assert importer_persos(json.dumps(REF["cas"][1]))[0]["kit"] == REF["cas"][1]["kit"]
    # un vrai perso au format du jeu : kit déduit des descriptions = sa ligne de la table de travail
    vrai = next(p for p in tout["persos"] if not p["free"])
    importe = importer_persos(json.dumps(vrai))[0]
    ligne = tout["tab"]["kit"].loc[vrai["id"]]
    assert set(importe["kit"]) == set(ligne[ligne].index)
    r = valider_perso(tout["moteur"], tout["moteur_kit"], importe)
    assert "stats identiques à un vrai perso" in r["alertes"]


def test_effet_personnalise_dans_la_validation(tmp_path, tout):
    chemin = tmp_path / "effets_personnalises.json"
    ajouter_effet_perso("Poison renforcé", "Autres mécaniques", liste_effets(tout["df_eff"])["jeu"],
                        se_comporte_comme="Dégâts continus", chemin=chemin)
    mk = ajuster_moteur_kit(tout["tab"], effets_perso=charger_effets_perso(chemin))
    perso = dict(stats=REF["cas"][1]["stats"], kit=["Rôle Break", "Poison renforcé"])
    r = valider_perso(tout["moteur"], mk, perso)
    r_modele = valider_perso(tout["moteur"], mk, REF["cas"][1])               # même kit avec « Dégâts continus »
    assert r["distance_kit"] == r_modele["distance_kit"]
    assert r["alertes"][-1].startswith("effet nouveau « Poison renforcé »")
