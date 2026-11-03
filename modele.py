import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from Elo import charger_matchs, calculer_elo, log_loss
from variables import construire_variables


matchs = construire_variables(charger_matchs(saison_max="22025"))
matchs, _ = calculer_elo(matchs, K=20, REVERSION=0.35, H=45.7)

matchs["ELO_DIFF"] = matchs["ELO_DOM"] - matchs["ELO_EXT"]
matchs["Y"] = matchs["DOM_GAGNE"].astype(float)
for c in ["SANS_AVANTAGE", "B2B_dom", "B2B_ext"]:
    matchs[c] = matchs[c].astype(float)

matchs["B2B_both"] = matchs["B2B_dom"] * matchs["B2B_ext"]


toutes = sorted(matchs["SEASON_ID"].unique())
train = toutes[1:7]       # 2016-17 -> 2021-22
valid = toutes[7:9]       # 2022-23, 2023-24
test  = toutes[9:]        # 2024-25, 2025-26 


def ll_modele(colonnes, apprentissage, evaluation):
    tr = matchs[matchs["SEASON_ID"].isin(apprentissage)]
    ev = matchs[matchs["SEASON_ID"].isin(evaluation)]
    modele = LogisticRegression(C=1e6, max_iter=1000)
    modele.fit(tr[colonnes], tr["Y"])
    p = modele.predict_proba(ev[colonnes])[:, 1]
    return log_loss(ev["Y"], p)

def pertes_modele(colonnes, apprentissage, evaluation):
    tr = matchs[matchs["SEASON_ID"].isin(apprentissage)]
    ev = matchs[matchs["SEASON_ID"].isin(evaluation)]
    modele = LogisticRegression(C=1e6, max_iter=1000).fit(tr[colonnes], tr["Y"])
    p = np.clip(modele.predict_proba(ev[colonnes])[:, 1], 1e-15, 1 - 1e-15)
    y = ev["Y"].to_numpy()
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


va = matchs[matchs["SEASON_ID"].isin(valid)]
ll_elo = log_loss(va["Y"], va["P_DOM_ELO"])
print(f"Elo brut sur la validation : {ll_elo:.4f}\n")


jeux = {
    "Elo seul":                     ["ELO_DIFF"],
    "+ sans avantage":              ["ELO_DIFF", "SANS_AVANTAGE"],
    "+ back-to-back":               ["ELO_DIFF", "SANS_AVANTAGE", "B2B_dom", "B2B_ext"],
    "+ repos séparés (plafonnés)":  ["ELO_DIFF", "SANS_AVANTAGE", "REPOS_dom_C", "REPOS_ext_C"],
    "+ avantage repos (plafonné)":  ["ELO_DIFF", "SANS_AVANTAGE", "AVANTAGE_REPOS"],
}

for nom, colonnes in jeux.items():
    ll = ll_modele(colonnes, train, valid)
    print(f"{nom:30s} log loss validation = {ll:.4f}  (écart avec l'Elo brut : {ll_elo - ll:+.4f})")

    print()


def proba_modele(colonnes, apprentissage, evaluation):
    tr = matchs[matchs["SEASON_ID"].isin(apprentissage)]
    ev = matchs[matchs["SEASON_ID"].isin(evaluation)]
    modele = LogisticRegression(C=1e6, max_iter=1000).fit(tr[colonnes], tr["Y"])
    return ev["Y"].to_numpy(), modele.predict_proba(ev[colonnes])[:, 1]

def table_calibration(y, p, n_classes=10):
    df = pd.DataFrame({"p": p, "y": y})
    df["classe"] = pd.qcut(df["p"], n_classes, duplicates="drop")
    t = df.groupby("classe", observed=True).agg(n=("y", "size"), p_moyen=("p", "mean"), freq_obs=("y", "mean"))
    t["ecart"] = t["freq_obs"] - t["p_moyen"]
    t["erreur_type"] = np.sqrt(t["freq_obs"] * (1 - t["freq_obs"]) / t["n"])
    return t.round(4)

FINAL = ["ELO_DIFF", "SANS_AVANTAGE", "B2B_dom", "B2B_ext"]
y, p = proba_modele(FINAL, train, valid)
print(table_calibration(y, p).to_string())

def comparer(nom_ref, cols_ref, nom_new, cols_new):
    d = pertes_modele(cols_ref, train, valid) - pertes_modele(cols_new, train, valid)
    se = d.std() / np.sqrt(len(d))
    print(f"[{nom_new} vs {nom_ref}]  n = {len(d)}")
    print(f"  gain {d.mean():+.4f} | erreur-type {se:.4f} | z = {d.mean() / se:+.2f}")
    print(f"  IC95 : [{d.mean() - 1.96 * se:+.4f}, {d.mean() + 1.96 * se:+.4f}]")

BASE = ["ELO_DIFF", "SANS_AVANTAGE", "B2B_dom", "B2B_ext"]
comparer("+ back-to-back", BASE, "+ forme (deux colonnes)", BASE + ["FORME_dom_C", "FORME_ext_C"])
comparer("+ back-to-back", BASE, "+ forme (écart)", BASE + ["FORME_DIFF"])
