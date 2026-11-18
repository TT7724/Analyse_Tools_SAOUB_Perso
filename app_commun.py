"""Outils partagés par toutes les pages de l'application : chargement en cache, bouton d'aide « ? », affichage d'un rapport."""
import os
import time

import streamlit as st

from saoub.creation import preparer_tout
from saoub.effets import CHEMIN_EFFETS_PERSO, phrases_a_classer
from saoub.export import CHEMIN_NOUVEAUX
from saoub.interface import lecture_distance


def chemins():
    """Fichiers modifiables par l'application. Les variables d'environnement servent aux tests (dossier temporaire)."""
    return dict(effets=os.environ.get("SAOUB_EFFETS_PERSO", str(CHEMIN_EFFETS_PERSO)),
                nouveaux=os.environ.get("SAOUB_NOUVEAUX", str(CHEMIN_NOUVEAUX)))


@st.cache_resource(show_spinner="Chargement des persos et réglage des moteurs (≈ 5 s)…")
def _charger(chemin_effets):
    tout = preparer_tout(chemin_effets_perso=chemin_effets)
    tout["a_classer"] = phrases_a_classer(tout["df_eff"], tout["persos"])
    tout["version"] = time.time()          # change à chaque rechargement : invalide les résultats en cache
    return tout


def donnees():
    """Lu UNE fois, puis gardé en mémoire tant que l'application tourne (partagé entre tous les utilisateurs).
    Après un changement de JSON ou d'effet personnalisé : recharger() puis st.rerun()."""
    return _charger(chemins()["effets"])


def recharger():
    _charger.clear()


def aide(titre, quoi, sert, lire, limites=None):
    """Bouton « ? » : quel outil/graphique, à quoi il sert, comment le lire (et ses limites)."""
    with st.popover("?", help=f"Aide : {titre}"):
        st.markdown(f"#### {titre}")
        st.markdown(f"**C'est quoi ?** {quoi}")
        st.markdown(f"**À quoi ça sert ?** {sert}")
        st.markdown(f"**Comment le lire ?** {lire}")
        if limites:
            st.markdown(f"**Limites :** {limites}")


def titre_avec_aide(titre, **textes_aide):
    """Titre de section avec son bouton « ? » aligné à droite."""
    gauche, droite = st.columns([12, 1], vertical_alignment="bottom")
    gauche.subheader(titre)
    with droite:
        aide(titre, **textes_aide)


AIDE_RAPPORT = dict(
    quoi="Le diagnostic d'un perso : chaque stat et chaque effet comparés aux 181 vrais persos non offerts (niveau 100).",
    sert="Repérer ce qui sort de l'ordinaire avant de proposer le perso à ton groupe.",
    lire="Percentile : 90 = plus haut que 90 % des vrais persos. Plage observée ✗ : valeur jamais vue. Grille ✗ : "
         "hors des pas habituels (HP 75, ATK/MATK 25, DEF/MDEF 15), vrai pour 21 à 32 % des vrais persos. "
         "Distance des stats : en général 0,41 entre vrais persos, 95 % sous 0,78. Distance du kit (Jaccard, de 0 à 1) : "
         "0 = mêmes groupes d'effets. ⚠ = point à vérifier, pas forcément une erreur.",
    limites="Aucune donnée de combat : « rien d'anormal » veut dire « ressemble aux vrais persos », pas « équilibré ».")


def afficher_rapport(r):
    """Affiche le rapport de saoub.validation.valider_perso."""
    gauche, droite = st.columns(2)
    with gauche:
        st.markdown(f"**Stats** · {r['famille']}")
        st.dataframe(r["stats"], hide_index=True, width="stretch",
                     column_config={"percentile": st.column_config.ProgressColumn(
                         "percentile", min_value=0, max_value=100, format="%d")})
        st.markdown(f"Plus proche vrai perso : **{r['plus_proche']}** (distance {r['distance']:.2f} : "
                    f"{lecture_distance(r['distance'])})")
    with droite:
        t = r["tailles_reference"]
        st.markdown(f"**Kit** · {r['taille']} élément(s) (vrais kits : médiane {t['mediane']}, de {t['min']} à {t['max']})")
        if len(r["kit"]):
            st.dataframe(r["kit"], hide_index=True, width="stretch",
                         column_config={"élément": st.column_config.TextColumn("élément", width="large"),
                                        "vrais_persos_avec": st.column_config.NumberColumn("persos", width="small"),
                                        "groupe_de_calcul": st.column_config.TextColumn("groupe de calcul")})
        st.markdown(f"Kit réel le plus proche : **{r['kit_proche']}** (distance {r['distance_kit']:.2f} ; "
                    f"entre vrais kits : médiane {r['distance_kit_reference']['mediane']:.2f})")
    if r["alertes"]:
        for alerte in r["alertes"]:
            st.warning(alerte)
    else:
        st.success("Rien d'anormal par rapport aux persos existants.")
