from pathlib import Path

from nba_api.stats.endpoints import scheduleleaguev2

sched = scheduleleaguev2.ScheduleLeagueV2(season="2026-27", timeout=60)
frames = sched.get_data_frames()
df = frames[0]

Path("data/raw").mkdir(parents=True, exist_ok=True)
df.to_csv("data/raw/calendrier_2026-27.csv", index=False)     

print("forme :", df.shape)
mots = ["teamid", "tricode", "teamname", "arena", "city"]
print([c for c in df.columns if any(m in c.lower() for m in mots)])
print(df["gameId"].astype(str).str[:3].value_counts())
print(df["gameStatus"].value_counts())
