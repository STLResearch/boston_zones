import pandas as pd
import geopandas as gpd
from shapely import wkt
import numpy as np
import json
from numerize import numerize

# from shapely.errors import WKTReadingError


def humanize_number(number):
    if number is None or np.isnan(number) or number <= 0:
        return 0
    return numerize.numerize(number)


combined_df = pd.read_csv("cambridge/final.csv")
zoning_gdf = gpd.read_file("cambridge/zones.geojson")

combined_df.dropna(subset=["shape_wkt"], inplace=True)
combined_df["geometry"] = combined_df["shape_wkt"].apply(lambda x: wkt.loads(x))

property_gdf = gpd.GeoDataFrame(combined_df, geometry="geometry", crs="EPSG:4326")

if zoning_gdf.crs != property_gdf.crs:
    print("CRS mismatch between property and zoning data")
    zoning_gdf = zoning_gdf.to_crs(property_gdf.crs)


gdf_final = gpd.sjoin(property_gdf, zoning_gdf, how="inner", predicate="within")


# Comprehensive FAR mapping for Cambridge zoning districts
def create_far_mapping():
    """
    Create a comprehensive mapping of Cambridge zoning districts to their maximum FAR values.
    For districts with different FAR for residential vs non-residential, uses the higher value.
    """

    far_mapping = {
        "A-1": 0.50,
        "A-2": 0.50,
        "B": 0.50,
        "C": 0.60,
        "C-1": 0.75,
        "C-1A": 1.25,
        "C-2": 1.75,
        "C-2A": 2.50,
        "C-2B": 1.75,
        "C-3": 3.00,
        "C-3A": 3.00,
        "C-3B": 4.00, 
        "O-1": 0.75,
        "O-2": 2.00,
        "O-2A": 1.50,
        "O-3": 3.00,
        "O-3A": 3.00,
        "BA": 1.75,
        "BA-1": 1.00,  # Higher of 1.00/0.75
        "BA-2": 1.75,  # Higher of 1.00/1.75
        "BA-3": 0.75,
        "BA-4": 2.00,  # With limitations, can go to 2.00
        "BA-5": 3.00,  # Higher of 1.00/3.0
        "BB": 3.00,  # Higher of 2.75/3.00
        "BB-1": 3.25,  # Higher of 1.50/3.25
        "BB-2": 3.00,  # Higher of 1.50/3.00
        "BC": 2.00,  # Higher of 1.25/2.00
        "BC-1": 3.00,  # Higher of 2.75/3.00
        "IA-1": 1.50,  # Higher of 1.25/1.50
        "IA-2": 4.00,  # Higher of 2.75/4.00
        "IA": 1.50,  # Higher of 1.25/1.50
        "IB-1": 3.00,  # Higher of 1.50/3.00
        "IB-2": 0.75,
        "IB": 4.00,  # Higher of 2.75/4.00
        "IC": 1.00,
        "OS": 0.25,
        "SD-1": 1.50,  # Similar to IA-1
        "SD-2": 0.50,  # Similar to B
        "SD-3": 1.00,  # Has aggregate limit, using conservative estimate
        "SD-4": 2.00,  # Similar to O-2
        "SD-4A": 2.00,  # Similar to O-2
        "SD-5": 2.00,  # Similar to O-2
        "SD-6": 3.00,  # Similar to C-3
        "SD-7": 3.00,  # Similar to BB
        "SD-8": 1.50,  # Similar to IA-1
        "SD-8A": 1.25,  # Similar to C-1A
        "SD-9": 0.60,  # Similar to C
        "SD-10(F)": 0.60,  # Similar to C
        "SD-10(H)": 0.60,  # Similar to C
        "SD-11": 2.00,  # Similar to O-2
        "SD-12": 1.75,  # Similar to C-2B
        "SD-13": 1.75,  # Similar to C-2
        "SD-14": 0.75,  # Similar to C-1
        "SD-15": 4.00,
        "MXD": 3.00,  # Mixed Use Development - conservative estimate
        "ASD": 3.00,  # Ames Street District (part of MXD)
        "CRDD": 2.50,  # Cambridgeport Revitalization - conservative estimate
        "NP": 3.00,
        "PUD-1": 3.00,
        "PUD-2": 4.00,  # 4.0 for residential
        "PUD-3": 3.00,
        "PUD-3A": 3.00,
        "PUD-4": 3.00,
        "PUD-4A": 3.00,
        "PUD-4B": 3.00,
        "PUD-4C": 3.00,
        "PUD-5": 3.90,  # Total FAR 3.9
        "PUD-6": 3.00,
        "PUD-7": 3.25,  # Based on total square footage allowance
        "PUD-8": 2.00,  # Conservative estimate based on new GFA limits
        "PUD-CDK": 2.50,  # Conservative estimate
        "PUD-KS": 3.00,
        "AOD-Q": 2.00,  # Conservative estimate for overlay
        "AOD-5": 2.00,  # Conservative estimate for overlay
        "AOD-6": 2.00,  # Conservative estimate for overlay
        "MXR": 2.00,  # Mixed Use Residential Overlay
    }

    return far_mapping


