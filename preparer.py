from pathlib import Path

import pandas as pd

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def un_match_par_ligne(df):
    df = df.copy()
    df["HOME"] = df["MATCHUP"].str.contains(" vs. ", regex=False)

    domicile = df[df["HOME"]][["GAME_ID", "GAME_DATE", "SEASON_ID", "TEAM_ID", "PTS", "WL"]]
    exterieur = df[~df["HOME"]][["GAME_ID", "TEAM_ID", "PTS"]]

    matchs = domicile.merge(
        exterieur,
        on="GAME_ID",
        suffixes=("_dom", "_ext"),
    )
    matchs["DOM_GAGNE"] = matchs["WL"] == "W"
    return matchs

def charger_depuis_mysql() -> pd.DataFrame:
    
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )
    query = """
        SELECT game_id, team_id, season_id, game_date, matchup, wl,
               minutes_total, pts, fg_pct, fgm, fga, fg3m, fg3a,
               fg3_pct, ftm, fta, ft_pct, oreb, dreb, reb,
               ast, stl, blk, tov, pf, plus_minus
        FROM game_log;
    """
    df = pd.read_sql(query, conn)

    df = pd.read_sql(query, conn, parse_dates=["game_date"])
    df.columns = df.columns.str.upper()
    conn.close()
    return df

if __name__ == "__main__":
    print("=== Chargement des données brutes ===")
    df = charger_depuis_mysql()
    print(f"Shape brut : {df.shape}")

    print("\n=== Transformation : 1 ligne par match ===")
    matchs = un_match_par_ligne(df)
    print(f"Shape matchs : {matchs.shape}")
    print(matchs.head())

   
    print("\n=== Répartition de DOM_GAGNE ===")
    print(matchs["DOM_GAGNE"].value_counts(normalize=True))


    sortie = Path("data/processed/matchs.csv")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    matchs.to_csv(sortie, index=False)
    print(f"\nSauvegardé dans {sortie}")
