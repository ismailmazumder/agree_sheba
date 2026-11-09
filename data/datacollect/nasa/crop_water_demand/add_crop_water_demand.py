"""
Add FAO-based crop water-demand estimates to crops_data.csv.

Input:
  crops_data.csv (UTF-16 CSV; crop/situation/season columns)

Output:
  crops_data_with_water_demand.csv (UTF-8-SIG)

The script downloads NASA POWER daily weather for 2001-2024, calculates
FAO-56 reference evapotranspiration (ET0), then estimates crop ET (ETc)
using FAO crop coefficients (Kc). Related-crop proxies are labelled.

IMPORTANT:
- Enter the centroid of the same ROI used to generate your soil values.
- Bangladesh season month windows below are simplified calendar windows.
- Crops without a defensible coefficient are left blank, not guessed.
- Rainfall minus ETc is only a gross comparison, not net irrigation demand.
"""

from pathlib import Path
import math
import requests
import numpy as np
import pandas as pd

INPUT_FILE = Path(__file__).with_name("crops_data.csv")
OUTPUT_FILE = Path(__file__).with_name("crops_data_with_water_demand.csv")

LAT = float(input("ROI centre latitude (e.g. 23.45): ").strip())
LON = float(input("ROI centre longitude (e.g. 91.18): ").strip())

START_DATE = "20010101"
END_DATE = "20241231"
ELEVATION_M = 10.0  # change if you know the ROI elevation

# Values supplied in your location summary; retained as comparison/context fields.
USER_PRECIPITABLE_WATER = 4.5025
USER_TOPSOIL_WETNESS = 0.763333
USER_MEAN_TEMP_C = 25.88
USER_WIND_10M_KMH = 10.40
USER_MEAN_RAINFALL_MM_DAY = 6.59

# Approximate Bangladesh agricultural seasons.
SEASON_MONTHS = {
    "Rabi": [11, 12, 1, 2],
    "Kharif-1": [3, 4, 5, 6],
    "Kharif-2": [7, 8, 9, 10],
}

