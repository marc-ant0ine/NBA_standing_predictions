import contextlib
import io

from simulation import main


def silencieux(g):
    with contextlib.redirect_stdout(io.StringIO()):
        return main(graine=g, sauver=False).set_index("Equipe")


a, b = silencieux(42), silencieux(7)
cols = ["P_top6", "P_top10", "P_seed1"]
ecart = (a[cols] - b.loc[a.index, cols]).abs()
print("écart maximum entre deux graines :", ecart.max().round(4).to_dict())
print("écart moyen entre deux graines   :", ecart.mean().round(4).to_dict())
