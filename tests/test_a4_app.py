"""Étape a4 : chaque page de l'application s'exécute sans erreur (test « sans navigateur » de Streamlit)."""
import pytest
from streamlit.testing.v1 import AppTest

from pathlib import Path

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PAGES = ["app_pages/accueil.py", "app_pages/graphiques.py", "app_pages/creation.py",
         "app_pages/verifier.py", "app_pages/comment_ca_marche.py"]


@pytest.mark.parametrize("page", PAGES)
def test_page_sans_erreur(page):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.switch_page(page).run()
    assert not at.exception, at.exception


def test_accueil_compteurs():
    at = AppTest.from_file(APP, default_timeout=60).run()
    valeurs = {m.label: m.value for m in at.metric}
    assert valeurs["Persos"] == "218" and valeurs["dont offerts (free)"] == "37"
    assert valeurs["Effets reconnus"] == "59"
