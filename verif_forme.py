import variables
from Elo import charger_matchs
from variables import table_equipe_match, ajouter_repos, ajouter_forme, test_fuite

em = table_equipe_match(charger_matchs())

print("1) avec shift(1)  -> test de fuite :", test_fuite(em))      # attendu : True

# Version volontairement fautive : moyenne glissante SANS décalage
def forme_sans_shift(em, N=10):
    g = em.groupby(["TEAM_ID", "SEASON_ID"])["GAGNE"]
    em["FORME"] = g.transform(lambda s: s.rolling(N, min_periods=3).mean())
    return em

variables.ajouter_forme = forme_sans_shift
print("2) sans shift(1)  -> test de fuite :", variables.test_fuite(em))   # attendu : False

# Valeurs manquantes de la bonne version (3 par équipe et par saison)
variables.ajouter_forme = ajouter_forme
em2 = ajouter_forme(ajouter_repos(table_equipe_match(charger_matchs())))
print("3) FORME manquantes :", int(em2["FORME"].isna().sum()), "(attendu : 990)")
