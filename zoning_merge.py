import pandas as pd
import geopandas as gpd
import numpy as np
from shapely import wkt
import json
from numerize import numerize


def load_wkt_geometry(wkt_string):
    try:
        return wkt.loads(wkt_string)
    except Exception as e:
        print(f"Error loading WKT: {e}")
        return None


def humanize_number(number):
    if number is None or np.isnan(number) or number <= 0:
        return 0
    return numerize.numerize(number)


try:
    property_df = pd.read_csv("parcels_with_assessment.csv", low_memory=False)
    zoning_gdf = gpd.read_file("subdistricts.geojson")

    # property_df['MAP_PAR_ID'] = property_df['MAP_PAR_ID'].astype(str)
    # zoning_df['MAP_PAR_ID'] = zoning_df['MAP_PAR_ID'].astype(str)
except FileNotFoundError as e:
    print(f"Error: {e}")
    exit()


property_df.dropna(subset=["shape_wkt"], inplace=True)
# zoning_df.dropna(subset=['shape_wkt'], inplace=True)

# print(zoning_df.head(2))

property_df["geometry"] = property_df["shape_wkt"].apply(load_wkt_geometry)
# zoning_df['geometry'] = zoning_df['shape_wkt'].apply(load_wkt_geometry)

property_gdf = gpd.GeoDataFrame(property_df, geometry="geometry", crs="EPSG:4326")
# zoning_gdf = gpd.GeoDataFrame(zoning_df, geometry='geometry', crs='EPSG:4326')

if zoning_gdf.crs != property_gdf.crs:
    print("CRS mismatch between property and zoning data")
    zoning_gdf = zoning_gdf.to_crs(property_gdf.crs)

gdf_final = gpd.sjoin(property_gdf, zoning_gdf, how="inner", predicate="within")

columns_to_keep = [
    "MAP_PAR_ID",
    "Shape_Area_left",
    "GROSS_AREA",
    "shape_wkt_left",
    "geometry",
    "Zoning_Subdistrict",
    "Max_FAR",
]

gdf_property_with_zoning = gdf_final[columns_to_keep].copy()


gdf_property_with_zoning.rename(
    columns={
        "Shape_Area_left": "Lot_Area_sqft",
        "GROSS_AREA": "Building_Area_sqft",
        "shape_wkt_left": "shape_wkt",
    },
    inplace=True,
)

SQM_TO_SQFT = 10.7639


gdf_property_with_zoning = gdf_property_with_zoning.to_crs(epsg=26986)


gdf_property_with_zoning["lot_area_sqft"] = (
    gdf_property_with_zoning.geometry.area * SQM_TO_SQFT
)


gdf_property_with_zoning["Used_FAR"] = (
    gdf_property_with_zoning["Building_Area_sqft"]
    / gdf_property_with_zoning["lot_area_sqft"]
)


gdf_property_with_zoning["Unused_FAR"] = (
    gdf_property_with_zoning["Max_FAR"] - gdf_property_with_zoning["Used_FAR"]
)

gdf_property_with_zoning["Unused_FAR_sqft"] = (
    gdf_property_with_zoning["Unused_FAR"] * gdf_property_with_zoning["lot_area_sqft"]
)


gdf_property_with_zoning["Unused_FAR_sqft"] = np.maximum(
    gdf_property_with_zoning["Unused_FAR_sqft"], 0
)

gdf_property_with_zoning["Unused_FAR_sqft"] = (gdf_property_with_zoning["Unused_FAR_sqft"]).fillna(0)





gdf_property_with_zoning["Unused_FAR_sqft_dollar_value"] = (
    gdf_property_with_zoning["Unused_FAR_sqft"] * 75
)

gdf_property_with_zoning["Unused_FAR_sqft_dollar_value"] = gdf_property_with_zoning[
    "Unused_FAR_sqft_dollar_value"
].apply(humanize_number)
gdf_property_with_zoning["lot_area_humanize_sqft"] = gdf_property_with_zoning["lot_area_sqft"].apply(humanize_number)
gdf_property_with_zoning["Building_Area_humanize_sqft"] = gdf_property_with_zoning["Building_Area_sqft"].apply(humanize_number)
gdf_property_with_zoning["Unused_FAR_humanize_sqft"] = (gdf_property_with_zoning["Unused_FAR_sqft"]).apply(humanize_number)


AMOUNT_OF_FAR_PER_SQFT = 75

properties_with_potential = (gdf_property_with_zoning["Unused_FAR_sqft"] > 0).sum()
total_properties = len(gdf_property_with_zoning)
total_properties_in_sqft = gdf_property_with_zoning["Unused_FAR_sqft"].sum()
percentage_of_properties_with_potential = (
    properties_with_potential / total_properties
) * 100

amount_of_potential = total_properties_in_sqft * AMOUNT_OF_FAR_PER_SQFT

gdf_property_with_zoning = gdf_property_with_zoning.to_crs(epsg=4326)

center_point = gdf_property_with_zoning.geometry.union_all().centroid
center_lon = center_point.x
center_lat = center_point.y

overall_stats = {
    "total_properties": int(total_properties),
    "properties_with_potential": int(properties_with_potential),
    "total_potential_sqft": float(total_properties_in_sqft),
    "profit_estimation_usd": float(amount_of_potential),
    "percentage_with_potential": float(percentage_of_properties_with_potential),
    "center_lon": float(center_lon),
    "center_lat": float(center_lat),
}

file_path = "overall_stats_boston.json"
with open(file_path, "w") as json_file:
    json.dump(overall_stats, json_file, indent=4)


gdf_property_with_zoning.to_file("gdf_property_with_zoning.geojson", driver="GeoJSON")