# (Kc_initial, Kc_mid, Kc_end, source/note)
# FAO-56 Table 12 values are used where available.
# "proxy" means a related FAO crop/group is being used, not a measured
# Bangladesh-specific coefficient. Update these with local research values.
KC_MAP = {
    # Cereals and rice
    "boro dhan": (1.05, 1.20, 0.75, "FAO-56 rice; Kc_end midpoint of 0.60-0.90 range"),
    "t. aman dhan": (1.05, 1.20, 0.75, "FAO-56 rice; Kc_end midpoint of 0.60-0.90 range"),
    "b. aman dhan": (1.05, 1.20, 0.75, "FAO-56 rice; Kc_end midpoint of 0.60-0.90 range"),
    "t. aus dhan": (1.05, 1.20, 0.75, "FAO-56 rice; Kc_end midpoint of 0.60-0.90 range"),
    "b. aus dhan": (1.05, 1.20, 0.75, "FAO-56 rice; Kc_end midpoint of 0.60-0.90 range"),
    "barley": (0.30, 1.15, 0.25, "FAO-56 Table 12: barley"),
    "wheat": (0.70, 1.15, 0.325, "FAO-56 winter wheat, non-frozen soil; Kc_end midpoint"),
    "maize": (0.30, 1.20, 0.475, "FAO-56 field maize; Kc_end midpoint of 0.35-0.60 range"),
    "kaon": (0.30, 1.00, 0.30, "FAO-56 millet proxy"),
    "proso millet": (0.30, 1.00, 0.30, "FAO-56 millet"),

    # Roots, tubers and vegetables
    "potato": (0.50, 1.15, 0.75, "FAO-56 Table 12: potato"),
    "sweet potato": (0.50, 1.15, 0.65, "FAO-56 Table 12: sweet potato"),
    "broccoli": (0.70, 1.05, 0.95, "FAO-56 Table 12: broccoli"),
    "cabbage": (0.70, 1.05, 0.95, "FAO-56 Table 12: cabbage"),
    "carrot": (0.70, 1.05, 0.95, "FAO-56 Table 12: carrot"),
    "cauliflower": (0.70, 1.05, 0.95, "FAO-56 small-vegetable group proxy"),
    "garlic": (0.70, 1.00, 0.70, "FAO-56 Table 12: garlic"),
    "onion": (0.70, 1.05, 0.75, "FAO-56 dry-onion values"),
    "spinach": (0.70, 1.00, 0.95, "FAO-56 Table 12: spinach"),
    "radish": (0.70, 0.90, 0.85, "FAO-56 Table 12: radish"),
    "tomato": (0.60, 1.15, 0.80, "FAO-56 Table 12: tomato; Kc_end midpoint"),
    "brinjal": (0.60, 1.05, 0.90, "FAO-56 Table 12: eggplant"),
    "chilli": (0.60, 1.05, 0.90, "FAO-56 sweet-pepper proxy"),
    "cucumber": (0.60, 1.00, 0.75, "FAO-56 fresh-market cucumber"),
    "cucumber (khira)": (0.60, 1.00, 0.75, "FAO-56 fresh-market cucumber"),
    "water melon": (0.40, 1.00, 0.75, "FAO-56 Table 12: watermelon"),
    "musk melon": (0.50, 1.05, 0.75, "FAO-56 sweet-melon proxy"),
    "ash gourd": (0.50, 1.00, 0.80, "FAO-56 cucurbit-group proxy"),
    "bitter gourd": (0.50, 1.00, 0.80, "FAO-56 cucurbit-group proxy"),
    "bottle gourd": (0.50, 1.00, 0.80, "FAO-56 cucurbit-group proxy"),
    "pumpkin (sweet gourd)": (0.50, 1.00, 0.80, "FAO-56 pumpkin/squash proxy"),
    "ridge gourd": (0.50, 1.00, 0.80, "FAO-56 cucurbit-group proxy"),
    "snake gourd": (0.50, 1.00, 0.80, "FAO-56 cucurbit-group proxy"),
    "sponge gourd": (0.50, 1.00, 0.80, "FAO-56 cucurbit-group proxy"),
    "pointed gourd": (0.50, 1.00, 0.80, "FAO-56 cucurbit-group proxy"),
    "teasle gourd": (0.50, 1.00, 0.80, "FAO-56 cucurbit-group proxy"),

    # Legumes and pulses
    "country bean": (0.50, 1.05, 0.90, "FAO-56 green-bean proxy"),
    "yard long bean": (0.50, 1.05, 0.90, "FAO-56 green-bean proxy"),
    "cowpea": (0.40, 1.05, 0.45, "FAO-56 green-gram/cowpea group; Kc_end midpoint"),
    "black gram": (0.40, 1.15, 0.35, "FAO-56 dry-bean/pulse proxy"),
    "gram / chickpea": (0.40, 1.00, 0.35, "FAO-56 Table 12: chickpea"),
    "grass pea": (0.40, 1.10, 0.30, "FAO-56 lentil/pulse proxy"),
    "ground nut": (0.40, 1.15, 0.60, "FAO-56 Table 12: groundnut"),
    "lentil": (0.40, 1.10, 0.30, "FAO-56 Table 12: lentil"),
    "mungbean": (0.40, 1.05, 0.45, "FAO-56 green-gram/cowpea group proxy"),
    "soybean": (0.40, 1.15, 0.50, "FAO-56 Table 12: soybean"),

    # Fibre and oil crops
    "cotton": (0.35, 1.175, 0.60, "FAO-56 Table 12: cotton; Kc_mid midpoint"),
    "linseed": (0.35, 1.10, 0.25, "FAO-56 flax proxy"),
    "sesame": (0.35, 1.10, 0.25, "FAO-56 Table 12: sesame"),
    "sunflower": (0.35, 1.075, 0.35, "FAO-56 Table 12: sunflower; Kc_mid midpoint"),
    "mustard": (0.35, 1.075, 0.35, "FAO-56 rapeseed/canola proxy"),

    # Other crops with separate FAO crop-water guidance
    "sugarcane": (0.50, 1.05, 0.60, "FAO crop-water guide: humid, low-wind virgin sugarcane; local cycle matters"),
    "tea": (0.95, 0.95, 0.95, "FAO crop-water guide: year-round Kc for tea without cover crop/shade"),

    # Leafy vegetables/herbs: related-crop proxies
    "red amaranth": (0.70, 1.00, 0.95, "FAO-56 spinach/leafy-vegetable proxy"),
    "stem amaranth": (0.70, 1.00, 0.95, "FAO-56 spinach/leafy-vegetable proxy"),
    "indian spinach": (0.70, 1.00, 0.95, "FAO-56 spinach/leafy-vegetable proxy"),
    "coriander": (0.70, 1.00, 0.95, "FAO-56 leafy-vegetable proxy"),
}

