import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguegamelog



SAISONS = [f"{a}-{str(a + 1)[2:]}" for a in range(2015, 2027)]
SAISON_COURANTE = SAISONS[-1] 
DOSSIER_CACHE = Path("data/raw")
DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)



def normaliser_types(df: pd.DataFrame) -> pd.DataFrame:
   
    df = df.copy()
    for col in ["GAME_ID", "SEASON_ID"]:
        df[col] = df[col].astype(str)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    return df


def telecharger_saison(saison: str) -> pd.DataFrame:
  
    cible = DOSSIER_CACHE / f"games_{saison}.csv"

 
    if cible.exists() and saison != SAISON_COURANTE:
        print(f"Déjà présent : {cible.name}")
        df = pd.read_csv(cible, dtype={"GAME_ID": str})
        return normaliser_types(df)


    print(f"Téléchargement : {saison}...")
    log = leaguegamelog.LeagueGameLog(
        season=saison,
        season_type_all_star="Regular Season",
        timeout=60,
    )
    df = log.get_data_frames()[0]
    df.to_csv(cible, index=False)
    time.sleep(0.6)
    return normaliser_types(df)



def telecharger_toutes_saisons() -> pd.DataFrame:
   
    dataframes = []
    echecs = []

    for saison in SAISONS:
        try:
            df = telecharger_saison(saison)
            dataframes.append(df)
            print(f"  → {saison} : {df.shape[0]} lignes")
        except Exception as e:
            print(f"  → {saison} : ERREUR — {e}")
            echecs.append(saison)

    if echecs:
        print(f"\n  Saisons échouées : {echecs}")

    df_all = pd.concat(dataframes, ignore_index=True)
    return df_all



def inspecter_saison(saison: str) -> None:
   
    cible = DOSSIER_CACHE / f"games_{saison}.csv"

    if not cible.exists():
        print(f"Fichier absent : {cible}.")
        return

    df = pd.read_csv(cible, dtype={"GAME_ID": str})
    df = normaliser_types(df)

    print(f"\n=== Inspection de la saison {saison} ===")
    print(f"Shape             : {df.shape}")
    print(f"Type GAME_ID      : {df['GAME_ID'].dtype}")
    print(f"Type SEASON_ID    : {df['SEASON_ID'].dtype}")
    print(f"Type GAME_DATE    : {df['GAME_DATE'].dtype}")
    print(f"Type TEAM_ID      : {df['TEAM_ID'].dtype}")
    print(f"Exemples GAME_ID  : {df['GAME_ID'].head(3).tolist()}")
    print(f"Date min          : {df['GAME_DATE'].min()}")
    print(f"Date max          : {df['GAME_DATE'].max()}")

    df["HOME"] = df["MATCHUP"].str.contains(" vs. ", regex=False)
    df["OPPONENT"] = df["MATCHUP"].str.split().str[-1]
    print(f"Exemples HOME     : {df['HOME'].head(5).tolist()}")



def valider_donnees(df_all: pd.DataFrame) -> None:
    
    print("\n" + "=" * 60)
    print("VALIDATION DES DONNÉES")
    print("=" * 60)


    print("\n--- 1. Occurrences de chaque GAME_ID ---")
    occurrences = df_all.groupby("GAME_ID").size()
    print(occurrences.value_counts())


    print("\n--- 2. Nombre de matchs par saison ---")
    par_saison = df_all.groupby("SEASON_ID")["GAME_ID"].nunique()
    print(par_saison)


    print("\n--- 3. Écart avec une saison complète (1 230 matchs) ---")
    attendu = 30 * 82 // 2
    print(par_saison - attendu)


    print("\n--- 4. Matchs par équipe et par saison ---")
    par_equipe = df_all.groupby(["SEASON_ID", "TEAM_ID"]).size()
    print(par_equipe.groupby("SEASON_ID").agg(["min", "max", "mean"]))


    print("\n--- 5. Vérification clé (GAME_ID, TEAM_ID) ---")
    doublons = df_all.duplicated(["GAME_ID", "TEAM_ID"]).sum()
    print(f"Doublons : {doublons}")

  
    print("\n--- 6. Stabilité des noms d'équipe ---")
    max_noms = (df_all.groupby("TEAM_ID")[["TEAM_NAME", "TEAM_ABBREVIATION"]]
                .nunique().max())
    print(max_noms)



if __name__ == "__main__":
    print("=== Téléchargement des saisons ===")
    df_all = telecharger_toutes_saisons()
    print(f"\nDataFrame final : {df_all.shape}")

    print("\n=== Vérifications  ===")

    nb_nan_min = df_all["MIN"].isna().sum()
    print(f"NaN dans MIN : {nb_nan_min} (attendu : 0)")
    if nb_nan_min > 0:
        print(" Suppression des lignes avec MIN manquant...")
        df_all = df_all.dropna(subset=["MIN"])
        print(f"   → DataFrame après nettoyage : {df_all.shape}")

    
    nb_doublons = df_all.duplicated(["GAME_ID", "TEAM_ID"]).sum()
    print(f"Doublons (GAME_ID, TEAM_ID) : {nb_doublons} (attendu : 0)")
    if nb_doublons > 0:
        print("  Doublons détectés — la clé composite est invalide !")
    

    inspecter_saison("2023-24")
    valider_donnees(df_all)

    df_all.to_csv("data/raw/games_all_seasons.csv", index=False)
    print("\nSauvegardé dans data/raw/games_all_seasons.csv")
