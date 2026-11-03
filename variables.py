import numpy as np
import pandas as pd

CAP = 4          # repos plafonné : "4 jours ou plus" forme une seule catégorie


def table_equipe_match(matchs):
    dom = matchs[["GAME_ID", "GAME_DATE", "SEASON_ID", "TEAM_ID_dom", "DOM_GAGNE"]].rename(
        columns={"TEAM_ID_dom": "TEAM_ID", "DOM_GAGNE": "GAGNE"})
    ext = matchs[["GAME_ID", "GAME_DATE", "SEASON_ID", "TEAM_ID_ext", "DOM_GAGNE"]].rename(
        columns={"TEAM_ID_ext": "TEAM_ID"})
    ext["GAGNE"] = 1 - ext["DOM_GAGNE"]
    ext = ext.drop(columns="DOM_GAGNE")
    return pd.concat([dom, ext], ignore_index=True).sort_values(
        ["TEAM_ID", "GAME_DATE", "GAME_ID"]).reset_index(drop=True)


def ajouter_repos(em):
    g = em.groupby(["TEAM_ID", "SEASON_ID"])
    em["REPOS"] = g["GAME_DATE"].diff().dt.days
    em["BACK_TO_BACK"] = em["REPOS"] == 1
    return em


def ajouter_forme(em, N=10):
    g = em.groupby(["TEAM_ID", "SEASON_ID"])["GAGNE"]
    em["FORME"] = g.transform(lambda s: s.shift(1).rolling(N, min_periods=3).mean())
    return em


def test_fuite(em, N=10):
    """True si la forme d'un match ne dépend PAS du résultat de ce match."""
    a = ajouter_forme(em.copy(), N)
    b = em.copy()
    i = b.index[100]
    b.loc[i, "GAGNE"] = 1 - b.loc[i, "GAGNE"]      # on inverse le résultat de CE match
    b = ajouter_forme(b, N)
    return bool(np.isclose(a.loc[i, "FORME"], b.loc[i, "FORME"], equal_nan=True))


def construire_variables(matchs):
    n_matchs = len(matchs)
    em = ajouter_forme(ajouter_repos(table_equipe_match(matchs)))

    # --- Fusion 1 : côté DOMICILE ---
    matchs = matchs.merge(
        em[["GAME_ID", "TEAM_ID", "REPOS", "BACK_TO_BACK", "FORME"]].rename(
            columns={
                "TEAM_ID": "TEAM_ID_dom",
                "REPOS": "REPOS_dom",
                "BACK_TO_BACK": "B2B_dom",
                "FORME": "FORME_dom",
            }
        ),
        on=["GAME_ID", "TEAM_ID_dom"],
        how="left",
        validate="one_to_one",
    )

    # --- Fusion 2 : côté EXTÉRIEUR ---
    matchs = matchs.merge(
        em[["GAME_ID", "TEAM_ID", "REPOS", "BACK_TO_BACK", "FORME"]].rename(
            columns={
                "TEAM_ID": "TEAM_ID_ext",
                "REPOS": "REPOS_ext",
                "BACK_TO_BACK": "B2B_ext",
                "FORME": "FORME_ext",
            }
        ),
        on=["GAME_ID", "TEAM_ID_ext"],
        how="left",
        validate="one_to_one",
    )

    # --- Plafonnement du repos ---
    for cote in ["dom", "ext"]:
        matchs[f"REPOS_{cote}_C"] = matchs[f"REPOS_{cote}"].fillna(CAP).clip(upper=CAP)
    matchs["AVANTAGE_REPOS"] = matchs["REPOS_dom_C"] - matchs["REPOS_ext_C"]

    # --- Forme : sans historique (début de saison), on suppose une équipe moyenne ---
    for cote in ["dom", "ext"]:
        matchs[f"FORME_{cote}_C"] = matchs[f"FORME_{cote}"].fillna(0.5)
    matchs["FORME_DIFF"] = matchs["FORME_dom_C"] - matchs["FORME_ext_C"]

    # --- Contrôles ---
    assert len(matchs) == n_matchs, "le nombre de matchs a changé"
    assert matchs["B2B_dom"].notna().all() and matchs["B2B_ext"].notna().all(), \
        "des matchs n'ont pas trouvé leur ligne dans em"
    assert matchs[["REPOS_dom_C", "REPOS_ext_C", "FORME_dom_C", "FORME_ext_C"]].isna().sum().sum() == 0, "NaN restants"
    return matchs


if __name__ == "__main__":
    from Elo import charger_matchs

    matchs = charger_matchs()
    em = ajouter_repos(table_equipe_match(matchs))

    print("lignes équipe-match :", len(em))                    
    print("REPOS manquants     :", em["REPOS"].isna().sum())    
    print("REPOS maximum       :", em["REPOS"].max())
    print("part de back-to-back:", em["BACK_TO_BACK"].mean())
    print(em["REPOS"].value_counts().sort_index().head(8))

    matchs = construire_variables(matchs)
    print("\nColonnes ajoutées :", [c for c in matchs.columns if "REPOS" in c or "B2B" in c])
