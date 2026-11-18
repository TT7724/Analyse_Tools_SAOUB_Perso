"""Point d'entrée de l'application. Lancement (depuis la racine du projet, venv activé) :
    streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="SAOUB : outil de persos", page_icon="⚔️", layout="wide")

pages = [
    st.Page("app_pages/accueil.py", title="Accueil", icon="🏠", default=True),
    st.Page("app_pages/graphiques.py", title="Graphiques", icon="📊"),
    st.Page("app_pages/creation.py", title="Création de perso", icon="🛠️"),
    st.Page("app_pages/verifier.py", title="Vérifier mon perso", icon="🔍"),
    st.Page("app_pages/comment_ca_marche.py", title="Comment ça marche ?", icon="📖"),
]
st.navigation(pages).run()
