import numpy as np
import pandas as pd
 
from Elo import charger_matchs, calculer_elo
from variables import construire_variables
 
matchs = construire_variables(charger_matchs(saison_max="22025"))
 
tab = (
    matchs.groupby(["B2B_dom", "B2B_ext"])["DOM_GAGNE"]
          .agg(n="size", part_dom="mean")
)
tab["erreur_type"] = np.sqrt(tab["part_dom"] * (1 - tab["part_dom"]) / tab["n"])
tab["IC95_bas"] = tab["part_dom"] - 1.96 * tab["erreur_type"]
tab["IC95_haut"] = tab["part_dom"] + 1.96 * tab["erreur_type"]
print(tab.round(4))
 
# 1) calculer l'Elo sur les matchs fusionnés (après les fusions REPOS/B2B)
matchs_f, _ = calculer_elo(matchs, K=20, REVERSION=0.35, H=45.7)
 
# 2) résidu = résultat observé - probabilité prédite par l'Elo
matchs_f["RESIDU"] = matchs_f["DOM_GAGNE"].astype(float) - matchs_f["P_DOM_ELO"]
 
# 3) moyenne du résidu par case B2B, avec effectif et erreur-type
res = (
    matchs_f.groupby(["B2B_dom", "B2B_ext"])["RESIDU"]
            .agg(n="size", residu_moyen="mean", residu_std="std")
)
res["erreur_type"] = res["residu_std"] / np.sqrt(res["n"])
res["IC95_bas"]  = res["residu_moyen"] - 1.96 * res["erreur_type"]
res["IC95_haut"] = res["residu_moyen"] + 1.96 * res["erreur_type"]
print(res.round(4).to_string())
 
# 4) résidu selon la durée du repos, pour chaque côté (à placer APRÈS la création de RESIDU)
for cote in ["dom", "ext"]:
    t = matchs_f.groupby(f"REPOS_{cote}_C")["RESIDU"].agg(n="size", residu_moyen="mean", residu_std="std")
    t["erreur_type"] = t["residu_std"] / np.sqrt(t["n"])
    t["IC95_bas"] = t["residu_moyen"] - 1.96 * t["erreur_type"]
    t["IC95_haut"] = t["residu_moyen"] + 1.96 * t["erreur_type"]
    print(f"\nRésidu selon le repos de l'équipe {cote.upper()} (plafonné) :")
    print(t.round(4).to_string())
