import pandas as pd



# Merging property-assessment data with parcels data

df_parcels = pd.read_csv("parcels.csv", low_memory=False)
df_assessment = pd.read_csv("assessments.csv", low_memory=False)

df_assessment['PID'] = df_assessment['PID'].astype(str)
df_assessment.rename(columns={'PID': 'MAP_PAR_ID'}, inplace=True)


merged_df = pd.merge(df_parcels, df_assessment, on='MAP_PAR_ID', how='inner')

columns_needed = [
    'MAP_PAR_ID',
    'Shape_Area',
    'GROSS_AREA',
    'shape_wkt'
]

df_parcels_with_assessment = merged_df[[col for col in columns_needed if col in merged_df.columns]]

df_parcels_with_assessment.dropna(subset=['Shape_Area', 'GROSS_AREA'], inplace=True)

# df_parcels_with_assessment.to_csv('parcels_with_assessment.csv', index=False)

print(df_parcels_with_assessment.count())





