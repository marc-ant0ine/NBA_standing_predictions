"""
Calcule les notes Elo et les probabilités de victoire à domicile
pour les matchs NBA. Distingue matchs neutres et bulle COVID.
"""



import numpy as np
import pandas as pd



K, BASE, REVERSION = 20, 1500, 0.25

def charger_matchs(chemin="data/processed/matchs.csv", saison_max=None):
    matchs = pd.read_csv(chemin, dtype={"GAME_ID": str, "SEASON_ID": str})
    matchs["GAME_DATE"] = pd.to_datetime(matchs["GAME_DATE"])
    if saison_max is not None:
        matchs = matchs[matchs["SEASON_ID"] <= saison_max].reset_index(drop=True)
    saison = matchs[matchs["SEASON_ID"] == "22019"]
    dates = saison["GAME_DATE"].drop_duplicates().sort_values()
    ecarts = dates.diff()
    reprise = dates[ecarts == ecarts.max()].iloc[0]

    matchs["BULLE"] = (matchs["SEASON_ID"] == "22019") & (matchs["GAME_DATE"] >= reprise)
    matchs["SANS_AVANTAGE"] = matchs["NEUTRE"] | matchs["BULLE"]
    return matchs


def proba_victoire(elo_dom, elo_ext, sans_avantage, H):
    ecart = elo_dom - elo_ext + (0 if sans_avantage else H)
    return 1 / (1 + 10 ** (-ecart / 400))


def calculer_elo(matchs, K, REVERSION, H):
    matchs = matchs.sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True)
    elo, saison_prec = {}, None
    probas, elos_dom, elos_ext = [], [], []

    for m in matchs.itertuples():
        if m.SEASON_ID != saison_prec:
            if saison_prec is not None:
                elo = {t: BASE + (r - BASE) * (1 - REVERSION) for t, r in elo.items()}
            saison_prec = m.SEASON_ID

        r_dom = elo.get(m.TEAM_ID_dom, BASE)
        r_ext = elo.get(m.TEAM_ID_ext, BASE)
        elos_dom.append(r_dom)              
        elos_ext.append(r_ext)

        p = proba_victoire(r_dom, r_ext, m.SANS_AVANTAGE, H)
        probas.append(p)

        delta = K * ((1.0 if m.DOM_GAGNE else 0.0) - p)
        elo[m.TEAM_ID_dom] = r_dom + delta
        elo[m.TEAM_ID_ext] = r_ext - delta

    matchs["ELO_DOM"], matchs["ELO_EXT"], matchs["P_DOM_ELO"] = elos_dom, elos_ext, probas
    return matchs, elo


def log_loss(y, p):
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))


if __name__ == "__main__":
    # 1. Charger les données
    matchs = pd.read_csv("data/processed/matchs.csv", dtype={"GAME_ID": str, "SEASON_ID": str})
    matchs["GAME_DATE"] = pd.to_datetime(matchs["GAME_DATE"])
    print(f"Matchs chargés : {matchs.shape}")

    # 2. Définir NEUTRE (10 matchs)
  
    print(f"Matchs neutres : {matchs['NEUTRE'].sum()}")

    # 3. Repérer la bulle
    saison = matchs[matchs["SEASON_ID"] == "22019"]
    dates = saison["GAME_DATE"].drop_duplicates().sort_values()
    ecarts = dates.diff()
    reprise = dates[ecarts == ecarts.max()].iloc[0]
    print(f"Plus grand trou : {ecarts.max().days} jours | reprise le {reprise.date()}")

    matchs["BULLE"] = (matchs["SEASON_ID"] == "22019") & (matchs["GAME_DATE"] >= reprise)
    print(f"Matchs de la bulle : {matchs['BULLE'].sum()}")

    matchs["SANS_AVANTAGE"] = matchs["NEUTRE"] | matchs["BULLE"]
    print(f"Matchs sans avantage : {matchs['SANS_AVANTAGE'].sum()}")

    # 4. Calculer H sur les matchs normaux
    normaux = matchs[~matchs["SANS_AVANTAGE"]]
    p_dom = normaux["DOM_GAGNE"].mean()
    H = 400 * np.log10(p_dom / (1 - p_dom))
    print(f"p_dom = {p_dom:.4f}, H = {H:.2f}")

    # 5. Calculer les Elo
    matchs_avec_elo, elo_final = calculer_elo(matchs, K=K, REVERSION=REVERSION, H=H)

    # 6. Évaluer
    test = matchs_avec_elo[matchs_avec_elo["SEASON_ID"] != "22015"]
    ll_elo = log_loss(test["DOM_GAGNE"], test["P_DOM_ELO"])
    ll_const = log_loss(test["DOM_GAGNE"], np.full(len(test), p_dom))
    print(f"Log loss Elo      : {ll_elo:.4f}")
    print(f"Log loss constante : {ll_const:.4f}")
    print(f"Gain              : {ll_const - ll_elo:.4f}")

    # 7. Part de victoires dans la bulle
    part_bulle = matchs[matchs["BULLE"]]["DOM_GAGNE"].mean()
    err = np.sqrt(0.25 / matchs["BULLE"].sum())
    print(f"Part victoires bulle : {part_bulle:.4f} ± {err:.4f}")

    

    # 8. Sauvegarder
    matchs_avec_elo.to_csv("data/processed/matchs_avec_elo.csv", index=False)
    print("\nSauvegardé.")

