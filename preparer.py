from pathlib import Path

import pandas as pd

from db import se_connecter


def un_match_par_ligne(df):
    df = df.copy()
    df["HOME"] = df["MATCHUP"].str.contains(" vs. ", regex=False)

    
    nb_dom = df.groupby("GAME_ID")["HOME"].transform("sum")
    df["NEUTRE"] = nb_dom == 0

   
    plus_petit_id = df.groupby("GAME_ID")["TEAM_ID"].transform("min")
    df["HOME"] = df["HOME"] | (df["NEUTRE"] & (df["TEAM_ID"] == plus_petit_id))

    domicile = df[df["HOME"]][["GAME_ID", "GAME_DATE", "SEASON_ID", "TEAM_ID", "PTS", "WL", "NEUTRE"]]
    exterieur = df[~df["HOME"]][["GAME_ID", "TEAM_ID", "PTS"]]

    matchs = domicile.merge(exterieur, on="GAME_ID", suffixes=("_dom", "_ext"), validate="one_to_one")
    matchs["DOM_GAGNE"] = matchs["WL"] == "W"

    assert len(matchs) == df["GAME_ID"].nunique(), "des matchs ont été perdus dans le merge"
    return matchs



def charger_depuis_mysql() -> pd.DataFrame:
    conn = se_connecter()
    query = """
        SELECT game_id, team_id, season_id, game_date, matchup, wl,
               minutes_total, pts, fg_pct, fgm, fga, fg3m, fg3a,
               fg3_pct, ftm, fta, ft_pct, oreb, dreb, reb,
               ast, stl, blk, tov, pf, plus_minus
        FROM game_log;
    """
    df = pd.read_sql(query, conn, parse_dates=["game_date"])
    conn.close()
    df.columns = df.columns.str.upper()
    return df


if __name__ == "__main__":
    print("=== Chargement des données brutes ===")
    df = charger_depuis_mysql()
    if df.empty:
        raise SystemExit("game_log est vide : lance d'abord charger_mysql.py")
    print(f"Shape brut : {df.shape}")

    print("\n=== Transformation : 1 ligne par match ===")
    matchs = un_match_par_ligne(df)
    print(f"Shape matchs : {matchs.shape}")
    print(matchs.head())

    print("\n=== Répartition de DOM_GAGNE ===")
    print(matchs["DOM_GAGNE"].value_counts(normalize=True))

    normaux = matchs[~matchs["NEUTRE"]]
    print(normaux.groupby("SEASON_ID")["DOM_GAGNE"].mean())

    sortie = Path("data/processed/matchs.csv")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    matchs.to_csv(sortie, index=False)
    print(f"\nSauvegardé dans {sortie}")
