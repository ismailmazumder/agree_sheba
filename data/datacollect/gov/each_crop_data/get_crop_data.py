import os
import re
from typing import Union, Dict, Any, Mapping, Iterable, List
import pandas as pd

# Base directory where cops_csv folders are stored
BASE_DIR = r"E:\Users\ismail\Desktop\collector_sheba\data\datacollect\gov\each_crop_data\cops_csv"

# Mapping of file keys to actual file names
DATA_FILES = {
    "weather": "1_weekly_weather.csv",
    "diseases": "2_diseases.csv",
    "pests": "3_insect_pests.csv",
    "warnings": "4_weather_warnings.csv"
}

WEATHER_VALUE_ALIASES = {
    "rainfall": ("rainfallmm",),
    "maxtemp": ("maxtempc", "maxtemperature", "maximumtemperature"),
    "mintemp": ("mintempc", "mintemperature", "minimumtemperature"),
    "relativehumiditymax": ("rhmaxpct", "maximumhumidity"),
    "relativehumiditymin": ("rhminpct", "minimumhumidity"),
    "relativehumiditymean": ("rhmeanpct", "meanhumidity"),
    "windspeed": ("windspeedkmh",),
}


def _normalize_name(name: str) -> str:
    """Normalize names for case-insensitive and flexible matching."""
    return re.sub(r"[^a-zA-Z0-9]", "", str(name).lower())


def _get_weather_value(parameter: str, weather_values: Mapping[str, Any]):
    normalized_values = {
        _normalize_name(key): value for key, value in weather_values.items()
    }
    normalized_parameter = _normalize_name(parameter)
    candidates = (
        normalized_parameter,
        *WEATHER_VALUE_ALIASES.get(normalized_parameter, ()),
    )
    for candidate in candidates:
        value = normalized_values.get(candidate)
        if value is not None and not pd.isna(value):
            try:
                return float(value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Weather value for '{parameter}' must be numeric, got {value!r}"
                ) from error
    return None


def _threshold_value(warning: Mapping[str, Any], field: str):
    value = warning.get(field)
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Weather warning {field!r} must be numeric, got {value!r}"
        ) from error


def filter_crop_suggestions(
    suggestions: Iterable[Union[str, Mapping[str, Any]]],
    weather_values: Mapping[str, Any],
) -> List[Union[str, Mapping[str, Any]]]:
    """Remove suggested crops whose matched weather exceeds a warning threshold.

    Weather values are keyed by warning parameter (for example ``rainfall``,
    ``max_temp``, or ``wind_speed``). Values with equivalent common names such
    as ``rainfall_mm`` and ``wind_speed_kmh`` are also recognized. An upper
    threshold is the maximum acceptable value; a lower threshold is the
    minimum acceptable value. Equality is accepted.

    Qualitative warnings without numeric thresholds, and thresholds for which
    no weather value was supplied, are not evaluated. Suggestion entries may
    be crop-name strings or mappings containing a ``crop`` field.
    """
    if not isinstance(weather_values, Mapping):
        raise TypeError("weather_values must be a mapping of parameters to values")

    filtered = []
    for suggestion in suggestions:
        if isinstance(suggestion, str):
            crop_name = suggestion
        elif isinstance(suggestion, Mapping):
            crop_name = suggestion.get("crop")
            if not isinstance(crop_name, str) or not crop_name.strip():
                raise ValueError("Suggestion mappings must contain a non-empty 'crop' field")
        else:
            raise TypeError("Suggestions must be crop-name strings or mappings")

        warnings = get_crop_data(crop_name, "warnings", as_dict=True)
        violates_warning = False
        for warning in warnings:
            parameter = warning.get("parameter")
            if not parameter:
                continue
            observed = _get_weather_value(parameter, weather_values)
            if observed is None:
                continue

            upper = _threshold_value(warning, "upper_threshold")
            lower = _threshold_value(warning, "lower_threshold")
            if upper is not None and observed > upper:
                violates_warning = True
                break
            if lower is not None and observed < lower:
                violates_warning = True
                break

        if not violates_warning:
            filtered.append(suggestion)
    return filtered


