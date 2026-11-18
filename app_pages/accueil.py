import streamlit as st

from app_commun import aide, donnees, recharger

st.title("⚔️ SAOUB : outil de persos")
st.write("Analyse les persos du jeu, crée-en de nouveaux et vérifie s'ils ressemblent à ce que font les développeurs.")

tout = donnees()
base = tout["tab"]["base"]
n_free = int(base["free"].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Persos", len(base), help="Tous les persos du fichier data/personnages_fr.json")
c2.metric("dont offerts (free)", n_free, help="Exclus des modèles de création : ils sont souvent plus faibles")
c3.metric("Effets reconnus", tout["df_eff"]["effet"].nunique())
c4.metric("Effets personnalisés", len(tout["effets_perso"]))

if len(tout["a_classer"]):
    st.warning(f"{len(tout['a_classer'])} phrase(s) de compétence ne sont reconnues par aucune règle. "
               "Tu peux en faire des effets personnalisés dans la page Création.")

st.divider()
gauche, droite = st.columns([12, 1], vertical_alignment="bottom")
gauche.subheader("Recharger les données")
with droite:
    aide("Recharger les données",
         quoi="Relit le fichier des persos et les effets personnalisés, puis règle à nouveau les moteurs.",
         sert="À utiliser après avoir remplacé data/personnages_fr.json (nouveaux persos du jeu).",
         lire="Les compteurs ci-dessus se mettent à jour. Compte environ 5 secondes.")
if st.button("🔄 Recharger"):
    recharger()
    st.rerun()
