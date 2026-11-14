# Prepared datasets

This folder holds prepared CSV and JSON data used for comparisons, analysis,
and app content. It is not a database with a guaranteed automated refresh:
files may come from different collection runs and date ranges.

| File | What it contains |
|---|---|
| `crop_economics_suitability(extrainfo).csv` | Combined crop-economics and crop-suitability records, with location, crop, season, and available water-demand and salt-tolerance fields. |
| `crops_data.csv` | Crop names, situations, and seasons. |
| `crops_data_with_salt_tolerance.csv` | Crop-season records with a salinity-tolerance field. |
| `crops_data_with_water_demand.csv` | Crop-season records with FAO-56-based ET0/ETc and gross rainfall-comparison fields. See the limitations in the root README; this is not net irrigation demand. |
| `crops_weather_and_warnings.json` | Crop-level phenological-stage weather and weather-warning records in JSON form. |
| `cumilla_nasa_data.csv` | Date-indexed climate variables for Cumilla, including MERRA-2 and CERES-labelled fields. |
| `district_locations.csv` | District and location-name lookup pairs. |
| `location_flood_assessment.csv` | Location-level possible-inundation indicators and assessment metadata. It is not an official flood-risk prediction. |
| `location_with_lat_lon.csv` | District/upazila names and coordinates used as location inputs by several workflows. |
| `nasa_power_location_means_2024_labeled_sensitive.csv` | 2024 location summaries with NASA POWER-labelled variables and labels. The filename flags sensitivity: review privacy and sharing permissions before use or publication. |
| `season.csv` | Rainfall/season summary fields, including monthly totals and wet-day statistics. |
| `upazila_salinity_decisions.csv` | Upazila names with a `decision` field; check the producing method before interpreting the decisions. |

## Notes

- Similar filenames do not guarantee identical content. The root-level
  `crops_data_with_salt_tolerance.csv` is a separate, non-identical copy of the
  file in this folder. Compare provenance and timestamps before choosing one.
- File names alone do not establish data provenance. Consult the root README
  and the source workflow for dataset identifiers, URLs, date ranges, units,
  and processing assumptions.
- Keep original inputs separate from derived outputs when updating the data.

