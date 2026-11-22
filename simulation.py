import numpy as np
import pandas as pd
from nba_api.stats.static import teams
from sklearn.linear_model import LogisticRegression

from Elo import charger_matchs, calculer_elo
from variables import construire_variables
from db import se_connecter
from previsions import sauver_previsions
from calendrier_restant import charger_calendrier_restant, matchs_manquants, variables_restants

K, REVERSION, H = 20, 0.35, 45.7
N_SIMS = 10_000
SAISON_COURANTE = "22026"
BASE = 1500

# À vérifier à partir d'une source officielle avant publication
EST = {"ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND", "MIA", "MIL", "NYK", "ORL", "PHI", "TOR", "WAS"}
CARACTERISTIQUES = ["ELO_DIFF", "SANS_AVANTAGE", "B2B_dom", "B2B_ext"]


def entrainer_modele(matchs_f):
    """Modèle entraîné sur toutes les saisons terminées (2016-17 à 2025-26)."""
    entrainement = matchs_f[matchs_f["SEASON_ID"].between("22016", "22025")]
    X = entrainement[CARACTERISTIQUES].astype(float)
    modele = LogisticRegression(C=1e6, max_iter=1000).fit(X, entrainement["DOM_GAGNE"].astype(float))
    return modele.intercept_[0], modele.coef_[0]          # b0, [b_elo, b_sans, b_b2b_dom, b_b2b_ext]


def simuler(elo0, victoires0, jeu, b0, coefs, n_sims, rng):
    """Boucle sur les matchs, vectorisée sur les simulations."""
    b_elo, b_sans, b_bd, b_be = coefs
    elo = np.tile(elo0, (n_sims, 1))                      # (n_sims, 30)
    vict = np.tile(victoires0, (n_sims, 1)).astype(float)

    for g in jeu.itertuples(index=False):
        diff = elo[:, g.i] - elo[:, g.j]
        logit = b0 + b_elo * diff + b_sans * g.SANS + b_bd * g.B2B_dom + b_be * g.B2B_ext
        p_modele = 1 / (1 + np.exp(-logit))                                   
        dom_gagne = rng.random(n_sims) < p_modele

        p_elo = 1 / (1 + 10 ** (-(diff + (0 if g.SANS else H)) / 400))    # probabilité de l'ELO : sert à mettre à jour
        delta = K * (dom_gagne.astype(float) - p_elo)                                       
        elo[:, g.i] += delta
        elo[:, g.j] -= delta

        vict[:, g.i] += dom_gagne
        vict[:, g.j] += ~dom_gagne
    return elo, vict


def completer_manquants(vict, elo, manque, b0, b_elo, rng):
    """Matchs absents du calendrier : contre un adversaire moyen, un à domicile puis un à l'extérieur."""
    n_sims = vict.shape[0]
    for t, m in enumerate(manque):
        for k in range(m):
            if k % 2 == 0:                                               # à domicile
                p = 1 / (1 + np.exp(-(b0 + b_elo * (elo[:, t] - BASE))))
            else:                                                        # à l'extérieur
                p = 1 - 1 / (1 + np.exp(-(b0 + b_elo * (BASE - elo[:, t]))))
            vict[:, t] += rng.random(n_sims) < p
    return vict


def probabilites_classement(vict, indices, rng):
    s = vict[:, indices] + rng.random((vict.shape[0], len(indices))) * 0.5      # bruit < 1 : égalités départagées au hasard
    rang = np.argsort(np.argsort(-s, axis=1), axis=1) + 1                                         
    return pd.DataFrame({
        "V_attendues": vict[:, indices].mean(axis=0),
        "P_top6": (rang <= 6).mean(axis=0),
        "P_playin": ((rang >= 7) & (rang <= 10)).mean(axis=0),
        "P_top10": (rang <= 10).mean(axis=0),
        "P_seed1": (rang == 1).mean(axis=0),
    })


def main(graine=42, sauver=True):
    matchs = construire_variables(charger_matchs())
    matchs_f, elo_final = calculer_elo(matchs, K=K, REVERSION=REVERSION, H=H)
    matchs_f["ELO_DIFF"] = matchs_f["ELO_DOM"] - matchs_f["ELO_EXT"]
    b0, coefs = entrainer_modele(matchs_f)
    print(f"Modèle : b0 = {b0:.3f} | b_elo = {coefs[0]:.5f} | b_sans = {coefs[1]:+.3f} | b_b2b_dom = {coefs[2]:+.3f} | b_b2b_ext = {coefs[3]:+.3f}")

    joues = matchs[matchs["SEASON_ID"] == SAISON_COURANTE]
    restants = charger_calendrier_restant(joues)
    v = variables_restants(joues, restants)

    ids = sorted(elo_final)
    pos = {t: k for k, t in enumerate(ids)}
    abbr = {t["id"]: t["abbreviation"] for t in teams.get_teams()}

    elo0 = np.array([elo_final[t] for t in ids])
    v_dom = joues.groupby("TEAM_ID_dom")["DOM_GAGNE"].sum()
    v_ext = (~joues["DOM_GAGNE"]).groupby(joues["TEAM_ID_ext"]).sum()
    victoires0 = v_dom.add(v_ext, fill_value=0).reindex(ids).fillna(0).to_numpy()

    manque = matchs_manquants(joues, restants, ids).to_numpy()

    jeu = pd.DataFrame({"i": v["TEAM_ID_dom"].map(pos), "j": v["TEAM_ID_ext"].map(pos),
                        "SANS": v["SANS_AVANTAGE"].astype(float),
                        "B2B_dom": v["B2B_dom"].astype(float), "B2B_ext": v["B2B_ext"].astype(float)})

    rng = np.random.default_rng(graine)
    elo, vict = simuler(elo0, victoires0, jeu, b0, coefs, N_SIMS, rng)
    vict = completer_manquants(vict, elo, manque, b0, coefs[0], rng)

    est = [k for k, t in enumerate(ids) if abbr[t] in EST]
    ouest = [k for k in range(len(ids)) if k not in est]
    sorties = []
    for nom, indices in [("Est", est), ("Ouest", ouest)]:
        t = probabilites_classement(vict, indices, rng)
        t.insert(0, "Equipe", [abbr[ids[k]] for k in indices])
        t.insert(1, "Conf", nom)
        t.insert(2, "V_actuelles", victoires0[indices])
        sorties.append(t.sort_values("V_attendues", ascending=False))
    resultat = pd.concat(sorties, ignore_index=True)

    for nom in ["Est", "Ouest"]:
        r = resultat[resultat["Conf"] == nom]
        print(f"\n=== {nom} (somme des P_top6 = {r['P_top6'].sum():.3f} ; P_top10 = {r['P_top10'].sum():.3f} ; P_seed1 = {r['P_seed1'].sum():.3f}) ===")
        print(r.drop(columns="Conf").round(3).head(6).to_string(index=False))
    if sauver:
        as_of = joues["GAME_DATE"].max().date()
        conn = se_connecter()
        n = sauver_previsions(conn, resultat, as_of)
        conn.close()
        print(f"\n{n} prévisions enregistrées (données au {as_of}).")
    return resultat


if __name__ == "__main__":
    main()
