"""NBA 3-point volume vs accuracy: nba_api -> SQLite -> SQL -> chart + statistics."""
import argparse
import sqlite3
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, linregress

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'nba_shooting.sqlite'
OUTPUT = ROOT / 'output'
SQL = (ROOT / 'sql' / 'analysis.sql').read_text()


def load_data(season: str, csv: str | None) -> pd.DataFrame:
    if csv:
        df = pd.read_csv(csv)
    else:
        from nba_api.stats.endpoints import leaguedashplayerstats
        print(f'Fetching NBA {season} regular-season player statistics...')
        response = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, season_type_all_star='Regular Season',
            per_mode_detailed='Totals', timeout=60)
        df = response.get_data_frames()[0]
        time.sleep(0.5)
    required = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GP', 'FG3M', 'FG3A']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f'Missing columns: {missing}. Need NBA LeagueDashPlayerStats totals CSV.')
    df = df[required].copy()
    for c in ['PLAYER_ID', 'GP', 'FG3M', 'FG3A']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=required).copy()
    df = df[(df.GP > 0) & (df.FG3A >= 0)]
    df = df.drop_duplicates(subset=['PLAYER_ID'], keep='last')
    df['SEASON'] = season
    return df


def store(df: pd.DataFrame):
    with sqlite3.connect(DB) as con:
        df.to_sql('player_totals', con, if_exists='replace', index=False)
        con.execute('CREATE INDEX IF NOT EXISTS idx_player_3pa ON player_totals (FG3A)')


def analyze(min_attempts: int):
    with sqlite3.connect(DB) as con:
        players = pd.read_sql_query(SQL, con, params={'min_attempts': min_attempts})
        all_players = pd.read_sql_query('SELECT SUM(FG3M) AS makes, SUM(FG3A) AS attempts FROM player_totals', con)
    if len(players) < 3:
        raise ValueError('Too few eligible players; lower --min-attempts.')
    league_pct = all_players['makes'][0] / all_players['attempts'][0] * 100
    x, y = players['threes_per_game'].to_numpy(), players['three_pct'].to_numpy()
    r, p = pearsonr(x, y)
    fit = linregress(x, y)
    return players, league_pct, r, p, fit



def make_plot(players, league_pct, r, p, fit, season, min_attempts):
    OUTPUT.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(15, 10), dpi=170)
    fig.patch.set_facecolor('#f5f6f8')
    ax.set_facecolor('white')

    x = players['threes_per_game'].to_numpy()
    y = players['three_pct'].to_numpy()
    xmid = float(np.median(x))

    ax.scatter(x, y, s=55, c='#2864a0', alpha=.75,
               edgecolors='white', linewidths=.6, zorder=3)

    ax.axvline(xmid, ls=(0, (5, 5)), color='#8a929d', lw=1.2)
    ax.axhline(league_pct, ls=(0, (5, 5)), color='#8a929d', lw=1.2)

    xpad = max(.2, (max(x) - min(x)) * .08)
    ypad = max(2, (max(y) - min(y)) * .1)

    ax.set_xlim(max(0, min(x) - xpad), max(x) + xpad)
    ax.set_ylim(max(0, min(y) - ypad), min(100, max(y) + ypad))

    ax.grid(alpha=.16, zorder=0)
    ax.spines[['top', 'right']].set_visible(False)

    ax.set_xlabel('3-point attempts per game', fontsize=12, labelpad=12)
    ax.set_ylabel('3-point percentage (%)', fontsize=12, labelpad=12)
    ax.set_title('NBA 3-Point Shooting: Volume vs. Efficiency',
                 fontsize=20, weight='bold', pad=28)

    ax.text(
        .5, 1.015,
        f'{season} regular season  •  minimum {min_attempts} 3PA  •  {len(players)} players',
        transform=ax.transAxes, ha='center', fontsize=10, color='#5b6571'
    )

    ax.text(xmid, ax.get_ylim()[1],
            f'  median {xmid:.1f} attempts/game',
            va='top', fontsize=9, color='#5b6571')

    ax.text(ax.get_xlim()[1], league_pct,
            f' league {league_pct:.1f}% ',
            ha='right', va='bottom', fontsize=9, color='#5b6571')

    quadrants = [
        players[(players.threes_per_game < xmid) & (players.three_pct >= league_pct)],
        players[(players.threes_per_game >= xmid) & (players.three_pct >= league_pct)],
        players[(players.threes_per_game < xmid) & (players.three_pct < league_pct)],
        players[(players.threes_per_game >= xmid) & (players.three_pct < league_pct)],
    ]

    label_counts = [8, 20, 8, 8]

    for quadrant_index, group in enumerate(quadrants):
        if group.empty:
            continue

        ranked = group.assign(
            score=(group.threes_per_game - xmid).abs() / max(np.std(x), 0.1)
                  + (group.three_pct - league_pct).abs() / max(np.std(y), 0.1)
        ).sort_values('score', ascending=False).head(label_counts[quadrant_index])

        for i, (_, player) in enumerate(ranked.iterrows()):
            short = ' '.join(player['PLAYER_NAME'].split()[-2:])

            x_offset = 7 if quadrant_index in (1, 3) else -7
            y_offset = (9, -11, 17, -19)[i % 4]

            ax.annotate(
                f'{short} ({player.TEAM_ABBREVIATION})',
                (player.threes_per_game, player.three_pct),
                xytext=(x_offset, y_offset),
                textcoords='offset points',
                ha='left' if x_offset > 0 else 'right',
                fontsize=7.0,
                alpha=.9,
                arrowprops=dict(
                    arrowstyle='-',
                    color='#a4adb8',
                    lw=.45
                )
            )

    fig.text(
        .12, .035,
        f'Pearson r = {r:+.3f}   |   p = {p:.3g}   |   SQL + SQLite + Python   |   Source: NBA Stats',
        fontsize=10, color='#4d5967'
    )

    fig.savefig(
        OUTPUT / 'nba_3pt_volume_vs_efficiency.png',
        bbox_inches='tight'
    )

    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', default='2024-25')
    parser.add_argument('--min-attempts', type=int, default=150)
    parser.add_argument('--csv', help='Use a previously downloaded NBA LeagueDashPlayerStats totals CSV')
    args = parser.parse_args()
    data = load_data(args.season, args.csv)
    store(data)
    players, league_pct, r, p, fit = analyze(args.min_attempts)
    make_plot(players, league_pct, r, p, fit, args.season, args.min_attempts)
    OUTPUT.mkdir(exist_ok=True)
    players.to_csv(OUTPUT / 'player_results.csv', index=False)
    significant = 'statistically significant' if p < .05 else 'not statistically significant'
    summary = (f'NBA {args.season}: 3-point volume vs. efficiency\n'
               f'Players with >= {args.min_attempts} 3PA: {len(players)}\n'
               f'League 3P% (all players, attempt-weighted): {league_pct:.2f}%\n'
               f'Pearson correlation (3PA/game vs 3P%): r={r:.4f}, p={p:.5g}\n'
               f'Result at alpha=0.05: {significant}\n'
               f'OLS slope: {fit.slope:.3f} percentage points per additional 3PA/game\n'
               f'NOTE: Observational, player-level correlation; no causal interpretation.\n'
               f'NOTE: Selection threshold and player roles can bias the association.\n')
    (OUTPUT / 'findings.txt').write_text(summary)
    print(summary)
    print('Saved output/nba_3pt_volume_vs_efficiency.png, output/player_results.csv, output/findings.txt')


if __name__ == '__main__':
    main()
