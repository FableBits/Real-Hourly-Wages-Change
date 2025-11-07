"""
OECD Hourly Wages Visualization - European Map Analysis
======================================================

This script creates a choropleth map visualization showing the percentage change 
in real hourly wages across European countries from 2007 to 2024, using OECD data.

Key Features:
- Connects to MySQL database containing OECD wage analysis results
- Downloads and processes Natural Earth geographic data for European boundaries
- Handles complex geographic adjustments (Cyprus unification, Crimea reassignment)
- Creates color-coded map with custom bins and legend
- Adds statistical summary boxes showing highest/lowest performing countries

Data Source: OECD statistics on average annual wages and hours worked
Geographic Data: Natural Earth (countries, disputed areas, administrative divisions)
Output: High-resolution PNG map visualization

Author: FableBits
Repository: https://github.com/FableBits/Hourly-Wages-Change
"""

# %%
from sqlalchemy import create_engine, text
from getpass import getpass
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.ops import unary_union
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

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
# GEOGRAPHIC DATA LOADING AND PROCESSING
# ============================================================================

# Load world countries shapefile from Natural Earth
world = gpd.read_file(
    "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_countries.zip"
)

# Load disputed areas to handle territorial complexities
disputed = gpd.read_file(
    "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_disputed_areas.zip"
) 

# Unite Cyprus and Northern Cyprus for unified country representation
south_cy = world.loc[world['NAME']=='Cyprus', 'geometry']
north_cy = disputed.loc[disputed['NAME']=='N. Cyprus', 'geometry']
north_cy = north_cy.to_crs(world.crs)
full_cy = unary_union(list(south_cy) + list(north_cy))
# Smooth the merged geometry to remove artifacts
closed = full_cy.buffer(0.05, join_style=1)
full_cy = closed.buffer(-0.05, join_style=1)
world.loc[world['NAME']=='Cyprus', 'geometry'] = full_cy

# Filter to European countries plus relevant neighbors
europe = world[
    (world['CONTINENT'] == 'Europe') |
    (world['NAME'].isin(['Turkey', 'Georgia', 'Armenia', 'Azerbaijan', 'Cyprus', 'Kazakhstan'])) 
]

# Remove OECD aggregate data (keep only individual countries)
df = df[df["country"] != "OECD"].copy()

# Keep only necessary geographic columns
europe = europe[['NAME', 'geometry']] 

# ============================================================================
# DATA PREPARATION AND TERRITORIAL ADJUSTMENTS
# ============================================================================

# Check for countries in data but not in geographic dataset
df_countries = set(df['country'].unique())
natural_countries = set(europe['NAME'].unique())
df_only = df_countries - natural_countries
print("only in df:", df_only)

# Select only the wage change column needed for visualization
df = df[['country', 'pct_change_2007_2024']]

# Merge economic data with geographic boundaries
df_mrg = pd.merge(
    df,
    europe,
    left_on='country',
    right_on='NAME',
    how='right'  # Keep all countries even if no economic data
)

# Convert to GeoDataFrame for spatial operations
df_mrg = gpd.GeoDataFrame(df_mrg, geometry="geometry")

# ============================================================================
# CRIMEA TERRITORIAL ADJUSTMENT (Ukraine representation)
# ============================================================================

# Load administrative divisions to extract Crimea
admin1 = gpd.read_file(
    "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip"
)

# Extract Crimea geometry
mask = admin1['name_en'].str.contains('Crimea', case=False, na=False)
crimea_raw = admin1.loc[mask, 'geometry'].union_all()
crimea = (
    gpd.GeoSeries([crimea_raw], crs=admin1.crs)
       .to_crs(df_mrg.crs)
       .iloc[0]
       .buffer(0)  # Clean topology
)

# Remove Crimea from Russia and add to Ukraine
df_mrg.loc[df_mrg['NAME']=='Russia', 'geometry'] = (
    df_mrg.loc[df_mrg['NAME']=='Russia', 'geometry']
          .apply(lambda g: g.difference(crimea).buffer(0))
)

df_mrg.loc[df_mrg['NAME']=='Ukraine', 'geometry'] = (
    df_mrg.loc[df_mrg['NAME']=='Ukraine', 'geometry']
          .apply(lambda g: g.union(crimea))
)

# Clean up Russia's geometry (remove small islands, etc.)
russia_parts = df_mrg.loc[df_mrg['NAME']=='Russia', 'geometry'].explode(index_parts=False)
# Keep only parts larger than a minimum area threshold (tweak as needed)
min_area = 0.10  # Minimum area threshold for Russia's parts
large_parts = [part for part in russia_parts if part.area > min_area]
clean_russia = unary_union(large_parts)
df_mrg.loc[df_mrg['NAME']=='Russia', 'geometry'] = clean_russia

