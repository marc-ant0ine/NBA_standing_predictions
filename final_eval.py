import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from Elo import charger_matchs, calculer_elo
from variables import construire_variables

matchs = construire_variables(charger_matchs(saison_max="22025"))
matchs, _ = calculer_elo(matchs, K=20, REVERSION=0.35, H=45.7)
matchs["ELO_DIFF"] = matchs["ELO_DOM"] - matchs["ELO_EXT"]
matchs["Y"] = matchs["DOM_GAGNE"].astype(float)
for c in ["SANS_AVANTAGE", "B2B_dom", "B2B_ext"]:
    matchs[c] = matchs[c].astype(float)

toutes = sorted(matchs["SEASON_ID"].unique())
train_final = toutes[1:9]      # 2016-17 -> 2023-24
test = toutes[9:]              # 2024-25 et 2025-26


def pertes(y, p):
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def pertes_modele(colonnes):
    tr = matchs[matchs["SEASON_ID"].isin(train_final)]
    ev = matchs[matchs["SEASON_ID"].isin(test)]
    modele = LogisticRegression(C=1e6, max_iter=1000).fit(tr[colonnes], tr["Y"])
    return pertes(ev["Y"].to_numpy(), modele.predict_proba(ev[colonnes])[:, 1])


ev = matchs[matchs["SEASON_ID"].isin(test)]
p_const = matchs[matchs["SEASON_ID"].isin(train_final)]["Y"].mean()

REF = ["ELO_DIFF", "SANS_AVANTAGE"]
FINAL = REF + ["B2B_dom", "B2B_ext"]

ll_const = pertes(ev["Y"].to_numpy(), np.full(len(ev), p_const)).mean()
ll_elo = pertes(ev["Y"].to_numpy(), ev["P_DOM_ELO"].to_numpy()).mean()
p_ref, p_final = pertes_modele(REF), pertes_modele(FINAL)

print(f"Constante ({p_const:.3f}) : {ll_const:.4f}")
print(f"Elo brut               : {ll_elo:.4f}")
print(f"Modèle sans B2B        : {p_ref.mean():.4f}")
print(f"Modèle final (+ B2B)   : {p_final.mean():.4f}")

d = p_ref - p_final
se = d.std() / np.sqrt(len(d))
print(f"\n[final vs sans B2B]  n = {len(d)}")
print(f"  gain {d.mean():+.4f} | erreur-type {se:.4f} | z = {d.mean() / se:+.2f}")
print(f"  IC95 : [{d.mean() - 1.96 * se:+.4f}, {d.mean() + 1.96 * se:+.4f}]")