def saturation_vapour_pressure(temp_c):
    """FAO-56 saturation vapour pressure, kPa."""
    return 0.6108 * np.exp((17.27 * temp_c) / (temp_c + 237.3))

def extraterrestrial_radiation(latitude_deg, day_of_year):
    """FAO-56 extraterrestrial radiation Ra, MJ m-2 day-1."""
    lat = math.radians(latitude_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * day_of_year / 365)
    solar_declination = 0.409 * np.sin(2 * np.pi * day_of_year / 365 - 1.39)
    sunset_angle = np.arccos(
        np.clip(-np.tan(lat) * np.tan(solar_declination), -1, 1)
    )
    gsc = 0.0820
    return (24 * 60 / np.pi) * gsc * dr * (
        sunset_angle * np.sin(lat) * np.sin(solar_declination)
        + np.cos(lat) * np.cos(solar_declination) * np.sin(sunset_angle)
    )

def calculate_fao56_eto(weather, latitude_deg, elevation_m):
    """Daily FAO-56 Penman-Monteith reference ET0, in mm/day."""
    w = weather.copy()
    required = ["T2M", "T2M_MAX", "T2M_MIN", "ALLSKY_SFC_SW_DWN"]
    missing = [c for c in required if c not in w.columns]
    if missing:
        raise ValueError(f"NASA POWER response is missing required parameters: {missing}")

    tmean, tmax, tmin = w["T2M"], w["T2M_MAX"], w["T2M_MIN"]
    rs = w["ALLSKY_SFC_SW_DWN"]  # AG daily solar radiation: MJ/m2/day

    # Prefer 2 m wind; otherwise convert 10 m wind to 2 m per FAO-56.
    if "WS2M" in w.columns and w["WS2M"].notna().any():
        u2 = w["WS2M"]
    elif "WS10M" in w.columns and w["WS10M"].notna().any():
        u2 = w["WS10M"] * 4.87 / np.log(67.8 * 10 - 5.42)
    else:
        raise ValueError("NASA POWER did not return WS2M or WS10M.")

    es = (saturation_vapour_pressure(tmax) + saturation_vapour_pressure(tmin)) / 2

    # Actual vapour pressure: dewpoint preferred; mean RH is fallback.
    ea = pd.Series(np.nan, index=w.index, dtype=float)
    if "T2MDEW" in w.columns:
        ea = ea.fillna(saturation_vapour_pressure(w["T2MDEW"]))
    if "RH2M" in w.columns:
        ea = ea.fillna((w["RH2M"] / 100.0) * es)
    if ea.isna().all():
        raise ValueError("Need T2MDEW or RH2M from NASA POWER.")

    pressure_from_elevation = 101.3 * (((293 - 0.0065 * elevation_m) / 293) ** 5.26)
    if "PS" in w.columns and w["PS"].notna().any():
        pressure_kpa = w["PS"].fillna(pressure_from_elevation)
    else:
        pressure_kpa = pressure_from_elevation

    gamma = 0.000665 * pressure_kpa
    delta = (4098 * saturation_vapour_pressure(tmean)) / ((tmean + 237.3) ** 2)

    ra = pd.Series(
        [extraterrestrial_radiation(latitude_deg, d) for d in w.index.dayofyear],
        index=w.index,
        dtype=float,
    )
    rso = (0.75 + 2e-5 * elevation_m) * ra
    rns = (1 - 0.23) * rs

    tmax_k, tmin_k = tmax + 273.16, tmin + 273.16
    sigma = 4.903e-9  # MJ K-4 m-2 day-1
    cloud_factor = (1.35 * (rs / rso).clip(lower=0.3, upper=1.0)) - 0.35
    rnl = (
        sigma * ((tmax_k ** 4 + tmin_k ** 4) / 2)
        * (0.34 - 0.14 * np.sqrt(ea.clip(lower=0)))
        * cloud_factor
    )
    rn = rns - rnl
    vpd = (es - ea).clip(lower=0)

    numerator = (
        0.408 * delta * rn
        + gamma * (900 / (tmean + 273)) * u2 * vpd
    )
    denominator = delta + gamma * (1 + 0.34 * u2)
    return (numerator / denominator).clip(lower=0).rename("ET0_mm_day")

