from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from nba_api.stats.static import teams as nba_teams

from db import se_connecter

_EQUIPES = nba_teams.get_teams()
ID_EQUIPE = {t["abbreviation"]: t["id"] for t in _EQUIPES}
NOM_EQUIPE = {t["abbreviation"]: t["full_name"] for t in _EQUIPES}

# Couleurs principales
COULEURS = {
    "ATL": "#C8102E", "BOS": "#007A33", "BKN": "#000000", "CHA": "#00788C", "CHI": "#CE1141",
    "CLE": "#860038", "DAL": "#00538C", "DEN": "#0E2240", "DET": "#C8102E", "GSW": "#1D428A",
    "HOU": "#CE1141", "IND": "#002D62", "LAC": "#C8102E", "LAL": "#552583", "MEM": "#5D76A9",
    "MIA": "#98002E", "MIL": "#00471B", "MIN": "#0C2340", "NOP": "#B4975A", "NYK": "#006BB6",
    "OKC": "#007AC1", "ORL": "#0077C0", "PHI": "#ED174C", "PHX": "#1D1160", "POR": "#E03A3E",
    "SAC": "#5A2D81", "SAS": "#C4CED4", "TOR": "#CE1141", "UTA": "#002B5C", "WAS": "#E31837",
}
COULEUR_PAR_DEFAUT = "#4B5563"


def url_logo(abbr):
    """Logo chargé depuis le serveur de la NBA au moment de l'affichage (rien n'est copié dans le projet)."""
    return f"https://cdn.nba.com/logos/nba/{ID_EQUIPE[abbr]}/primary/L/logo.svg"