def assign_max_far(zone_type, far_mapping):
    """
    Assign maximum FAR based on zone type.
    Returns the FAR value or NaN if zone type not found.
    """
    return far_mapping.get(zone_type, np.nan)


def analyze_far_coverage(gdf, far_mapping):
    """
    Analyze how many properties have FAR assignments and identify missing zones.
    """
    unique_zones = gdf["ZONE_TYPE"].unique()
    mapped_zones = set(far_mapping.keys())
    missing_zones = set(unique_zones) - mapped_zones

    print(f"Total unique zones in data: {len(unique_zones)}")
    print(f"Zones with FAR mapping: {len(unique_zones & mapped_zones)}")
    print(f"Missing zones: {missing_zones}")

    return missing_zones


# Create FAR mapping
far_mapping = create_far_mapping()

unique_zones = gdf_final["ZONE_TYPE"].unique()
print("Unique Zone Types:")
print(unique_zones)

gdf_final["Max_FAR"] = gdf_final["ZONE_TYPE"].apply(
    lambda x: assign_max_far(x, far_mapping)
)


columns_to_keep = [
    "ML",
    "Shape_Area",
    "GROSS_AREA",
    "shape_wkt",
    "geometry",
    "ZONE_TYPE",
    "Max_FAR",
]

gdf_property_with_zoning = gdf_final[columns_to_keep].copy()

gdf_property_with_zoning.rename(
    columns={
        "Shape_Area": "Lot_Area_sqft",
        "GROSS_AREA": "Building_Area_sqft",
        "ZONE_TYPE": "Zoning_Subdistrict",
    },
    inplace=True,
)

# Todo: Remove conversion as data would be in Meter square
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


gdf_property_with_zoning["Unused_FAR_sqft_dollar_value"] = (
    gdf_property_with_zoning["Unused_FAR_sqft"] * 75
)
gdf_property_with_zoning["Unused_FAR_sqft_dollar_value"] = gdf_property_with_zoning[
    "Unused_FAR_sqft_dollar_value"
].apply(humanize_number)
gdf_property_with_zoning["lot_area_humanize_sqft"] = gdf_property_with_zoning["lot_area_sqft"].apply(humanize_number)
gdf_property_with_zoning["Building_Area_humanize_sqft"] = gdf_property_with_zoning["Building_Area_sqft"].apply(humanize_number)
gdf_property_with_zoning["Unused_FAR_humanize_sqft"] = (gdf_property_with_zoning["Unused_FAR_sqft"]).apply(humanize_number)



gdf_property_with_zoning = gdf_property_with_zoning.to_crs(epsg=4326)

AMOUNT_OF_FAR_PER_SQFT = 75

properties_with_potential = (gdf_property_with_zoning["Unused_FAR_sqft"] > 0).sum()
total_properties = len(gdf_property_with_zoning)
total_properties_in_sqft = gdf_property_with_zoning["Unused_FAR_sqft"].sum()
percentage_of_properties_with_potential = (
    properties_with_potential / total_properties
) * 100

amount_of_potential = total_properties_in_sqft * AMOUNT_OF_FAR_PER_SQFT

center_point = gdf_property_with_zoning.geometry.union_all().centroid

# Extract the longitude and latitude
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

file_path = "overall_stats_cambridge.json"
with open(file_path, "w") as json_file:
    # Use indent=4 to make the JSON file readable
    json.dump(overall_stats, json_file, indent=4)

# print(gdf_property_with_zoning.info())

zone_analysis = gdf_property_with_zoning.groupby('Zoning_Subdistrict').agg(
    total_properties = ('ML', 'count'),
    properties_with_potential=('Unused_FAR_sqft', lambda x: (x > 0).sum()),
    total_potential_sqft=('Unused_FAR_sqft', 'sum'),
)

zone_analysis['percentage_with_potential'] = (
    (zone_analysis['properties_with_potential'] / zone_analysis['total_properties']) * 100
).fillna(0)

zone_analysis['profit_estimation_usd'] = (
    zone_analysis['total_potential_sqft'] * 75
).fillna(0).round(2)


zone_analysis['total_potential_sqft'] = zone_analysis['total_potential_sqft'].round(2)
zone_analysis['percentage_with_potential'] = zone_analysis['percentage_with_potential'].round(2)

zone_analysis.reset_index(inplace=True)

zone_analysis.round(2)

final_aggregates = pd.DataFrame({
    'Zoning Subdistrict': zone_analysis['Zoning_Subdistrict'],
    'Total Properties': zone_analysis['total_properties'],
    'Properties with Potential': zone_analysis['properties_with_potential'],
    'Total Potential sqft': zone_analysis['total_potential_sqft'],
    'Percentage with Potential (%)': zone_analysis['percentage_with_potential'],
    'Profit Estimation ($)': zone_analysis['profit_estimation_usd'],
})

output_filename = 'zoning_analysis_summary_cambridge.xlsx'
final_aggregates.to_excel(output_filename)


gdf_property_with_zoning.to_file("cambridge/combined.geojson", driver="GeoJSON")
