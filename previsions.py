SQL_TABLE = """
CREATE TABLE IF NOT EXISTS prevision (
    jour                DATE          NOT NULL,
    equipe              CHAR(3)       NOT NULL,
    conference          VARCHAR(5)    NOT NULL,
    victoires_actuelles INT           NOT NULL,
    victoires_attendues DECIMAL(5, 2) NOT NULL,
    p_top6              DECIMAL(5, 4) NOT NULL,
    p_playin            DECIMAL(5, 4) NOT NULL,
    p_top10             DECIMAL(5, 4) NOT NULL,
    p_seed1             DECIMAL(5, 4) NOT NULL,
    PRIMARY KEY (jour, equipe),
    CONSTRAINT chk_conference CHECK (conference IN ('Est', 'Ouest'))
) ENGINE=InnoDB
"""

SQL_INSERT = """
INSERT INTO prevision (jour, equipe, conference, victoires_actuelles, victoires_attendues,
                       p_top6, p_playin, p_top10, p_seed1)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    conference          = VALUES(conference),
    victoires_actuelles = VALUES(victoires_actuelles),
    victoires_attendues = VALUES(victoires_attendues),
    p_top6              = VALUES(p_top6),
    p_playin            = VALUES(p_playin),
    p_top10             = VALUES(p_top10),
    p_seed1             = VALUES(p_seed1)
"""


def sauver_previsions(conn, resultat, jour):
    """Enregistre les probabilités du jour (idempotent : relancer le même jour écrase la ligne)."""
    lignes = [
        (jour, r.Equipe, r.Conf, int(r.V_actuelles), float(r.V_attendues),
         float(r.P_top6), float(r.P_playin), float(r.P_top10), float(r.P_seed1))
        for r in resultat.itertuples()
    ]
    cursor = conn.cursor()
    cursor.execute(SQL_TABLE)
    cursor.executemany(SQL_INSERT, lignes)
    conn.commit()
    cursor.close()
    return len(lignes)
