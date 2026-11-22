import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

from db import se_connecter

DOSSIER = Path(__file__).resolve().parent

# (nom, script, bloquant) : une étape non bloquante peut échouer sans empêcher la suite
ETAPES = [
    ("Téléchargement et chargement MySQL", "charger_mysql.py", True),
    ("Un match par ligne", "preparer.py", True),
    ("Calendrier", "calendrier.py", False),
    ("Simulation et enregistrement", "simulation.py", True),
]
RETARD_MAX_JOURS = 3          # au-delà, on considère que le téléchargement a échoué


def maintenant():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def donnees_a_jour():
    """Vérifie que la base contient des matchs récents : un téléchargement raté ne fait pas planter charger_mysql.py."""
    conn = se_connecter()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(game_date) FROM game_log")
    dernier = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    retard = (dt.date.today() - dernier).days
    print(f"[{maintenant()}] Dernier match en base : {dernier} (il y a {retard} jour(s))", flush=True)
    return retard <= RETARD_MAX_JOURS


def main():
    debut = time.time()
    for nom, script, bloquant in ETAPES:
        print(f"[{maintenant()}] Étape : {nom} ({script})", flush=True)
        resultat = subprocess.run([sys.executable, script], cwd=DOSSIER)
        if resultat.returncode != 0:
            print(f"[{maintenant()}] ÉCHEC de « {nom} » (code {resultat.returncode})", flush=True)
            if bloquant:
                sys.exit(resultat.returncode)
        if script == "charger_mysql.py" and not donnees_a_jour():
            print(f"[{maintenant()}] ARRÊT : les données en base sont trop anciennes.", flush=True)
            sys.exit(2)
    print(f"[{maintenant()}] Pipeline terminé en {time.time() - debut:.0f} s.", flush=True)


if __name__ == "__main__":
    main()
