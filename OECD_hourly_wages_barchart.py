"""
OECD Hourly Wages Visualization - Horizontal Bar Chart Comparison
================================================================

This script creates a side-by-side horizontal bar chart comparing hourly wages 
across OECD countries between 2007 and 2024, using data from MySQL database analysis.

Key Features:
- Connects to MySQL database containing OECD wage analysis results
- Creates mirrored horizontal bar charts for 2007 vs 2024 comparison
- Applies color gradients based on wage values (YlGnBu colormap)
- Excludes countries not in USD PPP (Bulgaria, Romania, Croatia)
- Sorts countries independently by their respective year's wages
- Displays exact wage values on each bar
- Includes methodology footnote and professional styling

Data Source: OECD statistics on average annual wages and hours worked
Output: High-resolution PNG bar chart visualization

Author: FableBits
Repository: https://github.com/FableBits/Real-Hourly-Wages-Change
"""

# %%
import mysql.connector
from sqlalchemy import create_engine, text
from getpass import getpass
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import Normalize

# ============================================================================
# DATABASE CONNECTION AND DATA LOADING
# ============================================================================

# Database credentials
user = "********"
password = getpass("MySQL password: ")
database = "********"

# Create SQLAlchemy engine for database connection
engine = create_engine(f"mysql+pymysql://{user}:{password}@localhost/{database}")

# Test database connection
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT '✅ Connection successful' AS status"))
        print(result.scalar())
except Exception as e:
    print(f"❌ Connection failed: {e}")

# Load OECD hourly wage analysis results
query = "SELECT * FROM oecd_hw_change"
df = pd.read_sql(query, engine)

# ============================================================================
# DATA PREPARATION
# ============================================================================

# Exclude countries not using USD PPP (use national currency instead)
not_in_usd = ['Bulgaria', 'Romania', 'Croatia']
df = df[~df['country'].isin(not_in_usd)].copy()

# Rename OECD aggregate for better display
df = df.replace("OECD", "OECD average")

# ============================================================================
# CHART SETUP AND DATA SORTING
# ============================================================================

# Create figure with two mirrored subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 10), gridspec_kw={'width_ratios': [1, 1]})

# Set consistent background colors
fig.patch.set_facecolor("lightcyan")
ax1.set_facecolor("lightcyan")
ax2.set_facecolor("lightcyan")

# Sort countries by wage values for each year independently
df_2007_sorted = df.sort_values('hw_2007')
df_2024_sorted = df.sort_values('hw_2024')

# Create color normalization for gradient mapping
norm_2007 = Normalize(vmin=df_2007_sorted['hw_2007'].min(), vmax=df_2007_sorted['hw_2007'].max())
norm_2024 = Normalize(vmin=df_2024_sorted['hw_2024'].min(), vmax=df_2024_sorted['hw_2024'].max())
cmap = plt.cm.YlGnBu

# ============================================================================
# BAR CHART VISUALIZATION
# ============================================================================

# Left subplot: 2007 wages with color gradient
bars1 = ax1.barh(df_2007_sorted['country'], df_2007_sorted['hw_2007'], 
                color=[cmap(norm_2007(value)) for value in df_2007_sorted['hw_2007']])
ax1.set_title('Hourly Wages in 2007 (USD)', fontsize=16, fontweight='bold')

# Add wage values as text labels on left bars
for bar in bars1:
    width = bar.get_width()
    ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
             f'{width:.1f}', ha='left', va='center', fontsize=9)

# Right subplot: 2024 wages with color gradient and inverted axis
bars2 = ax2.barh(df_2024_sorted['country'], df_2024_sorted['hw_2024'], 
                color=[cmap(norm_2024(value)) for value in df_2024_sorted['hw_2024']])
ax2.invert_xaxis()  # Create mirrored effect
ax2.set_title('Hourly Wages in 2024 (USD)', fontsize=16, fontweight='bold')
ax2.yaxis.set_label_position("right")
ax2.yaxis.tick_right()

# Add wage values as text labels on right bars
for bar in bars2:
    width = bar.get_width()
    ax2.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
             f'{width:.1f}', ha='right', va='center', fontsize=9)
    
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_visible(False)
ax1.spines['bottom'].set_visible(False)
ax2.spines['top'].set_visible(False)
ax2.spines['left'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['bottom'].set_visible(False)

# Add main title
fig.suptitle('OECD Hourly Wages: 2007 vs 2024', fontsize=20, fontweight='bold', y=0.98)

plt.figtext(
    0.25, 0.01,    
    "*Hourly wages are calculated as average annual wage of dependent employees divided  \n"
    "by each country’s estimated annual hours worked per dependent employee (self‑employed   \n"
    "and employers excluded). Wages are inflation adjusted and reported in 2024 constant  \n"
    "prices in USD (PPP). The annual hours worked are estimated by OECD as the total number \n"
    "of hours worked over the year, divided by the average number of people in dependent employment.",
    fontsize=11,
    ha='left',
    va='bottom',
    color='black'
)

# Remove x-axis ticks and labels
ax1.set_xticks([])  # Remove x-axis ticks
ax1.set_xticklabels([])  # Remove x-axis labels

ax2.set_xticks([])  # Remove x-axis ticks
ax2.set_xticklabels([])  # Remove x-axis labels

# Adjust layout
plt.tight_layout()
plt.subplots_adjust(wspace=0.05, top=0.88)

# Export high-resolution chart
plt.savefig(
    'hourly_wages_bars_caption',
    dpi=300,
    bbox_inches='tight',
    pad_inches=0.1,
    facecolor='lightcyan',
    transparent=False  
)

plt.show()