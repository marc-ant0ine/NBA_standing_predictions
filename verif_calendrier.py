from Elo import charger_matchs
from calendrier_restant import charger_calendrier_restant, matchs_manquants
from calendrier_restant import variables_restants

matchs = charger_matchs()
joues = matchs[matchs["SEASON_ID"] == "22026"]
restants = charger_calendrier_restant(joues)

print("joués :", len(joues), "| restants avec équipes :", len(restants))
print("matchs neutres à venir :", int(restants["NEUTRE"].sum()))
print(restants[restants["NEUTRE"]][["GAME_ID", "GAME_DATE", "TEAM_ID_dom", "TEAM_ID_ext", "arenaCity"]].to_string())

ids = sorted(set(matchs["TEAM_ID_dom"]) | set(matchs["TEAM_ID_ext"]))
print(matchs_manquants(joues, restants, ids).value_counts())



v = variables_restants(joues, restants)
print("\nmatchs à venir avec variables :", len(v))
print("back-to-back à venir (domicile, extérieur) :", int(v["B2B_dom"].sum()), int(v["B2B_ext"].sum()))
print("sans avantage du terrain :", int(v["SANS_AVANTAGE"].sum()))
print(v.head(5).to_string())
