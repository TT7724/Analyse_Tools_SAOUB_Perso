"""Étape a2 : à graine égale, les moteurs du paquet redonnent exactement les persos du notebook 03.
tests/reference/moteurs_notebook.json a été produit par les fonctions du notebook 03."""
import json
from pathlib import Path

import numpy as np
import pytest

from saoub.creation import creer_persos, preparer_tout
from saoub.donnees import STATS
from saoub.effets import ajouter_effet_perso, charger_effets_perso, liste_effets
from saoub.moteur_kit import ajuster_moteur_kit, lister_effets, proposer_kit, valider_moteur_kit
from saoub.moteur_stats import proposer_stats, valider_moteur_stats

REF = json.load(open(Path(__file__).parent / "reference" / "moteurs_notebook.json", encoding="utf-8"))


@pytest.fixture(scope="module")
def tout(tmp_path_factory):
    vide = tmp_path_factory.mktemp("registre") / "effets_personnalises.json"     # registre vide pour les tests
    return preparer_tout(chemin_effets_perso=vide)


def test_moteur_kit_identique(tout):
    mk = tout["moteur_kit"]
    assert list(mk["G"].columns) == REF["groupes"] and len(REF["groupes"]) == 30
    assert np.allclose(mk["a"], REF["a"])


def test_stats_identiques(tout):
    reglages = [(0, None, 1.0), (0, 0.6, 1.0), (3, None, 1.2)]
    for c, (g, d, t), attendu in zip(REF["contraintes"], reglages, REF["stats"]):
        res, infos = proposer_stats(tout["moteur"], c, n=5, graine=g, distance_min=d, temperature=t)
        assert res[STATS].values.tolist() == attendu


def test_kits_identiques(tout):
    reglages = [(0, 1.0), (0, 1.5), (2, 1.0)]
    for imposes, (g, t), attendu in zip(REF["imposes"], reglages, REF["kits"]):
        kits, infos = proposer_kit(tout["moteur_kit"], imposes, n=5, graine=g, temperature=t)
        assert kits == attendu


def test_creer_persos_identique(tout):
    persos, infos = creer_persos(tout["moteur"], tout["moteur_kit"],
                                 {"famille": "physique", "ATK": {"egal": 2800}, "SPD": {"pct_min": 80}},
                                 ["Dégâts continus"], n=5, graine=0)
    assert persos == REF["persos"]
    assert infos["stats"]["n_reels"] == 0 and infos["stats"]["alertes"]       # 0 vrai perso : une alerte
    assert infos["kit"]["n_reels"] == 47


def test_diversifier(tout):
    """Les 5 propositions diversifiées sont plus éloignées entre elles que les 5 normales (moyenne sur 10 graines)."""
    from saoub.moteur_stats import espace_z
    def ecart(res):
        Z = espace_z(tout["moteur"], res[STATS]); D = np.sqrt(((Z[:, None] - Z[None]) ** 2).sum(2))
        return D[np.triu_indices(len(Z), 1)].min()
    normal = np.mean([ecart(proposer_stats(tout["moteur"], {}, graine=g)[0]) for g in range(10)])
    divers = np.mean([ecart(proposer_stats(tout["moteur"], {}, graine=g, diversifier=True)[0]) for g in range(10)])
    assert divers > normal
    kits, _ = proposer_kit(tout["moteur_kit"], ["Dégâts continus"], graine=0, diversifier=True)
    assert len(kits) == 5 and all("Dégâts continus" in k for k in kits)


def test_effet_personnalise_dans_le_kit(tmp_path, tout):
    chemin = tmp_path / "effets_personnalises.json"
    connus = liste_effets(tout["df_eff"])["jeu"]
    ajouter_effet_perso("Poison renforcé", "Autres mécaniques", connus, se_comporte_comme="Dégâts continus", chemin=chemin)
    ajouter_effet_perso("Danse étrange", "Autres mécaniques", connus, chemin=chemin)
    mk = ajuster_moteur_kit(tout["tab"], effets_perso=charger_effets_perso(chemin))
    # « comme Dégâts continus » : même tirage que si on imposait Dégâts continus, nom remplacé
    kits_perso, infos = proposer_kit(mk, ["Poison renforcé"], graine=0)
    kits_ref, _ = proposer_kit(mk, ["Dégâts continus"], graine=0)
    assert kits_perso == [sorted("Poison renforcé" if e == "Dégâts continus" else e for e in k) for k in kits_ref]
    assert any("aucune donnée réelle" in a for a in infos["alertes"])
    # sans modèle : ajouté au kit, sans influence
    kits2, infos2 = proposer_kit(mk, ["Danse étrange"], graine=0)
    assert all("Danse étrange" in k for k in kits2)
    assert set(lister_effets(mk)["effet"]) >= {"Poison renforcé", "Danse étrange"}


def test_validations_moteurs(tout):
    v = valider_moteur_stats(tout["moteur"])
    assert v["ecart_corr_moyen"] < 0.05 and v["copies"] == 0
    vk = valider_moteur_kit(tout["moteur_kit"])
    assert vk["ecart_freq_moyen"] < 1.0 and vk["corr_liens"] > 0.6
