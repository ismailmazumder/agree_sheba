# Bangladesh Crop & Rotation Decision Support

A local, offline-capable decision-support web app that compares crop sequences using the project’s cached crop-zoning, seasonal, salinity, and satellite flood data. It is designed to help a farmer and a local agriculture expert discuss options; it is not an authoritative prescription.

## Run it

Requires Python 3.10 or later. The application uses only the Python standard library and the CSV files already in `data/datasets/`.

```powershell
python app.py
```

Open <http://127.0.0.1:8000>. To choose a different local port, set `CROP_APP_PORT` before starting. The server binds to loopback by default. It makes no external API calls, so it remains usable without an internet connection.

Run the test suite:

```powershell
python -m unittest discover -s tests -v
```

## What the system does

1. Select an upazila, season, current/recent crops, and priorities.
2. Retrieve crop-season entries for that upazila from the locally cached crop-zoning/economics file.
3. Keep the farmer’s existing crop sequence in the comparison and form alternatives from locally listed crops in the selected season and the next season label.
4. Rank up to eight crops recorded for that upazila and season using local crop-season evidence, situation/adaptation labels, and available local economic percentiles. The list is limited to observed local crop entries; crops are never fabricated to fill eight slots.
5. Compare the existing plan with locally listed rotation alternatives using the explainable score below, not an ML prediction.
6. Optionally enter locally verified crop durations, planting dates, and a next-crop planting window. The calendar check calculates harvest dates where the user supplied enough information and flags conflicts. Missing durations or dates remain unknown.
7. Show evidence, reported economic values, confidence coverage, assumptions, and data gaps in English and Bangla.

The next-season label order (`Rabi → Kharif-1 → Kharif-2 → Rabi`) is a planning assumption, not a crop-specific calendar. The local crop table’s season entry supports whether a crop is listed in a season; the supplied files do **not** contain verified planting windows or crop durations.

### Score and recommendation logic

The 0–100 score is an option-ranking aid, not a probability, yield, profitability, or flood-risk estimate.

- For the top-eight crop list, each economic field is ranked independently by ascending midrank percentile among crops in the same upazila and season. Ties receive their average rank. The ranks for available `gm_tk_dec`, `bcr_vc`, and `bcr_tc` values are averaged to make a local economic-relative component. All three are interpreted in the higher-is-better direction, and no arbitrary outlier cutoff is applied. Missing metrics are omitted rather than imputed. The app preserves and displays the reported raw values and percentile ranks.
- The rotation-plan score starts with local crop-season evidence 35%, diversity/legume-name indicator 15%, calendar compatibility 20%, adaptation evidence 10%, and local economic-relative rank 20%. Selected priorities reweight the score; unavailable components are omitted and the remaining component weights are normalized over available evidence. Lower-water priority has no crop-demand data and is therefore unscored. Soil priority uses only an explicit crop-name legume heuristic, not a measured soil effect. Flood priority uses a historical point signal and source submergence-tolerance label; heat priority has no local crop-specific threshold.
- Crop-season evidence is the fraction of crops in a plan that are listed for the relevant upazila and season.
- Rotation diversity receives a rule-based indicator for distinct crop names and a short, documented legume-name list. This is not a measured soil-health response; verify crop identity and local suitability.
- Calendar results are `CHECKED`, `PARTIAL`, `CONFLICT`, or `UNKNOWN`. A `CHECKED` result means the available season labels and farmer-supplied dates pass implemented checks; it does not certify local agronomic timing.
- The displayed weighted-evidence coverage is the share of selected score components with data. The qualitative confidence label is capped at Moderate and is Low if coverage is below 80%, the date checks are incomplete, or a planned crop lacks a local crop-season record. It is not statistically calibrated, and every result remains unvalidated.

Missing evidence is never filled with a fabricated value. A high score does not override a missing soil test, water requirement, local weather record, or expert review. `not floody` is not proof that a farm cannot flood.

## Dataset inventory

All seven files under `data/datasets/` were inspected. Variable names and missing-value counts below reflect the local snapshots; unknown units or provenance are explicitly marked unknown rather than inferred as facts.

