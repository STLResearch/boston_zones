import pandas as pd
import geopandas as gpd
from shapely import wkt

# Load the datasets
df_parcels = pd.read_csv("cambridge/parcel.csv", low_memory=False)
df_property = pd.read_csv("cambridge/prop.csv", low_memory=False)


# Clean the data - remove rows with null join keys
df_parcels = df_parcels.dropna(subset=["ML"])
df_property = df_property.dropna(subset=["Map/Lot"])

# Convert ML and Map/Lot to string and strip whitespace for consistent matching
df_parcels["ML"] = df_parcels["ML"].astype(str).str.strip()
df_property["Map/Lot"] = df_property["Map/Lot"].astype(str).str.strip()

# Perform the join on ML field
joined_df = df_parcels.merge(df_property, left_on="ML", right_on="Map/Lot", how="inner")


# Create geometry from the WKT string
joined_df["geometry"] = joined_df["the_geom"].apply(lambda x: wkt.loads(x))

# Convert to GeoDataFrame in WGS84
joined_gdf = gpd.GeoDataFrame(joined_df, geometry="geometry", crs="EPSG:4326")


# Convert back to WGS84 for final output

# Prepare final columns
joined_gdf["GROSS_AREA"] = joined_gdf["LandArea"]
joined_gdf["shape_wkt"] = joined_gdf["the_geom"]
joined_gdf["Shape_Area"] = joined_gdf["SHAPE_STAr"]


# Select only the columns needed
columns_needed = ["ML", "Shape_Area", "GROSS_AREA", "shape_wkt"]
final_gdf = joined_gdf[columns_needed].copy()

final_gdf.dropna(subset=["Shape_Area", "GROSS_AREA"], inplace=True)

# Save to CSV
final_gdf.to_csv("cambridge/final.csv", index=False)
