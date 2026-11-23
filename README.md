# NBA standings predictor

Predicts the final NBA standings by simulating the rest of the season 10,000 times. A model estimates the win probability of every remaining game; each simulation draws the results, updates the team ratings along the way, and ranks the teams in each conference. The output is, for every team, an expected number of wins and the probability of finishing in the top 6, the play-in (7th to 10th), the top 10, or first in its conference.

It is a personal project, built step by step and kept honest: every modelling choice was checked on seasons the model had not seen, and the forecasts are stored every day so that they can be compared with the real final standings.

## Key results

All numbers below come from `final_eval.py` and `backtest.py`.

**Game-level model** (2024-25 and 2025-26, 2,460 games never used to choose the model, log loss, lower is better):

| Predictor | Log loss |
|---|---|
| Constant home-win probability | 0.6888 |
| Elo rating | 0.6095 |
| Elo + back-to-back flags (final model) | 0.6090 |

The back-to-back flags are worth about +0.003 log loss on the validation seasons (z = 2.5) but only +0.0014 ± 0.0014 on the test seasons: a probable, small effect that is **not confirmed out of sample**.

**Standings backtest** (2023-24, 2024-25, 2025-26; the forecast is rebuilt at five dates of each season using only the information available then; mean absolute error on final wins):

| Share of season played | Model | Current pace | Previous season's wins |
|---|---|---|---|
| 10 % | **7.75** | 9.78 | 9.33 |
| 25 % | **5.55** | 6.19 | 9.33 |
| 50 % | 4.03 | 3.89 | 9.33 |
| 75 % | 2.30 | 2.48 | 9.33 |
| 90 % | 1.04 | 1.12 | 9.33 |

- Early in the season the model beats both references by about 1.6 to 2.0 wins (z ≈ 2.5 to 2.8, with standard errors that are optimistic: 3 seasons only).
- From the middle of the season, it is no better than extrapolating the current pace, which is expected.
- Even at 10 % of the season, the typical error on a team's final wins is about 8: a forecast of 60 wins means roughly 52 to 68.
- Calibration is good: when the model announces 70 to 90 % to finish in the top 6, the team does so 76 % of the time (46 team-dates, about ±6 points). Be careful: 450 team-dates but only 90 independent team-seasons.

## How it works

```
nba_api  ->  CSV cache  ->  MySQL (equipe, game_log)  ->  one row per game
                                                              |
              Elo ratings  <-  neutral-site and bubble flags  +  rest days (back-to-back)
                                                              |
                  logistic regression (Elo gap, back-to-back, no-home-advantage)
                                                              |
         remaining schedule  ->  Monte Carlo (10,000 simulations)  ->  MySQL (prevision)
                                                              |
                                              Streamlit dashboard + backtest
```

- **Elo**: K = 20, ratings pulled 35 % towards the mean at the start of each season, home advantage of about 46 Elo points. Neutral-site games and the 2019-20 bubble games get no home advantage.
- **Features**: back-to-back flags for both teams, computed from the schedule (known in advance). A rolling "recent form" variable and an interaction between the two back-to-backs were tested and dropped: no gain beyond noise.
- **Simulation**: a loop over the remaining games, vectorised over the 10,000 simulations. The outcome of a game is drawn with the **model** probability, but the ratings are updated with the **Elo** probability, the dynamics on which the model was trained. Ties are broken at random.
- **Validation discipline**: chronological splits only, a one-shot final evaluation, a unit test that detects leakage in rolling features (`verif_forme.py`), and toy cases with known answers for the simulation (`test_simulation.py`).

## Limitations

- Injuries, trades and rest decisions are not modelled.
- Ties are broken at random, not with the real NBA tiebreakers. The play-in is assumed to cover the 7th to 10th seeds.
- While the NBA has not published all the games that depend on the NBA Cup, each team gets two fictitious games against an average opponent so that every team ends at 82 games. They disappear automatically once the real schedule is complete.
- The home advantage has declined in recent seasons (about 58.6 % of home wins in 2015-19, 54.7 % in 2023-26), while the model uses one value estimated on all seasons.
- The Elo parameters were tuned on 2016-17 to 2023-24; only 2024-25 and 2025-26 are fully out of sample.
- The two test seasons were looked at twice (Elo alone, then the final model), with no change in between.
- The probabilities are only as reliable as the model: the simulation noise is about ±0.5 point, the model uncertainty is much larger.

## Project structure

| File | Role |
|---|---|
| `nba_data.py` | Downloads and caches the game logs (`nba_api`) |
| `db.py`, `charger_mysql.py` | MySQL connection, loading of finished games |
| `preparer.py` | One row per game, flags neutral-site games |
| `Elo.py`, `tuner_elo.py` | Ratings, grid search on validation seasons |
| `variables.py`, `analyse_repos.py`, `verif_forme.py` | Rest days, residual analysis, leakage test |
| `modele.py`, `final_eval.py` | Model comparison, one-shot final evaluation |
| `calendrier.py`, `calendrier_restant.py`, `calendrier_explore.py`, `verif_calendrier.py` | Season schedule and remaining games |
| `simulation.py`, `previsions.py` | Monte Carlo simulation, storage of the forecasts |
| `test_simulation.py`, `verif_conferences.py`, `comparer_graines.py` | Tests, conference check, simulation noise |
| `backtest.py`, `analyse_backtest.py` | Backtest on past seasons and its analysis |
| `quotidien.py` | Daily pipeline |
| `dashboard_nba.py` | Streamlit dashboard |
| `sql/schema.sql` | Tables `equipe`, `game_log`, `prevision` |
| `results/backtest.csv` | Backtest results (team-date forecasts and outcomes), read by the dashboard's reliability tab |

## Installation

```bash
git clone https://github.com/marc-ant0ine/NBA_standing_predictions.git
cd NBA_standing_predictions
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # then fill in your MySQL credentials
mysql -u root -e "CREATE DATABASE IF NOT EXISTS nba;"
mysql -u root nba < sql/schema.sql
```

(The SQL can also be run in MySQL Workbench.)

## Usage

```bash
python quotidien.py                       # download, load, prepare, schedule, simulate, store
python backtest.py                        # rebuilds the backtest (data/processed/backtest.csv)
python test_simulation.py                 # unit tests with known answers
streamlit run dashboard_nba.py            # dashboard on http://localhost:8501
```

`quotidien.py` stops if the database holds no recent game, so it only makes sense during the season. To run it every day at 10:00 (all of the previous night's games are finished):

```cron
0 10 * * * cd /path/to/NBA_standing_predictions && .venv/bin/python quotidien.py >> data/log_quotidien.txt 2>&1
```

## Data and credits

Game data comes from stats.nba.com through the unofficial [`nba_api`](https://github.com/swar/nba_api) package, whose endpoints may change without notice. NBA team names and logos belong to the NBA and its teams: the dashboard loads the logos from the NBA's servers when it displays them, and this repository does not contain any.