def _luminance(couleur):
    r, g, b = (int(couleur[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


def couleur_texte(fond):
    return "#000000" if _luminance(fond) > 150 else "#FFFFFF"


def couleur_courbe(couleur):
    """Une courbe presque noire disparaît sur fond sombre : on la remplace par un gris."""
    return couleur if _luminance(couleur) > 40 else "#6B7280"

st.set_page_config(page_title="NBA : classement attendu", layout="wide")
st.title("NBA : classement attendu de la saison")


@st.cache_data(ttl=3600)
def charger_previsions():
    conn = se_connecter()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT jour, equipe, conference, victoires_actuelles, victoires_attendues,
               p_top6, p_playin, p_top10, p_seed1
        FROM prevision ORDER BY jour
    """)
    colonnes = [c[0] for c in cursor.description]
    lignes = cursor.fetchall()
    cursor.close()
    conn.close()
    df = pd.DataFrame(lignes, columns=colonnes)
    for c in df.columns[3:]:
        df[c] = df[c].astype(float)
    df["jour"] = pd.to_datetime(df["jour"])
    return df


@st.cache_data
def charger_backtest():
    for chemin in [Path("data/processed/backtest.csv"), Path("results/backtest.csv")]:
        if chemin.exists():
            return pd.read_csv(chemin)
    return None


with st.sidebar:
    st.header("Affichage")
    afficher_logos = st.checkbox("Afficher les logos", value=True)
    st.caption("Les logos appartiennent à la NBA et aux équipes : ils sont chargés depuis le serveur de la NBA "
               "au moment de l'affichage et ne sont pas copiés dans ce projet.")

prev = charger_previsions()
if prev.empty:
    st.warning("Aucune prévision enregistrée : lance d'abord simulation.py.")
    st.stop()

derniere = prev["jour"].max()
st.caption(f"Prévision calculée avec les matchs joués jusqu'au {derniere:%d/%m/%Y} (10 000 simulations de la fin de saison).")

onglet_classement, onglet_evolution, onglet_fiabilite = st.tabs(["Classements", "Évolution", "Fiabilité"])

# ---------------------------------------------------------------- Classements
with onglet_classement:
    colonnes = st.columns(2)
    for colonne, conf in zip(colonnes, ["Est", "Ouest"]):
        t = prev[(prev["jour"] == derniere) & (prev["conference"] == conf)].sort_values("victoires_attendues", ascending=False)
        affichage = pd.DataFrame({
            "Logo": [url_logo(a) for a in t["equipe"]],
            "Équipe": t["equipe"],
            "V actuelles": t["victoires_actuelles"].astype(int),
            "V attendues": t["victoires_attendues"].round(1),
            "Top 6 (%)": (t["p_top6"] * 100).round(1),
            "Barrage 7-10 (%)": (t["p_playin"] * 100).round(1),
            "Top 10 (%)": (t["p_top10"] * 100).round(1),
            "N°1 (%)": (t["p_seed1"] * 100).round(1),
        })
        config = {
            "Top 6 (%)": st.column_config.ProgressColumn("Top 6 (%)", min_value=0, max_value=100, format="%.0f"),
            "Top 10 (%)": st.column_config.ProgressColumn("Top 10 (%)", min_value=0, max_value=100, format="%.0f"),
        }
        if afficher_logos:
            config["Logo"] = st.column_config.ImageColumn("", width="small")
        else:
            affichage = affichage.drop(columns="Logo")

        def colorer(ligne):
            fond = COULEURS.get(ligne["Équipe"], COULEUR_PAR_DEFAUT)
            return [f"background-color: {fond}; color: {couleur_texte(fond)}; font-weight: 600" if c == "Équipe" else ""
                    for c in ligne.index]

        formats = {c: "{:.1f}" for c in ["V attendues", "Top 6 (%)", "Barrage 7-10 (%)", "Top 10 (%)", "N°1 (%)"]}
        colonne.subheader(f"Conférence {conf}")
        colonne.dataframe(affichage.style.apply(colorer, axis=1).format(formats), hide_index=True, column_config=config)

# ---------------------------------------------------------------- Évolution
with onglet_evolution:
    equipe = st.selectbox("Équipe", sorted(prev["equipe"].unique()), format_func=lambda a: f"{a} · {NOM_EQUIPE.get(a, a)}")
    couleur = COULEURS.get(equipe, COULEUR_PAR_DEFAUT)
    entete_logo, entete_nom = st.columns([1, 9])
    if afficher_logos:
        entete_logo.image(url_logo(equipe), width=70)
    entete_nom.markdown(f"<h2 style='color:{couleur_courbe(couleur)}; margin-top:0'>{NOM_EQUIPE.get(equipe, equipe)}</h2>",
                        unsafe_allow_html=True)

    e = prev[prev["equipe"] == equipe].set_index("jour")
    if len(e) < 2:
        st.info("Une seule prévision enregistrée pour l'instant : la courbe se construira jour après jour.")
    else:
        st.subheader("Probabilités (%)")
        st.line_chart((e[["p_top6", "p_top10"]] * 100).rename(columns={"p_top6": "Top 6", "p_top10": "Top 10"}),
                      color=[couleur_courbe(couleur), "#9CA3AF"])
        st.subheader("Victoires attendues")
        st.line_chart(e[["victoires_attendues"]].rename(columns={"victoires_attendues": "V attendues"}),
                      color=couleur_courbe(couleur))
    st.dataframe(e[["victoires_actuelles", "victoires_attendues", "p_top6", "p_top10"]].round(3))

# ---------------------------------------------------------------- Fiabilité
with onglet_fiabilite:
    bt = charger_backtest()
    if bt is None:
        st.warning("Aucun fichier de backtest trouvé (data/processed/backtest.csv ou results/backtest.csv) : lance backtest.py.")
    else:
        lignes = []
        for f, g in bt.groupby("fraction"):
            lignes.append({
                "Part de saison jouée": f"{int(f * 100)} %",
                "Erreur modèle": (g["V_att"] - g["V_finale"]).abs().mean(),
                "Erreur rythme actuel": (g["V_pace"] - g["V_finale"]).abs().mean(),
                "Erreur saison précédente": (g["V_prec"] - g["V_finale"]).abs().mean(),
                "Compétence top 6": 1 - ((g["P_top6"] - g["O_top6"]) ** 2).mean() / ((0.4 - g["O_top6"]) ** 2).mean(),
            })
        resume = pd.DataFrame(lignes)
        st.subheader("Erreur moyenne sur les victoires finales (en victoires)")
        st.bar_chart(resume.set_index("Part de saison jouée")[["Erreur modèle", "Erreur rythme actuel", "Erreur saison précédente"]])
        st.dataframe(resume.round(2), hide_index=True)

        bt = bt.copy()
        bt["classe"] = pd.cut(bt["P_top6"], [0, .1, .3, .5, .7, .9, 1.0], include_lowest=True)
        calib = bt.groupby("classe", observed=True).agg(n=("O_top6", "size"), annoncée=("P_top6", "mean"), observée=("O_top6", "mean"))
        calib.index = calib.index.astype(str)
        st.subheader("Calibration : probabilité annoncée de finir dans le top 6 contre fréquence observée")
        st.line_chart(calib[["annoncée", "observée"]])
        st.dataframe(calib.round(3))

        st.markdown(
            f"**À lire avec prudence** : {bt['saison'].nunique()} saisons, soit {bt['saison'].nunique() * 30} équipes-saisons "
            "indépendantes par date. L'avantage du modèle est surtout net en début de saison ; à partir de la moitié "
            "de la saison, il ne se distingue plus du rythme actuel."
        )