| File | Variables and units | Period, coverage, resolution | Missing values and source |
|---|---|---|---|
| `crop_economics_suitability(extrainfo).csv` | Place/codes; English/Bangla crop and season; situation/adaptation labels; `gm_tk_dec` (Gross Margin, Rs./Percentage), `bcr_vc` (Income Expense Ratio, Variable Costs), `bcr_tc` (Income Expense Ratio, Total Expenses); `vs/s/ms/ls/ns`. Economic definitions are clarified by the user; source period and detailed calculations are not documented. `vs` etc. are undefined. | 45,756 rows; 64 districts and 480 upazila codes; upazila level; period not stated. | Missing: `gm_tk_dec` 1,275; `bcr_vc` 1,416; `bcr_tc` 8; crop-season/variety/situation and `vs/s/ms/ls/ns` each 2,133. Collector in `data/datacollect/gov/mighty_crop_data.py` uses the Bangladesh crop-zoning API (`api1.cropzoning.gov.bd`). Snapshot does not state a data license or observation year. |
| `crops_data.csv` | Crop name, situation, season in English and Bangla; categorical values, no units. | 45,756 repeated rows; 81 crop names; not spatial; period not stated. UTF-16 encoded. | No blank fields detected. Apparently a repeated lookup derived from crop-economics/suitability data; no independent source/license recorded. Repetitions are not independent observations. |
| `cumilla_nasa_data.csv` | Daily T2M (°C), QV2M (g/kg), PS (kPa), GWETTOP (fraction), CERES all-sky surface UV index (header gives W m⁻² × 40; verify product unit). | 2025-01-01–2025-12-31, 365 daily rows; one point inferred to be in Cumilla from the file name; exact coordinates and grid resolution not supplied. | No blank fields detected. Headers identify NASA MERRA-2/CERES; exact source URL and extraction coordinates are absent. One year/point is not a climate normal and is not used to rank crops. |
| `location_flood_assessment.csv` | Latitude/longitude, assessment dates, OPERA water detections and valid observations (counts), possible inundation frequency (%), JRC permanent-water occurrence (%), status. | 2022-09-01–2026-11-07; 45,756 rows with about 478 distinct coordinate pairs; point samples at 30 m nominal OPERA scale, not farm boundaries. | `permanent_water_occurrence_pct` missing in 37,749 rows; other fields populated. Local export generated by `data/datacollect/nasa/flood/calculate_location_flood_signal.py` from NASA OPERA DSWx-S1 and JRC Global Surface Water. This historical satellite signal is not a forecast. |
| `location_with_lat_lon.csv` | District/thana/upazila names and latitude/longitude (decimal degrees). | 45,756 repeated rows; 64 districts, 467 thana names, about 478 unique points; point meaning and spatial accuracy not documented. | No blank fields detected. Original coordinate provenance/license is not recorded. |
| `season.csv` | Monthly mean/median rainfall (mm/month), mean daily precipitation (mm/day), rainy days (days/month), wet-day frequency (%); wet day is at least 1 mm/day. | 12 monthly rows, reported period 2024–2025 with one complete year; one point at 23.8103°N, 90.4125°E; IMERG grid about 0.1°. | No blank fields detected. Summarized from NASA GPM IMERG by `data/datacollect/nasa/rain_imperg/imerg_monthly/summary.ipynb`. Too short and too spatially limited for farm-specific crop ranking; not used in score. |
| `upazila_salinity_decisions.csv` | District, upazila, `decision` category; no concentration or unit. | 102 upazilas in 18 districts; upazila labels; period and measurement resolution not stated. | No blank fields detected; all 102 entries are `Saline`. Source, method, measurement date, and license are absent. A missing upazila entry means unknown, not non-saline. |

### Supplementary local files outside `data/datasets/`

- `data/datacollect/gov/salty.csv` has 102 records with total/cultivated/saline land areas and `s1_ha`–`s5_ha` fields (hectares indicated by field names). The application displays the matched upazila’s reported saline area but does not infer a farm’s soil salinity or score area share as severity. The accompanying `salty.pdf` is present, but the CSV/PDF do not identify a publisher, measurement date, category definitions, or reuse license.
- `data/datacollect/nasa/lswi/data/` contains 39 complete Bangladesh MOD09A1.061 composites with B02, B06, and QC rasters, dated 2025-12-27–2026-10-24. The 500 m product has approximately 463 m pixels and 8-day composites. LSWI is calculated as `(B02-B06)/(B02+B06)` with the notebook’s QA filter; at an upazila’s matched reference point the app displays the mean/latest value and valid-date count. It is context only, not a crop-specific score: a pixel may mix crops, water, and other land cover, and the notebook’s LSWI classes are explicitly indicative. These rasters and the QA logic are documented in `data/datacollect/nasa/lswi/lwsi.ipynb`. `data/datacollect/nasa/lswi/egypt_data/` holds 44 additional Egypt-region TIFF files and is not used for Bangladesh recommendations.
- `salty.csv` and MODIS rasters are loaded only when present. MODIS sampling uses the existing `rasterio` package if installed; the app still runs offline without it and reports that vegetation sampling is unavailable.

### Data and licensing limitations

- The crop-zoning API snapshot has no license notice in the supplied files. Confirm reuse and redistribution rights with its publisher.
- The salinity table and location coordinates have no recorded source/license. Do not treat them as surveyed or authoritative measurements.
- NASA/JRC datasets have their own attribution and use terms; consult the upstream product documentation before redistributing source data. The local project does not include complete product metadata or license files.
- The MOD09A1 rasters are NASA MODIS products, but the local files do not contain a complete download/attribution manifest or license text. Verify current NASA product terms before redistribution.
- The filenames and headers alone do not provide crop-calendar dates, crop duration, soil tests (texture/pH), irrigation demand by crop, location-specific heat normals, or farm outcome/yield labels.
- Source-reported economic values have missing data and extreme values (including ratios over 1,000). The system does not silently trim or cap them: percentile ranking limits the influence of magnitudes while retaining their ordering. Ranks are descriptive comparisons, not validated estimates of a farm's actual costs, returns, yield, or profit. Confirm source definitions, units, and reporting period with local experts.

## Model, validation, and limitations

No reliable historical crop-yield/outcome labels are available, so this application does not train a yield model or invent targets. It uses deterministic, inspectable rules instead. No clustering model is added: the climate files cover only isolated points/short periods and cannot support meaningful, representative farm/season clusters. The tested fallback is the rule-based score, with each unsupported dimension shown as a gap.

Recommendations are for discussion with the farmer and a Bangladesh Department of Agricultural Extension (DAE) officer or qualified agronomist. Verify variety, soil, water availability, crop durations, planting windows, market conditions, and flood/salinity exposure locally before making a decision.