# ============================================================================
# DATA CATEGORIZATION AND COLOR SCHEME
# ============================================================================

# Define bins for wage change percentages
bins = [-np.inf, 0, 10, 20, 30, 40, 60, np.inf]
labels = ["< 0%", "0–10%", "10–20%", "20–30%", "30–40%", "40–60%", "60%+"]

# Categorize countries into wage change bins
df_mrg['change_bins'] = pd.cut(
    df_mrg['pct_change_2007_2024'],
    bins=bins,
    labels=labels,
    right=True,
    include_lowest=True
)

# Create color scheme: red for negative, blue gradient for positive
categories = df_mrg["change_bins"].cat.categories
pos_n = len(categories) - 1
pos_colors = plt.get_cmap("YlGnBu", pos_n)(range(pos_n))
colors = ["darksalmon"] + list(pos_colors)  # Red for negative, blue gradient for positive
cmap = mpl.colors.ListedColormap(colors)

# ============================================================================
# MAP VISUALIZATION
# ============================================================================

# Create figure with specified size and background
fig, ax = plt.subplots(1, figsize=(15, 10))
fig.patch.set_facecolor("mintcream")
ax.set_facecolor("mintcream")

# Plot choropleth map
df_mrg.plot(
    column="change_bins",
    cmap=cmap,
    categorical=True,
    linewidth=0.8,
    edgecolor="lightgrey",
    legend=False,
    legend_kwds={"title": "% change 2007–2024"},
    missing_kwds={"color": "lightgrey", "edgecolor": "white", "label": "No data"},
    ax=ax,
)

# Create custom legend with reversed order (highest first)
legend_labels = labels[::-1] + ['No data']
legend_colors = colors[::-1] + ["lightgrey"]


legend_handles = [
    Patch(facecolor=legend_colors[i], edgecolor='black', label=legend_labels[i])
    for i in range(len(legend_labels))
]

ax.legend(
    handles=legend_handles,
    title='% Change, 2007–2024',
    title_fontproperties={'weight': 'bold', 'size': 16},
    loc='lower left',
    bbox_to_anchor=(0.0, 0.37),
    frameon=False,
    fontsize=16
)

# Set map title
ax.set_title("Change in real hourly wages, 2007–2024", fontsize=20)

# ============================================================================
# STATISTICAL SUMMARY BOXES
# ============================================================================

# Highest performing countries box
table_text = r'$\bf{Highest}$' + '\n'
table_text += 'Bulgaria: 155,2%   \n'
table_text += 'Romania: 142,3%     \n'
table_text += 'Latvia: 72,4%      '

fig.text(
    0.05, 0.35,
    table_text,
    transform=ax.transAxes,
    fontfamily='DejaVu Sans',
    fontsize=14,
    verticalalignment='top',
    horizontalalignment='left',
    bbox=dict(boxstyle='round,pad=0.5', facecolor='blue', alpha=0.2)
)

# Lowest performing countries box
table_text = r'$\bf{Lowest}$' + '\n'
table_text += 'Greece: -16,7%    \n'
table_text += 'Italy: -4%     \n'
table_text += 'Netherlands: -0,9% '

fig.text(
    0.05, 0.2,
    table_text,
    transform=ax.transAxes,
    fontfamily='DejaVu Sans',
    fontsize=14,
    verticalalignment='top',
    horizontalalignment='left',
    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightsalmon', alpha=0.4)
)

# Data source attribution
x, y = 0.41, 0.18
text_str = "Data source: OECD"
bbox_props = dict(boxstyle="round,pad=0.5", edgecolor="black", facecolor="darkcyan", alpha=0.3, linewidth=1)
fig.text(x, y, text_str, ha='center', va='center', fontsize=14, bbox=bbox_props)

# Methodology footnote
plt.figtext(
    0.03, 0.05,    
    "* Hourly wages are calculated as average annual wage of dependent employees divided by each country’s estimated annual hours \n"
    "worked per dependent employee (self‑employed and employers excluded). Wages are inflation adjusted and reported in 2024 constant \n"
    "prices in USD (PPP), except for Romania and Bulgaria that are in national currency. The annual hours worked are estimated by OECD \n"
    "as the total number of hours worked over the year divided by the average number of people in dependent employment.",
    fontsize=11,
    ha='left',
    va='bottom',
    color='black'
)

# ============================================================================
# FINAL MAP CONFIGURATION AND EXPORT
# ============================================================================

# Set map boundaries to focus on Europe
ax.set_xlim(-24, 50)
ax.set_ylim(32, 72)

# Remove axis elements for clean map appearance
ax.set_axis_off()
plt.tight_layout()

# Export high-resolution map
plt.savefig(
    'hourly_wages_2007',
    dpi=300,
    bbox_inches='tight',
    pad_inches=0.1,
    facecolor='lightcyan'
)