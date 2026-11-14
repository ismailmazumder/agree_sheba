# Government and crop-calendar data

This folder contains Bangladesh agricultural data collection and crop-specific
weather/calendar files.

## Files and folders

- `mighty_crop_data.py` calls the Bangladesh Crop Zoning API. It writes
  location, suitability, economics, and merged CSV files beside the script.
  The generated files include `district_code.csv`, `district_locations.csv`,
  `ceupazilas.csv`, `crop_suitability.csv`, `crop_economics.csv`,
  `crop_economics_suitability.csv`, and `crop_suitability_ceupazilas.csv`.
  The API must be reachable; this is a live collector, not an offline build.
- `district_locations.csv` is a district/location lookup already present in
  this folder.
- [`each_crop_data/README.md`](each_crop_data/README.md) documents the
  crop-calendar references, per-crop CSVs, JSON files, and related scripts.
- `salty.csv` and `salty.pdf` are salinity-related files; inspect their
  provenance and contents before using them as data inputs.
- `salty.py` is currently empty and does not implement a processing workflow.

## Path portability

The scripts under `each_crop_data/` include absolute paths from a different
local checkout or workstation. They will not reliably run from a fresh clone
until those paths are changed and the expected input folders are available.

