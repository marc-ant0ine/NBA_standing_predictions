import pandas as pd
from Elo import charger_matchs

df = pd.read_csv("data/raw/calendrier_2026-27.csv", dtype={"gameId": str})
df["prefixe"] = df["gameId"].str[:3]

print("=== Préfixe x statut ===")
print(pd.crosstab(df["prefixe"], df["gameStatus"]))

reg = df[df["prefixe"] == "002"].copy()
reg["num"] = reg["gameId"].str[-4:].astype(int)
manquants = sorted(set(range(1, 1231)) - set(reg["num"]))
print(f"\nNuméros de la saison régulière absents du calendrier : {len(manquants)}")
print(manquants[:10], "...", manquants[-5:])

print("\n=== Matchs par équipe dans le calendrier (saison régulière) ===")
par_equipe = pd.concat([reg["homeTeam_teamTricode"], reg["awayTeam_teamTricode"]]).value_counts()
print(par_equipe.value_counts().sort_index())

print("\n=== Formats de date et de lieu ===")
print(df[["gameId", "gameDate", "gameDateEst", "gameStatusText"]].head(3).to_string())
print(df[["homeTeam_teamTricode", "awayTeam_teamTricode", "arenaName", "arenaCity"]].head(5).to_string())



m = charger_matchs(saison_max="22025")
fin = m[(m["SEASON_ID"] == "22025") & (m["GAME_ID"].str[-4:].astype(int) >= 1195)]
print(fin[["GAME_ID", "GAME_DATE", "TEAM_ID_dom", "TEAM_ID_ext", "NEUTRE"]].to_string())

# 1) les matchs sans équipe identifiée
sans = reg[(reg["homeTeam_teamTricode"].fillna("") == "") | (reg["awayTeam_teamTricode"].fillna("") == "")]
print("matchs sans équipe identifiée :", len(sans))
print(sans[["gameId", "gameDateEst", "homeTeam_teamTricode", "awayTeam_teamTricode"]].to_string())

# 2) les dates du calendrier et celles de l'historique sont-elles identiques ?
from Elo import charger_matchs
matchs = charger_matchs()
joues = reg.merge(matchs[matchs["SEASON_ID"] == "22026"][["GAME_ID", "GAME_DATE"]],
                  left_on="gameId", right_on="GAME_ID")
joues["date_cal"] = pd.to_datetime(joues["gameDateEst"]).dt.tz_localize(None).dt.normalize()
print("matchs présents dans les deux sources :", len(joues))
print("dates différentes :", int((joues["date_cal"] != joues["GAME_DATE"]).sum()), "(attendu : 0)")