def download_nasa_power():
    parameters = (
        "T2M,T2M_MAX,T2M_MIN,T2MDEW,RH2M,WS2M,WS10M,"
        "ALLSKY_SFC_SW_DWN,PRECTOTCORR,PS"
    )
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    query = {
        "parameters": parameters,
        "community": "AG",
        "longitude": LON,
        "latitude": LAT,
        "start": START_DATE,
        "end": END_DATE,
        "format": "JSON",
        "time-standard": "UTC",
    }

    print("Downloading NASA POWER daily weather data...")
    response = requests.get(url, params=query, timeout=120)
    response.raise_for_status()
    payload = response.json()

    try:
        parameter_data = payload["properties"]["parameter"]
    except KeyError:
        raise RuntimeError(f"Unexpected NASA POWER response: {payload}")

    weather = pd.DataFrame({
        name: pd.Series(values, dtype=float)
        for name, values in parameter_data.items()
    })
    weather.index = pd.to_datetime(weather.index, format="%Y%m%d")
    weather = weather.sort_index().replace(-999, np.nan)

    if "PRECTOTCORR" not in weather.columns:
        raise ValueError("NASA POWER did not return PRECTOTCORR rainfall.")

    weather["ET0_mm_day"] = calculate_fao56_eto(weather, LAT, ELEVATION_M)
    return weather

