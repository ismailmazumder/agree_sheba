import pandas as pd
import numpy as np

# 1. Read the dataset with correct encoding
df = pd.read_csv('E:\\Users\\ismail\\Desktop\\agree_sheba\\data\\datacollect\\nasa\\crop_salt_tola\\crops_data.csv', encoding='utf-16')

# 2. Define Maas & Hoffman (1977) parameters from FAO T0234E03.htm
# Threshold 'a' (dS/m) and Slope 'b' (% per dS/m)
salt_tolerance_params = {
    'Barley': {'a': 8.0, 'b': 5.0},
    'Cotton': {'a': 7.7, 'b': 5.2},
    'Wheat': {'a': 6.0, 'b': 7.1},
    'Soybean': {'a': 5.0, 'b': 20.0},
    'Sugar Beet': {'a': 7.0, 'b': 5.9},
    'Sugarcane': {'a': 1.7, 'b': 5.9},
    'Maize': {'a': 1.7, 'b': 12.0},
    'Sunflower': {'a': 4.8, 'b': 5.0},
    'Sorghum': {'a': 6.8, 'b': 16.0},
    'Boro dhan': {'a': 3.0, 'b': 12.0},
    'T. Aman dhan': {'a': 3.0, 'b': 12.0},
    'T. Aus dhan': {'a': 3.0, 'b': 12.0},
    'B. Aus dhan': {'a': 3.0, 'b': 12.0},
    'B. Aman dhan': {'a': 3.0, 'b': 12.0},
    # Crops with no published data in Maas & Hoffman (1977) / FAO T0234E03
    'Mustard': {'a': np.nan, 'b': np.nan},
    'Lentil': {'a': np.nan, 'b': np.nan},
    'Mungbean': {'a': np.nan, 'b': np.nan},
    'Sesame': {'a': np.nan, 'b': np.nan},
    'Jute (Deshi)': {'a': np.nan, 'b': np.nan},
    'Jute (Tosa)': {'a': np.nan, 'b': np.nan},
}

# 3. Function to calculate ECe at 100/90/75/50/0 % yield using Y = 100 - b*(ECe - a)
def compute_salt_tolerance(row):
    crop = row['crop_name']
    params = salt_tolerance_params.get(crop, None)
    
    # Handle unprinted crops (not penalized, gap stated)
    if params is None or pd.isna(params['a']):
        return "Unpublished / Data Unavailable (Not Penalized)"
    
    a = params['a']
    b = params['b']
    
    ec_100 = a
    ec_90 = a + (10 / b)
    ec_75 = a + (25 / b)
    ec_50 = a + (50 / b)
    ec_0 = a + (100 / b)
    
    return (f"Threshold(a)={a} dS/m, Slope(b)={b}% | "
            f"100%:{ec_100:.1f}, 90%:{ec_90:.2f}, 75%:{ec_75:.2f}, "
            f"50%:{ec_50:.2f}, 0%:{ec_0:.2f} dS/m")

# 4. Apply to the DataFrame
df['salt_tolerance'] = df.apply(compute_salt_tolerance, axis=1)

# 5. Save the updated file
df.to_csv('crops_data_with_salt_tolerance.csv', index=False, encoding='utf-16')
print("Successfully generated 'crops_data_with_salt_tolerance.csv' with salt tolerance scores!")