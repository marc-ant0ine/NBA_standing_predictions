from itertools import product

import numpy as np
import pandas as pd

from Elo import charger_matchs, calculer_elo, log_loss

matchs = charger_matchs(saison_max="22025")
print("Matchs neutres :", matchs["NEUTRE"].sum(),
      "| bulle :", matchs["BULLE"].sum(),
      "| sans avantage :", matchs["SANS_AVANTAGE"].sum())   # attendu : 10, 88, 98

def evaluer(matchs, saisons, K, REVERSION, H):
    res, _ = calculer_elo(matchs, K=K, REVERSION=REVERSION, H=H)
    sous = res[res["SEASON_ID"].isin(saisons)]
    return log_loss(sous["DOM_GAGNE"].astype(float), sous["P_DOM_ELO"])




toutes = sorted(matchs["SEASON_ID"].unique())
valid = toutes[1:-2]      # de 2016-17 à 2023-24 : sans la saison de rodage ni les 2 saisons de test
test = toutes[-2:]        # 2024-25 et 2025-26 : on n'y touche qu'à la fin

# H estimé uniquement sur les saisons de validation
normaux_train = matchs[matchs["SEASON_ID"].isin(valid) & ~matchs["SANS_AVANTAGE"]]
p_train = normaux_train["DOM_GAGNE"].mean()
H_train = 400 * np.log10(p_train / (1 - p_train))

lignes = []
for K_, REV_, H_ in product([10, 20, 30, 40], [0.15, 0.25, 0.35], [30, 35, round(H_train, 1)]):
    lignes.append(dict(K=K_, REVERSION=REV_, H=H_, log_loss=evaluer(matchs, valid, K_, REV_, H_)))
resultats = pd.DataFrame(lignes).sort_values("log_loss")
print(resultats.head(5).to_string(index=False))

meilleur = resultats.loc[resultats["log_loss"].idxmin()]
ll_test = evaluer(matchs, test, meilleur["K"], meilleur["REVERSION"], meilleur["H"])
y_test = matchs[matchs["SEASON_ID"].isin(test)]["DOM_GAGNE"].astype(float)
ll_const = log_loss(y_test, np.full(len(y_test), p_train))
print(f"TEST  Elo {ll_test:.4f} | constante {ll_const:.4f}")
