import os
import shutil
import pandas as pd

# Directories
PDF_DIR = r"E:\Users\ismail\Desktop\collector_sheba\data\datacollect\gov\each_crop_data\crops_pdf"
SRC_DATA_DIR = r"D:\Users\ismail\Documents\Default Project"
DEST_CSV_DIR = r"E:\Users\ismail\Desktop\collector_sheba\data\datacollect\gov\each_crop_data\cops_csv"

# Mapping from canonical crop name (from crops_data.csv / PDF filename without extension)
# to the pre-extracted source directory in Default Project
CROP_SRC_MAP = {
    "Banana": "banana_bogura",
    "Boro dhan": "rice_boro_bogura",
    "Bottle Gourd": "gourd_bogra",
    "Brinjal": "brinjal_bogra",
    "Chilli": "chilli_bogra",
    "Cotton": "cotton_bogura",
    "Cucumber": "cucumber_bogra",
    "Garlic": "garlic_bogura",
    "Ground Nut": "groundnut_kharif_1_barishal",
    "Guava": "guava_barishal",
    "Jackfruit": "jackfruit_bogura",
    "Jujube": "jujube_dhaka",
    "Jute (Deshi)": "jute_bogura",
    "Lentil": "lentil_bogura",
    "Litchi": "litchi_bogura",
    "Maize": "maize_kharif_1_bogura",
    "Mango": "mango_dinajpur",
    "Mungbean": "green_gram_robi_dinajpur",
    "Mustard": "mustard_bogura",
    "Onion": "onion_bogura",
    "Papaya": "papaya_bogura",
    "Pineapple": "pineapple_dhaka",
    "Pointed Gourd": "pointed_gourd_bogura",
    "Potato": "potato_bogura",
    "Pumpkin (Sweet gourd)": "pumpkin_bogura",
    "Soybean": "soybean_barisal",
    "Sugarcane": "sugarcane_bogura",
    "T. Aman dhan": "rice_aman_bogura",
    "T. Aus dhan": "rice_aus_bogura",
    "Tomato": "tomato_barisal",
    "Wheat": "wheat_bogura",
}

def convert_all():
    os.makedirs(DEST_CSV_DIR, exist_ok=True)
    success_count = 0

    for crop_name, src_folder_name in CROP_SRC_MAP.items():
        src_path = os.path.join(SRC_DATA_DIR, src_folder_name)
        dest_crop_dir = os.path.join(DEST_CSV_DIR, crop_name)

        if not os.path.exists(src_path):
            print(f"[WARN] Source folder not found: {src_path}")
            continue

        os.makedirs(dest_crop_dir, exist_ok=True)

        csv_files = [
            "1_weekly_weather.csv",
            "2_diseases.csv",
            "3_insect_pests.csv",
            "4_weather_warnings.csv",
        ]

        for fname in csv_files:
            src_file = os.path.join(src_path, fname)
            dest_file = os.path.join(dest_crop_dir, fname)

            if os.path.exists(src_file):
                try:
                    df = pd.read_csv(src_file)
                    # Update crop column to exact canonical crop name
                    if "crop" in df.columns:
                        df["crop"] = crop_name
                    df.to_csv(dest_file, index=False, encoding="utf-8-sig")
                except Exception as e:
                    # Fallback to direct copy if reading fails
                    shutil.copy2(src_file, dest_file)
            else:
                print(f"[WARN] Missing {fname} in {src_path}")

        print(f"[OK] {crop_name} -> {dest_crop_dir}")
        success_count += 1

    print(f"\nCompleted! Processed {success_count}/{len(CROP_SRC_MAP)} crops into {DEST_CSV_DIR}")

if __name__ == "__main__":
    convert_all()
