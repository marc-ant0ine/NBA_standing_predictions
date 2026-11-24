import numpy as np
import pandas as pd
from nba_api.stats.static import teams
from sklearn.linear_model import LogisticRegression

from Elo import charger_matchs, calculer_elo
from variables import construire_variables
import simulation as S

N_SIMS = 2_000
SAISONS_BACKTEST = ["22023", "22024", "22025"]     
FRACTIONS = [0.10, 0.25, 0.50, 0.75, 0.90]          


def entrainer_jusqua(matchs_f, saison):
    """Régression logistique entraînée sur les saisons STRICTEMENT antérieures à `saison`."""
    ent = matchs_f[(matchs_f["SEASON_ID"] >= "22016") & (matchs_f["SEASON_ID"] < saison)]
    X = ent[S.CARACTERISTIQUES].astype(float)
    m = LogisticRegression(C=1e6, max_iter=1000).fit(X, ent["DOM_GAGNE"].astype(float))
    return m.intercept_[0], m.coef_[0]


def part_places(victoires, k):
    """Part des k premières places revenant à chaque équipe (égalités départagées au hasard)."""
    sortie = np.zeros(len(victoires))
    deja = 0
    for v in sorted(set(victoires), reverse=True):
        groupe = np.where(victoires == v)[0]
        libres = max(min(k - deja, len(groupe)), 0)                                          # 1er blanc : places encore libres, au plus len(groupe), jamais négatif
        sortie[groupe] = libres / len(groupe)
        deja += len(groupe)
    return sortie


def victoires_par_equipe(sous, ids):
    v_dom = sous.groupby("TEAM_ID_dom")["DOM_GAGNE"].sum()
    v_ext = (~sous["DOM_GAGNE"]).groupby(sous["TEAM_ID_ext"]).sum()
    return v_dom.add(v_ext, fill_value=0).reindex(ids).fillna(0).to_numpy()


def matchs_par_equipe(sous, ids):
    n = sous["TEAM_ID_dom"].value_counts().add(sous["TEAM_ID_ext"].value_counts(), fill_value=0)
    return n.reindex(ids).fillna(0).to_numpy()

def brier(P, O):
    return np.mean((np.asarray(P, dtype=float) - np.asarray(O, dtype=float)) ** 2)

def backtest(matchs, matchs_f, ids, pos, abbr, est, ouest, rng):
    lignes = []
    for saison in SAISONS_BACKTEST:
        b0, coefs = entrainer_jusqua(matchs_f, saison)
        sai = matchs[matchs["SEASON_ID"] == saison].sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True)
        finales = victoires_par_equipe(sai, ids)
        precedente = victoires_par_equipe(matchs[matchs["SEASON_ID"] == str(int(saison) - 1)], ids)

        for f in FRACTIONS:
            date_coupure = sai.loc[int(f * len(sai)), "GAME_DATE"]
            joues = sai[sai["GAME_DATE"] < date_coupure]
            restants = sai[sai["GAME_DATE"] >= date_coupure]

            _, elo_fin = calculer_elo(matchs[matchs["GAME_DATE"] < date_coupure], K=S.K, REVERSION=S.REVERSION, H=S.H)
            elo0 = np.array([elo_fin[t] for t in ids])
            victoires0 = victoires_par_equipe(joues, ids)
            pace = victoires0 * 82 / np.maximum(matchs_par_equipe(joues, ids), 1)

            jeu = pd.DataFrame({"i": restants["TEAM_ID_dom"].map(pos).to_numpy(), "j": restants["TEAM_ID_ext"].map(pos).to_numpy(),
                                "SANS": restants["SANS_AVANTAGE"].astype(float).to_numpy(),
                                "B2B_dom": restants["B2B_dom"].astype(float).to_numpy(),
                                "B2B_ext": restants["B2B_ext"].astype(float).to_numpy()})
            _, vict = S.simuler(elo0, victoires0, jeu, b0, coefs, N_SIMS, rng)

            for nom, indices in [("Est", est), ("Ouest", ouest)]:
                t = S.probabilites_classement(vict, indices, rng)
                o6, o10 = part_places(finales[indices], 6), part_places(finales[indices], 10)
                for r, k in enumerate(indices):
                    lignes.append(dict(saison=saison, fraction=f, Equipe=abbr[ids[k]], Conf=nom,
                                       V_att=t["V_attendues"].iloc[r], V_pace=pace[k], V_prec=precedente[k], V_finale=finales[k],
                                       P_top6=t["P_top6"].iloc[r], P_top10=t["P_top10"].iloc[r], O_top6=o6[r], O_top10=o10[r]))
    return pd.DataFrame(lignes)


def resume(res):
    lignes = []
    for f, g in res.groupby("fraction"):
        lignes.append({
            "fraction": f,
            "MAE_modele": (g["V_att"] - g["V_finale"]).abs().mean(),
            "MAE_rythme": (g["V_pace"] - g["V_finale"]).abs().mean(),
            "MAE_saison_prec": (g["V_prec"] - g["V_finale"]).abs().mean(),
            "Brier_top6": brier(g["P_top6"], g["O_top6"]),
            "Brier_top6_const": brier(0.4, g["O_top6"]),
            "Brier_top10": brier(g["P_top10"], g["O_top10"]),
            "Brier_top10_const": brier(10 / 15, g["O_top10"]),
        })
    return pd.DataFrame(lignes).round(3)


def main():
    matchs = construire_variables(charger_matchs())
    matchs_f, _ = calculer_elo(matchs, K=S.K, REVERSION=S.REVERSION, H=S.H)
    matchs_f["ELO_DIFF"] = matchs_f["ELO_DOM"] - matchs_f["ELO_EXT"]

    ids = sorted(set(matchs["TEAM_ID_dom"]) | set(matchs["TEAM_ID_ext"]))
    pos = {t: k for k, t in enumerate(ids)}
    abbr = {t["id"]: t["abbreviation"] for t in teams.get_teams()}
    est = [k for k, t in enumerate(ids) if abbr[t] in S.EST]
    ouest = [k for k in range(len(ids)) if k not in est]

    res = backtest(matchs, matchs_f, ids, pos, abbr, est, ouest, np.random.default_rng(42))
    for (saison, f, conf), g in res.groupby(["saison", "fraction", "Conf"]):
        assert np.isclose(g["O_top6"].sum(), 6) and np.isclose(g["O_top10"].sum(), 10), "les résultats réels ne somment pas à 6 / 10"
        assert np.isclose(g["P_top6"].sum(), 6) and np.isclose(g["P_top10"].sum(), 10), "les probabilités ne somment pas à 6 / 10"
    print(resume(res).to_string(index=False))

    res["classe"] = pd.cut(res["P_top6"], [0, .1, .3, .5, .7, .9, 1.0], include_lowest=True)
    print("\nCalibration de P_top6 (toutes dates et saisons confondues)")
    print(res.groupby("classe", observed=True).agg(n=("O_top6", "size"), P_moyenne=("P_top6", "mean"), frequence_reelle=("O_top6", "mean")).round(3).to_string())
    res.to_csv("data/processed/backtest.csv", index=False)
    return res


if __name__ == "__main__":
    main()
