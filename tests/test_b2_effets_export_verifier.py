"""Étape b2 : effets personnalisés, export et page Vérifier (simulés sans navigateur, fichiers en dossier temporaire)."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def fichiers(tmp_path, monkeypatch):
    chemins = dict(effets=tmp_path / "effets_personnalises.json", nouveaux=tmp_path / "personage_new.json")
    monkeypatch.setenv("SAOUB_EFFETS_PERSO", str(chemins["effets"]))
    monkeypatch.setenv("SAOUB_NOUVEAUX", str(chemins["nouveaux"]))
    return chemins


def ouvrir(page):
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.switch_page(page).run()
    assert not at.exception, at.exception
    return at


def bouton(at, debut):
    exact = [b for b in at.button if b.label == debut]
    return exact[0] if exact else next(b for b in at.button if b.label.startswith(debut))


def test_creer_utiliser_supprimer_effet(fichiers):
    at = ouvrir("app_pages/creation.py")
    at.text_input(key="n_nom").set_value("Poison renforcé")
    at.selectbox(key="n_modele").set_value("Dégâts continus")
    bouton(at, "Créer l'effet").click().run()
    assert not at.exception
    assert json.loads(fichiers["effets"].read_text(encoding="utf-8"))["effets"][0]["nom"] == "Poison renforcé"
    assert "Poison renforcé" in at.multiselect(key="c_effets").options[-1]           # dernier de la liste

    at.multiselect(key="c_effets").set_value(["Poison renforcé"])
    bouton(at, "Créer").click().run()
    assert not at.exception
    assert any("Poison renforcé" in w.value for w in at.warning)                     # alerte « aucune donnée réelle »

    at.text_input(key="n_nom").set_value("poison RENFORCÉ")                          # doublon refusé
    bouton(at, "Créer l'effet").click().run()
    assert at.error and "existe déjà" in at.error[0].value

    at.selectbox(key="n_suppr").set_value("Poison renforcé").run()
    at.button(key="n_bouton_suppr").click().run()
    assert not at.exception
    assert json.loads(fichiers["effets"].read_text(encoding="utf-8"))["effets"] == []
    assert at.multiselect(key="c_effets").value == []                               # retiré de la sélection


def test_export(fichiers):
    at = ouvrir("app_pages/creation.py")
    bouton(at, "Créer").click().run()
    at.text_input(key="e_nom").set_value("Eugeo")
    at.text_input(key="e_titre").set_value("Chevalier de glace")
    at.run()
    assert at.number_input(key="e_id").value == 999000001
    bouton(at, "💾").click().run()
    assert not at.exception and at.success
    contenu = json.loads(fichiers["nouveaux"].read_text(encoding="utf-8"))
    assert contenu["personnages"][0]["nom_complet"] == "[Chevalier de glace] Eugeo"
    assert at.number_input(key="e_id").value == 999000002                            # id suivant proposé
    at.number_input(key="e_id").set_value(999000001).run()
    bouton(at, "💾").click().run()
    assert at.error and "déjà présent" in at.error[0].value


def test_verifier_saisie_et_import(fichiers):
    at = ouvrir("app_pages/verifier.py")
    at.multiselect(key="v_kit").set_value(["Rôle Break", "Dégâts continus"])
    at.button(key="v_saisie").click().run()
    assert not at.exception and "Diagnostic" in at.subheader[0].value
    simple = {"stats": {"HP": 12010, "MP": 270, "ATK": 2810, "MATK": 900, "DEF": 1500, "MDEF": 1450, "CRIT": 999,
                        "SPD": 335}, "kit": ["Provocation", "Effet inventé"]}
    at.text_area(key="v_texte").set_value(json.dumps(simple)).run()
    at.button(key="v_import").click().run()
    assert not at.exception
    textes = [w.value for w in at.warning]
    assert any("Effet inventé" in t for t in textes) and any("HP = 12010" in t for t in textes)
    at.text_area(key="v_texte").set_value("{pas du json").run()
    assert at.error and "illisible" in at.error[0].value
