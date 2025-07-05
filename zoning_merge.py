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

except FileNotFoundError as e:
    print(f"Error: {e}")
    exit()


property_df.dropna(subset=["shape_wkt"], inplace=True)

property_df["geometry"] = property_df["shape_wkt"].apply(load_wkt_geometry)

property_gdf = gpd.GeoDataFrame(property_df, geometry="geometry", crs="EPSG:4326")

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
    "total_properties": humanize_number(int(total_properties)),
    "properties_with_potential": humanize_number(int(properties_with_potential)),
    "total_potential_sqft": humanize_number(float(total_properties_in_sqft)),
    "profit_estimation_usd": humanize_number(float(amount_of_potential)),
    "percentage_with_potential": float(percentage_of_properties_with_potential),

    "center_lon": float(center_lon),
    "center_lat": float(center_lat),
}


file_path = "overall_stats_boston.json"
with open(file_path, "w") as json_file:
    json.dump(overall_stats, json_file, indent=4)


zone_analysis = gdf_property_with_zoning.groupby('Zoning_Subdistrict').agg(
    total_properties = ('MAP_PAR_ID', 'count'),
    properties_with_potential=('Unused_FAR_sqft', lambda x: (x > 0).sum()),
    total_potential_sqft=('Unused_FAR_sqft', 'sum'),
)

zone_analysis['percentage_with_potential'] = (
    (zone_analysis['properties_with_potential'] / zone_analysis['total_properties']) * 100
).fillna(0)

zone_analysis['profit_estimation_usd'] = (
    zone_analysis['total_potential_sqft'] * 75
).fillna(0).apply(humanize_number)

zone_analysis['total_properties'] = zone_analysis['total_properties'].apply(humanize_number)
zone_analysis['properties_with_potential'] = zone_analysis['properties_with_potential'].apply(humanize_number)
zone_analysis['total_potential_sqft'] = zone_analysis['total_potential_sqft'].apply(humanize_number)
zone_analysis['percentage_with_potential'] = zone_analysis['percentage_with_potential'].apply(humanize_number)


zone_analysis.reset_index(inplace=True)

final_aggregates = pd.DataFrame({
    'Zoning Subdistrict': zone_analysis['Zoning_Subdistrict'],
    'Total Properties': zone_analysis['total_properties'],
    'Properties with Potential': zone_analysis['properties_with_potential'],
    'Total Potential sqft': zone_analysis['total_potential_sqft'],
    'Percentage with Potential': zone_analysis['percentage_with_potential'],
    'Profit Estimation ($)': zone_analysis['profit_estimation_usd'],
})

output_filename = 'zoning_analysis_summary_boston.xlsx'
final_aggregates.to_excel(output_filename)

gdf_property_with_zoning.to_file("gdf_property_with_zoning.geojson", driver="GeoJSON")