def _find_crop_folder(crop_name: str, base_dir: str = BASE_DIR) -> str:
    """Find matching folder name in cops_csv directory."""
    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"Base directory does not exist: {base_dir}")

    folders = os.listdir(base_dir)
    norm_target = _normalize_name(crop_name)

    # 1. Exact match
    for folder in folders:
        if folder.lower() == crop_name.lower():
            return folder

    # 2. Normalized match (ignores spaces, punctuation, case)
    for folder in folders:
        if _normalize_name(folder) == norm_target:
            return folder

    # 3. Substring / partial match
    for folder in folders:
        if norm_target in _normalize_name(folder):
            return folder

    available = ", ".join(sorted(folders))
    raise ValueError(f"Crop '{crop_name}' not found. Available crops:\n{available}")

def get_crop_data(
    crop_name: str, 
    crop_data_userwant: str = "all", 
    as_dict: bool = False
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, Any]]:
    """
    Access crop related data.

    Parameters:
    -----------
    crop_name : str
        Name of the crop (e.g., 'Banana', 'T. Aman dhan', 'Bottle Gourd', 'rice').
    crop_data_userwant : str, default 'all'
        Specific dataset to return:
        - 'all': returns all 4 datasets in a dictionary
        - 'weather' / 'weekly': returns 1_weekly_weather.csv
        - 'diseases' / 'disease': returns 2_diseases.csv
        - 'pests' / 'insect_pests': returns 3_insect_pests.csv
        - 'warnings' / 'weather_warnings': returns 4_weather_warnings.csv
    as_dict : bool, default False
        If True, returns data as Python dict/list of records instead of pandas DataFrames.

    Returns:
    --------
    pd.DataFrame or Dict[str, pd.DataFrame] or Dict[str, Any]
        Requested crop data.
    """
    folder = _find_crop_folder(crop_name)
    crop_dir = os.path.join(BASE_DIR, folder)

    # Normalize user request
    req = str(crop_data_userwant).lower().strip()

    # Determine which file(s) to load
    target_key = None
    if req in ["all", "", "none", "*"]:
        target_key = "all"
    elif any(k in req for k in ["weather", "weekly", "week", "1"]):
        target_key = "weather"
    elif any(k in req for k in ["disease", "diseases", "2"]):
        target_key = "diseases"
    elif any(k in req for k in ["pest", "insect", "bug", "3"]):
        target_key = "pests"
    elif any(k in req for k in ["warning", "alert", "4"]):
        target_key = "warnings"
    else:
        raise ValueError(
            f"Invalid crop_data_userwant: '{crop_data_userwant}'. "
            f"Choose from: 'all', 'weather', 'diseases', 'pests', 'warnings'."
        )

    # Load requested data
    if target_key == "all":
        result = {}
        for key, fname in DATA_FILES.items():
            fpath = os.path.join(crop_dir, fname)
            if os.path.exists(fpath):
                df = pd.read_csv(fpath)
                result[key] = df.to_dict(orient="records") if as_dict else df
            else:
                result[key] = [] if as_dict else pd.DataFrame()
        return result
    else:
        fname = DATA_FILES[target_key]
        fpath = os.path.join(crop_dir, fname)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"File not found: {fpath}")
        df = pd.read_csv(fpath)
        return df.to_dict(orient="records") if as_dict else df


# Example usage when run directly
if __name__ == "__main__":
    print("=== TEST 1: Get ALL data for Banana ===")
    all_banana = get_crop_data("Banana", "all")
    for section, df in all_banana.items():
        print(f"[{section.upper()}] Rows: {len(df)}, Columns: {list(df.columns[:4])}...")

    print("\n=== TEST 2: Get only weather for 'bottle gourd' (case-insensitive) ===")
    weather_bg = get_crop_data("bottle gourd", "weather")
    print(weather_bg[["crop", "std_week", "rainfall_mm", "mean_temp_c", "phenological_stage"]].head())

    print("\n=== TEST 3: Get diseases for 'T. Aman' as Python dict ===")
    diseases = get_crop_data("T. Aman", "diseases", as_dict=True)
    print(diseases)
