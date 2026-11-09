import os
import json
import re
import pandas as pd
import numpy as np

BASE_DIR = r"E:\Users\ismail\Desktop\collector_sheba\data\datacollect\gov\each_crop_data\cops_csv"
BIG_JSON_PATH = os.path.join(BASE_DIR, "crops_weather_and_warnings.json")
ROOT_BIG_JSON_PATH = r"E:\Users\ismail\Desktop\collector_sheba\data\datacollect\gov\each_crop_data\crops_weather_and_warnings.json"

def clean_val(val):
    """Clean data values for json serialization."""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (np.floating, float)):
        if np.isnan(val):
            return None
        return int(val) if val.is_integer() else round(float(val), 2)
    if isinstance(val, (np.integer, int)):
        return int(val)
    s = str(val).strip()
    # Clean broken degree symbols
    s = s.replace("\ufffd", "°").replace("\uf0b0", "°")
    return s

def clean_records(df: pd.DataFrame):
    """Convert dataframe rows to cleaned dictionary records."""
    records = df.to_dict(orient="records")
    cleaned = []
    for row in records:
        cleaned_row = {col: clean_val(val) for col, val in row.items()}
        cleaned.append(cleaned_row)
    return cleaned

def build_crops_json():
    all_crops_data = {}
    crop_folders = [d for d in sorted(os.listdir(BASE_DIR)) if os.path.isdir(os.path.join(BASE_DIR, d))]

    for folder in crop_folders:
        folder_path = os.path.join(BASE_DIR, folder)
        weather_file = os.path.join(folder_path, "1_weekly_weather.csv")
        warnings_file = os.path.join(folder_path, "4_weather_warnings.csv")

        if not os.path.exists(weather_file) or not os.path.exists(warnings_file):
            print(f"[SKIP] Missing files in {folder}")
            continue

        # 1. Process weekly weather: keep the 1st row for each phenological_stage
        w_df = pd.read_csv(weather_file)
        subset = ["season", "phenological_stage"] if "season" in w_df.columns else ["phenological_stage"]
        # Drop duplicates keeping the first occurrence
        stages_df = w_df.drop_duplicates(subset=subset, keep="first")
        stages_records = clean_records(stages_df)

        # 2. Process weather warnings
        warn_df = pd.read_csv(warnings_file)
        warnings_records = clean_records(warn_df)

        # Extract general crop metadata
        region = stages_records[0].get("region") if stages_records else None
        duration_days = stages_records[0].get("duration_days") if stages_records else None

        crop_obj = {
            "crop": folder,
            "region": region,
            "duration_days": duration_days,
            "phenological_stages_count": len(stages_records),
            "phenological_stages_weather": stages_records,
            "weather_warnings_count": len(warnings_records),
            "weather_warnings": warnings_records
        }

        all_crops_data[folder] = crop_obj

        # Save individual JSON inside the crop folder
        individual_json_path = os.path.join(folder_path, "weather_and_warnings.json")
        with open(individual_json_path, "w", encoding="utf-8") as f:
            json.dump(crop_obj, f, indent=2, ensure_ascii=False)

    # Save the combined BIG JSON file in cops_csv
    with open(BIG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(all_crops_data, f, indent=2, ensure_ascii=False)

    # Also save a copy at parent folder for convenience
    with open(ROOT_BIG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(all_crops_data, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Processed {len(all_crops_data)} crops.")
    print(f"Big JSON saved to:\n  1. {BIG_JSON_PATH}\n  2. {ROOT_BIG_JSON_PATH}")
    print(f"Individual JSONs saved inside each of the {len(all_crops_data)} crop folders as 'weather_and_warnings.json'.")

if __name__ == "__main__":
    build_crops_json()
