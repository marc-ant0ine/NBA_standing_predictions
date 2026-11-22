import pandas as pd

from db import se_connecter
from nba_data import telecharger_toutes_saisons


def charger_equipes(conn, df):
    equipes = df[["TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME"]].drop_duplicates()
    lignes = list(equipes.astype(object).itertuples(index=False, name=None))
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO equipe (team_id, abreviation, nom) VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE abreviation = VALUES(abreviation), nom = VALUES(nom)
    """, lignes)
    conn.commit()
    cursor.close()
    print(f" {len(lignes)} équipes chargées.")


def charger_game_log(conn, df):
    """Charge les lignes de stats dans game_log (idempotent)."""
    # Un match en cours a WL vide : on ne charge que les matchs terminés (les deux lignes de chaque match)
    df = df[df["WL"].notna()]
    df = df.groupby("GAME_ID").filter(lambda g: len(g) == 2)

    df = df.rename(columns={"MIN": "minutes_total"})

    colonnes = [
        "GAME_ID", "TEAM_ID", "SEASON_ID", "GAME_DATE", "MATCHUP", "WL",
        "minutes_total", "PTS", "FG_PCT", "FGM", "FGA", "FG3M", "FG3A",
        "FG3_PCT", "FTM", "FTA", "FT_PCT", "OREB", "DREB", "REB",
        "AST", "STL", "BLK", "TOV", "PF", "PLUS_MINUS"
    ]
    df = df[colonnes].copy()

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"]).dt.date
    df = df.astype(object).where(df.notna(), None)
    lignes = list(df.itertuples(index=False, name=None))

    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO game_log (
            game_id, team_id, season_id, game_date, matchup, wl,
            minutes_total, pts, fg_pct, fgm, fga, fg3m, fg3a,
            fg3_pct, ftm, fta, ft_pct, oreb, dreb, reb,
            ast, stl, blk, tov, pf, plus_minus
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            season_id     = VALUES(season_id),
            game_date     = VALUES(game_date),
            matchup       = VALUES(matchup),
            wl            = VALUES(wl),
            minutes_total = VALUES(minutes_total),
            pts           = VALUES(pts),
            fg_pct        = VALUES(fg_pct),
            fgm           = VALUES(fgm),
            fga           = VALUES(fga),
            fg3m          = VALUES(fg3m),
            fg3a          = VALUES(fg3a),
            fg3_pct       = VALUES(fg3_pct),
            ftm           = VALUES(ftm),
            fta           = VALUES(fta),
            ft_pct        = VALUES(ft_pct),
            oreb          = VALUES(oreb),
            dreb          = VALUES(dreb),
            reb           = VALUES(reb),
            ast           = VALUES(ast),
            stl           = VALUES(stl),
            blk           = VALUES(blk),
            tov           = VALUES(tov),
            pf            = VALUES(pf),
            plus_minus    = VALUES(plus_minus)
    """, lignes)
    conn.commit()
    cursor.close()
    print(f" {len(lignes)} lignes chargées/mises à jour dans game_log.")


if __name__ == "__main__":
    df_all = telecharger_toutes_saisons()
    print("MIN manquants :", df_all["MIN"].isna().sum())   

    conn = se_connecter()
    charger_equipes(conn, df_all)      
    charger_game_log(conn, df_all)
    conn.close()
