# NBA 3-PT Shooting Analysis: Volume vs. Efficiency
Analyzing the relationship between three point shooting volume and efficiency from the 2024-25 NBA regular season using Python, SQLite, and statistical testing.

# Overview
Do certain NBA players shoot at different efficiency levels when looking at the number of three point shots they take? 

The analysis uses official NBA player statistics, filters for players that attempted at least 150 three point shots, and calculates shooting volume and accuracy using SQL. 

# VIZ
The scatterplot compares three points attempts per game against three point percentage, with a reference line highlighting the median shooting volume and league-wide shooting efficiency

# Statistical Analysis
The code uses Pearson's correlation test and ordinary least squares linear regression to interpret the relationship between shooting volume and efficiency. 
- Null Hypothesis: there is no correlation between three point attempts per game and three point percentage
- Alt Hypothesis: A linear correlation exists (nonzero)
- α = 0.05

# Results
See the output/findings.txt file to see the results from the Pearson's test and regression slope
Statistical significance does not imply correlation. There are a number of other factors which can play a role in these findings, such as shot difficulty, the minimum-attempt threshold, shot location, defender proximity, etc. 

# Technologies
Python: pandas, matplotlib, numpy, scipy
SQL/SQLite: Data storage, cleaning, filtering, aggregation
NBA API: Official NBA player statistics

# How to Use
Clone the repo, navigate to the project directory and run the following terminal commands:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --season 2024-25

Generated outputs are saved in the output/ directory.

# Data Source
NBA.com/stats — Official NBA Player Statistics
