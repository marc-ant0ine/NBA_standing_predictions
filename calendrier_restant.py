import pandas as pd

from variables import construire_variables

# Villes où une équipe joue parfois "à domicile" dans une autre salle, devant son public habituel
VILLES_DOMICILE_ALTERNATIVE = {"Austin"}


def charger_calendrier_restant(matchs_joues, chemin="data/raw/calendrier_2026-27.csv"):
    cal = pd.read_csv(chemin, dtype={"gameId": str})
    cal = cal[cal["gameId"].str.startswith("002")].copy()                       # saison régulière
    cal = cal[cal["homeTeam_teamTricode"].notna() & cal["awayTeam_teamTricode"].notna()].copy()   # équipes connues

    # Les matchs sans équipe rendaient ces colonnes décimales (float) : on les remet en entiers
    for col in ["homeTeam_teamId", "awayTeam_teamId"]:
        cal[col] = cal[col].astype(int)

    cal["GAME_DATE"] = pd.to_datetime(cal["gameDateEst"]).dt.tz_localize(None).dt.normalize()

    # Ville habituelle de chaque équipe = la ville la plus fréquente de ses matchs à domicile
    ville_habituelle = cal.groupby("homeTeam_teamTricode")["arenaCity"].agg(lambda s: s.mode().iloc[0])
    autre_ville = cal["arenaCity"] != cal["homeTeam_teamTricode"].map(ville_habituelle)
    cal["NEUTRE"] = autre_ville & ~cal["arenaCity"].isin(VILLES_DOMICILE_ALTERNATIVE)

    restants = cal[~cal["gameId"].isin(matchs_joues["GAME_ID"])]               # identifiants pas encore joués
    return restants.rename(columns={"gameId": "GAME_ID",
                                    "homeTeam_teamId": "TEAM_ID_dom",
                                    "awayTeam_teamId": "TEAM_ID_ext"})[
        ["GAME_ID", "GAME_DATE", "TEAM_ID_dom", "TEAM_ID_ext", "NEUTRE", "arenaCity"]
    ].reset_index(drop=True)


def matchs_manquants(matchs_joues, restants, ids_equipes):
    n_joues = pd.concat([matchs_joues["TEAM_ID_dom"], matchs_joues["TEAM_ID_ext"]]).value_counts()
    n_rest = pd.concat([restants["TEAM_ID_dom"], restants["TEAM_ID_ext"]]).value_counts()
    total = n_joues.add(n_rest, fill_value=0).reindex(ids_equipes).fillna(0)
    return (82 - total).astype(int)


def variables_restants(joues, restants):
    """Jours de repos et terrain neutre des matchs à venir, calculés avec l'historique de la saison."""
    colonnes = ["GAME_ID", "GAME_DATE", "SEASON_ID", "TEAM_ID_dom", "TEAM_ID_ext", "DOM_GAGNE"]
    futurs = restants.copy()
    futurs["SEASON_ID"] = joues["SEASON_ID"].iloc[0]
    futurs["DOM_GAGNE"] = False            # inconnu : sans effet sur les jours de repos
    tout = pd.concat([joues[colonnes], futurs[colonnes]], ignore_index=True)
    tout = construire_variables(tout)

    sortie = tout[tout["GAME_ID"].isin(futurs["GAME_ID"])]
    sortie = sortie.merge(futurs[["GAME_ID", "NEUTRE"]], on="GAME_ID", how="left", validate="one_to_one")
    sortie = sortie.rename(columns={"NEUTRE": "SANS_AVANTAGE"})
    return sortie[["GAME_ID", "GAME_DATE", "TEAM_ID_dom", "TEAM_ID_ext", "B2B_dom", "B2B_ext", "SANS_AVANTAGE"]
                  ].sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True)
