import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.errors import WKTReadingError

def load_wkt_geometry(wkt_string):
    try: 
        return wkt.loads(wkt_string)
    except WKTReadingError as e:
        print(f"Error loading WKT: {e}")
        return None

def get_heatmap_color(used_far):
    if used_far >= 2.0:
        return '#2a9d8f';
    elif used_far >= 0:
        return '#e9c46a';
    else:
        return '#e76f51';

try: 
    property_df = pd.read_csv("parcels_with_assessment.csv", low_memory=False)
    zoning_gdf = gpd.read_file("subdistricts.geojson")

    print("Property Data Loaded", len(property_df))
    print("Zoning Data Loaded", len(zoning_gdf))

    # property_df['MAP_PAR_ID'] = property_df['MAP_PAR_ID'].astype(str)
    # zoning_df['MAP_PAR_ID'] = zoning_df['MAP_PAR_ID'].astype(str)
except FileNotFoundError as e:
    print(f"Error: {e}")
    exit()


property_df.dropna(subset=['shape_wkt'], inplace=True)
# zoning_df.dropna(subset=['shape_wkt'], inplace=True)

# print(zoning_df.head(2))

property_df['geometry'] = property_df['shape_wkt'].apply(load_wkt_geometry)
# zoning_df['geometry'] = zoning_df['shape_wkt'].apply(load_wkt_geometry)

property_gdf = gpd.GeoDataFrame(property_df, geometry='geometry', crs='EPSG:4326')
# zoning_gdf = gpd.GeoDataFrame(zoning_df, geometry='geometry', crs='EPSG:4326')

if zoning_gdf.crs != property_gdf.crs:
    print("CRS mismatch between property and zoning data")
    zoning_gdf = zoning_gdf.to_crs(property_gdf.crs)

gdf_final = gpd.sjoin(property_gdf, zoning_gdf, how='inner', predicate='within')

columns_to_keep = [
    'MAP_PAR_ID',
    'Shape_Area_left',
    'GROSS_AREA',
    'shape_wkt_left',
    'geometry',
    'Zoning_Subdistrict',
    'Max_FAR',
]

gdf_property_with_zoning = gdf_final[columns_to_keep].copy()



gdf_property_with_zoning.rename(columns={
    'Shape_Area_left': 'Lot_Area_sqft',
    'GROSS_AREA': 'Building_Area_sqft',
    'shape_wkt_left': 'shape_wkt',
}, inplace=True)


print("CRS",gdf_property_with_zoning.crs)

gdf_property_with_zoning = gdf_property_with_zoning.to_crs(epsg=26986)
gdf_property_with_zoning['lot_area_m2'] = gdf_property_with_zoning.geometry.area
gdf_property_with_zoning['building_area_m2'] = gdf_property_with_zoning['Building_Area_sqft'] * 0.092903

gdf_property_with_zoning['Used_FAR'] = gdf_property_with_zoning['building_area_m2'] / gdf_property_with_zoning['lot_area_m2']
gdf_property_with_zoning['Unused_FAR'] = gdf_property_with_zoning['Max_FAR'] - gdf_property_with_zoning['Used_FAR']

gdf_property_with_zoning['fill'] = gdf_property_with_zoning['Unused_FAR'].apply(get_heatmap_color)
gdf_property_with_zoning['stroke'] = 'black'
gdf_property_with_zoning['stroke-width'] = 0.5

print("CRS",gdf_property_with_zoning.crs)
gdf_property_with_zoning = gdf_property_with_zoning.to_crs(epsg=4326)

print("CRS",gdf_property_with_zoning.crs)

gdf_property_with_zoning.to_file('gdf_property_with_zoning.geojson', driver='GeoJSON')
# gdf_property_with_zoning.to_csv('gdf_property_with_zoning.csv')


# print("Number of rows in gdf_property_with_zoning:", len(gdf_property_with_zoning))
# print("Shape of gdf_property_with_zoning:", gdf_property_with_zoning.shape)
