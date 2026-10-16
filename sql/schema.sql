USE nba;

CREATE TABLE IF NOT EXISTS equipe (
    team_id       INT PRIMARY KEY,
    abreviation   CHAR(3) NOT NULL,
    nom           VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS game_log (
    game_id        CHAR(10)     NOT NULL,
    team_id        INT          NOT NULL,
    season_id      CHAR(5)      NOT NULL,
    game_date      DATE         NOT NULL,
    matchup        VARCHAR(15)  NOT NULL,
    wl             CHAR(1)      NOT NULL,
    minutes_total  INT          NOT NULL,   
    pts            INT          NOT NULL,
    fg_pct         DECIMAL(5,3),
    fgm            INT,
    fga            INT,
    fg3m           INT,
    fg3a           INT,
    fg3_pct        DECIMAL(5,3),
    ftm            INT,
    fta            INT,
    ft_pct         DECIMAL(5,3),
    oreb           INT,
    dreb           INT,
    reb            INT,
    ast            INT,
    stl            INT,
    blk            INT,
    tov            INT,
    pf             INT,
    plus_minus     INT,
    PRIMARY KEY (game_id, team_id),
    INDEX idx_team_date (team_id, game_date),   
    CONSTRAINT fk_log_equipe FOREIGN KEY (team_id) REFERENCES equipe(team_id),
    CONSTRAINT chk_wl CHECK (wl IN ('W', 'L'))
) ENGINE=InnoDB;