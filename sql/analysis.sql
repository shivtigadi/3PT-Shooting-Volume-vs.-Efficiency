SELECT
    PLAYER_ID,
    PLAYER_NAME,
    TEAM_ABBREVIATION,
    GP AS games_played,
    FG3M AS threes_made,
    FG3A AS threes_attempted,
    ROUND(1.0 * FG3A / GP, 3) AS threes_per_game,
    ROUND(100.0 * FG3M / NULLIF(FG3A, 0), 3) AS three_pct
FROM player_totals
WHERE FG3A >= :min_attempts AND GP > 0
ORDER BY threes_per_game DESC;
