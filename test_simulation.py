import numpy as np
import pandas as pd
import simulation as S

def jeu_un_match(sans):
    return pd.DataFrame({"i": [0], "j": [1], "SANS": [sans], "B2B_dom": [0.0], "B2B_ext": [0.0]})

# a) b0 = 0, terrain neutre : p_modele = p_elo = 0,5 -> l'Elo doit bouger de +K/2 ou -K/2
elo, vict = S.simuler(np.array([1500., 1500.]), np.zeros(2), jeu_un_match(1.0), 0.0, np.zeros(4),
                      100_000, np.random.default_rng(0))
assert set(np.unique(elo[:, 0])) == {1500 - S.K / 2, 1500 + S.K / 2}, "mise à jour de l'Elo incorrecte"
assert abs(vict[:, 0].mean() - 0.5) < 0.01

# b) b0 = 1 : l'équipe à domicile doit gagner avec la probabilité sigmoïde(1) = 0,731
elo, vict = S.simuler(np.array([1500., 1500.]), np.zeros(2), jeu_un_match(1.0), 1.0, np.zeros(4),
                      100_000, np.random.default_rng(1))
assert abs(vict[:, 0].mean() - 1 / (1 + np.exp(-1.0))) < 0.01, "probabilité du modèle incorrecte"

# c) conservation
assert np.allclose(elo.sum(axis=1), 3000)
assert np.all(vict.sum(axis=1) == 1)
print("Tous les tests passent.")
