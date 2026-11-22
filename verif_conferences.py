from collections import Counter

import pandas as pd

from simulation import EST

cal = pd.read_csv("data/raw/calendrier_2026-27.csv", dtype={"gameId": str})
reg = cal[cal["gameId"].str.startswith("002")]
reg = reg[reg["homeTeam_teamTricode"].notna() & reg["awayTeam_teamTricode"].notna()]

equipes = set(reg["homeTeam_teamTricode"]) | set(reg["awayTeam_teamTricode"])
OUEST = equipes - EST
print("équipes du calendrier :", len(equipes), "| EST :", len(EST), "| OUEST :", len(OUEST))
print("abréviations de EST absentes du calendrier :", sorted(EST - equipes))     # doit être vide

rencontres = Counter(frozenset(p) for p in zip(reg["homeTeam_teamTricode"], reg["awayTeam_teamTricode"]))
voisins = {t: set() for t in equipes}
for paire, n in rencontres.items():
    if n >= 3:                      # même conférence : 3 ou 4 matchs ; conférences opposées : 2
        a, b = tuple(paire)
        voisins[a].add(b)
        voisins[b].add(a)


def groupe(depart):
    vu, pile = {depart}, [depart]
    while pile:
        for v in voisins[pile.pop()] - vu:
            vu.add(v)
            pile.append(v)
    return vu


g_est = groupe(next(iter(EST)))
g_ouest = groupe(next(iter(OUEST)))
print("groupe de l'Est identique à EST :", g_est == EST)
print("groupe de l'Ouest identique à OUEST :", g_ouest == OUEST)
print("dans le groupe mais pas dans EST :", sorted(g_est - EST), "| dans EST mais pas dans le groupe :", sorted(EST - g_est))


