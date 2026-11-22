import numpy as np
import pandas as pd

res = pd.read_csv("data/processed/backtest.csv")

# 1) Gain en victoires du modèle contre chaque référence, avec son erreur-type (écarts appariés)
lignes = []
for f, g in res.groupby("fraction"):
    err_modele = (g["V_att"] - g["V_finale"]).abs()
    for nom, col in [("rythme", "V_pace"), ("saison_prec", "V_prec")]:
        d = (g[col] - g["V_finale"]).abs() - err_modele          # > 0 : le modèle fait mieux
        lignes.append({"fraction": f, "contre": nom, "gain_victoires": d.mean(),
                       "erreur_type": d.std() / np.sqrt(len(d))})
gains = pd.DataFrame(lignes)
gains["z"] = gains["gain_victoires"] / gains["erreur_type"]
print(gains.round(3).to_string(index=False))

# 2) Score de Brier "de compétence" : 1 = parfait, 0 = pas mieux que la constante
lignes = []
for f, g in res.groupby("fraction"):
    lignes.append({
        "fraction": f,
        "BSS_top6": 1 - ((g["P_top6"] - g["O_top6"]) ** 2).mean() / ((0.4 - g["O_top6"]) ** 2).mean(),
        "BSS_top10": 1 - ((g["P_top10"] - g["O_top10"]) ** 2).mean() / ((10 / 15 - g["O_top10"]) ** 2).mean(),
    })
print()
print(pd.DataFrame(lignes).round(3).to_string(index=False))
print("\nÉquipes-saisons indépendantes par date :", res["saison"].nunique() * 30)