def read_crop_csv():
    try:
        crops = pd.read_csv(INPUT_FILE, encoding="utf-16")
    except UnicodeError:
        crops = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

    for col in ["crop_name", "season_name"]:
        if col not in crops.columns:
            raise ValueError(f"Input CSV must contain '{col}'.")
        crops[col] = crops[col].astype(str).str.strip()
    return crops

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError("Put this script in the same folder as crops_data.csv.")

    crops = read_crop_csv()
    weather = download_nasa_power()

    # Seasonal climatology from the same 2001-2024 period.
    season_stats = {}
    for season, months in SEASON_MONTHS.items():
        subset = weather[weather.index.month.isin(months)]
        season_stats[season] = {
            "ET0": subset["ET0_mm_day"].mean(),
            "rain": subset["PRECTOTCORR"].mean(),
        }

    kc_values = crops["crop_name"].apply(
        lambda name: KC_MAP.get(str(name).strip().lower())
    )
    crops["Kc_initial"] = kc_values.apply(lambda x: x[0] if x else np.nan)
    crops["Kc_mid"] = kc_values.apply(lambda x: x[1] if x else np.nan)
    crops["Kc_end"] = kc_values.apply(lambda x: x[2] if x else np.nan)
    crops["Kc_source_note"] = kc_values.apply(
        lambda x: x[3] if x else "No mapped coefficient; add locally validated Kc"
    )

    crops["ET0_season_avg_mm_day"] = crops["season_name"].map(
        {k: v["ET0"] for k, v in season_stats.items()}
    )
    crops["NASA_POWER_rain_season_avg_mm_day"] = crops["season_name"].map(
        {k: v["rain"] for k, v in season_stats.items()}
    )

    # ETc = Kc x ET0 for each crop growth stage.
    for stage in ["initial", "mid", "end"]:
        etc = crops[f"Kc_{stage}"] * crops["ET0_season_avg_mm_day"]
        crops[f"ETc_{stage}_mm_day"] = etc
        crops[f"ETc_{stage}_mm_8day"] = etc * 8
        crops[f"ETc_{stage}_m3_ha_day"] = etc * 10
        crops[f"ETc_{stage}_m3_ha_8day"] = etc * 80

    # Representative daily crop water demand (mid-season).
    crops["water_demand_mm_day"] = crops["ETc_mid_mm_day"]

    # Water demand over 8 days.
    crops["water_demand_mm_8day"] = crops["water_demand_mm_day"] * 8

    # Water demand per hectare.
    crops["water_demand_m3_ha_day"] = crops["water_demand_mm_day"] * 10

    # Water demand per hectare over 8 days.
    crops["water_demand_m3_ha_8day"] = crops["water_demand_mm_day"] * 80

    # Gross rainfall comparison, before runoff, drainage and soil-storage changes.
    crops["NASA_POWER_rain_minus_ETc_mid_mm_day"] = (
        crops["NASA_POWER_rain_season_avg_mm_day"] - crops["ETc_mid_mm_day"]
    )
    crops["provided_rain_6_59_minus_ETc_mid_mm_day"] = (
        USER_MEAN_RAINFALL_MM_DAY - crops["ETc_mid_mm_day"]
    )

    def classify(row):
        if pd.isna(row["ETc_mid_mm_day"]):
            return "Kc missing - needs crop-specific data"
        balance = row["NASA_POWER_rain_minus_ETc_mid_mm_day"]
        if pd.isna(balance):
            return "Weather data missing"
        if balance >= 0:
            return "Gross rainfall >= ETc (before losses)"
        return "Gross rainfall < ETc (possible deficit)"

    crops["Gross_rain_vs_ETc_status"] = crops.apply(classify, axis=1)

    # Keep the user's supplied location indicators as context, not direct water inputs.
    crops["input_precipitable_water"] = USER_PRECIPITABLE_WATER
    crops["input_topsoil_wetness"] = USER_TOPSOIL_WETNESS
    crops["input_mean_temp_C"] = USER_MEAN_TEMP_C
    crops["input_wind_10m_kmh"] = USER_WIND_10M_KMH
    crops["input_mean_rainfall_2001_2024_mm_day"] = USER_MEAN_RAINFALL_MM_DAY

    crops["ETc_method"] = "ETc = Kc x FAO-56 ET0; standard, non-water-stressed crop"
    crops["rain_balance_warning"] = (
        "Gross rainfall minus ETc only; not net irrigation requirement. "
        "Effective rainfall, runoff, drainage, soil storage and crop stage are not modelled."
    )

    crops.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Rows: {len(crops):,}")
    print(f"Mapped crop rows: {crops['Kc_mid'].notna().sum():,}")
    print(f"Unmapped crop rows: {crops['Kc_mid'].isna().sum():,}")
    print("\nSeason averages (2001-2024):")
    for season, stats in season_stats.items():
        print(f"  {season}: ET0={stats['ET0']:.2f} mm/day; rain={stats['rain']:.2f} mm/day")

    preview = [
        "crop_name", "season_name", "Kc_mid", "ET0_season_avg_mm_day",
        "ETc_mid_mm_day", "ETc_mid_mm_8day",
        "NASA_POWER_rain_season_avg_mm_day",
        "NASA_POWER_rain_minus_ETc_mid_mm_day", "Gross_rain_vs_ETc_status",
    ]
    print("\nPreview:")
    print(crops[preview].head(12).to_string(index=False))

if __name__ == "__main__":
    main()
