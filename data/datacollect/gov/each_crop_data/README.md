# Crop-specific weather and warning data

This folder contains BAMIS crop-calendar references and per-crop weather,
disease, pest, and warning records.

## Contents

- `collect.py` is currently a list of BAMIS calendar URLs in comments; it does
  not download data.
- `crops_pdf/` contains crop-calendar PDF files.
- `cops_csv/` contains per-crop CSV folders. The common files are
  `1_weekly_weather.csv`, `2_diseases.csv`, `3_insect_pests.csv`, and
  `4_weather_warnings.csv`.
- `crops_weather_and_warnings.json` is a combined JSON export of crop weather
  stages and warnings.
- `convert_crops.py` copies/converts four CSVs per crop from a separate
  extracted-data directory into `cops_csv/`.
- `create_crop_json.py` converts weekly-weather and warning CSVs into
  per-crop and combined JSON files.
- `get_crop_data.py` provides crop-folder lookup and access to the weather,
  disease, pest, and warning records. It also filters suggested crops against
  numeric weather-warning thresholds when the necessary weather values exist.

## Important

`convert_crops.py`, `create_crop_json.py`, and `get_crop_data.py` contain
absolute paths tied to a previous local setup. Before running or importing
them, update their path constants to the current repository and verify the
expected files. `convert_crops.py` also expects a separate extracted-data
folder that is not part of this repository.

