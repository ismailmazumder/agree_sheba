# NASA and satellite data workflows

This folder groups independent workflows. Live API collection, Earth Engine
processing, and exploratory notebooks have different requirements; no common
runner rebuilds all outputs.

## Folder map

- `crop_water_demand/`
  - `add_crop_water_demand.py` reads `crops_data.csv`, requests daily NASA
    POWER weather for 2001–2024, calculates FAO-56 ET0 and estimated crop ETc,
    and writes `crops_data_with_water_demand.csv`.
  - The script prompts for an ROI latitude and longitude. Its seasonal month
    windows and crop-coefficient proxies are assumptions; gross rainfall
    minus ETc is not net irrigation demand.
- `crop_salt_tola/`
  - `main.py` applies Maas & Hoffman salinity-response parameters to
    `crops_data.csv` and writes `crops_data_with_salt_tolerance.csv`.
  - The script contains a machine-specific absolute input path and writes its
    output relative to the current working directory. Check both paths first.
- `flood/`
  - `calculate_location_flood_signal.py` uses NASA OPERA DSWx-S1 and JRC
    Global Surface Water through Google Earth Engine to add possible
    inundation indicators to location rows. It requires Earth Engine
    authentication; the output is an indicator, not an official flood-risk
    prediction.
  - `location_with_lat_lon.csv` and `location_flood_assessment.csv` are the
    location input and assessment output.
  - `bangladesh_eonet_flood_events*.csv` and matching `.geojson` files are
    flood-event datasets; check their date range and provenance before use.
  - `location.py` is a one-off Nominatim geocoding example. `flood.ipynb` and
    `floodtest.ipynb` are exploratory notebooks.
- `lswi/`
  - `lwsi.ipynb` is an exploratory MODIS/LSWI notebook; `data/` contains
    downloaded raster inputs. These are intermediate remote-sensing files,
    not district-level ground measurements.
- `nasa_power/`
  - `power.py` collects monthly NASA POWER values for each row in
    `data/datasets/location_with_lat_lon.csv` and saves monthly records under
    `location_monthly_2024/`.
  - `location_monthly_2024/meandata.py` summarizes the monthly location data;
    the folder also contains raw, labeled, and sensitive-labeled CSV exports.
- `rain_imperg/`
  - Contains GPM IMERG rainfall data and notebook-based processing. The
    `imerg_monthly/` folder includes NetCDF inputs and derived daily-point,
    rainfall-season, and monsoon-onset files.
- `rain_mean/`
  - `rain_mean.py` collects daily corrected NASA POWER precipitation for
    2001–2024 and appends an overall mean daily rainfall value per location.
    The script writes `rainfall_overall_mean_by_location_2001_2024.csv`;
    `rainfall_by_location_2001_2024.csv` is also present as a stored dataset.
    Verify date coverage before relying on either file.

## Before running

- NASA POWER collection needs a network connection and can take time because
  it queries locations one by one.
- The flood workflow needs Earth Engine access and authentication.
- The water-demand script uses interactive coordinates and simplified season
  windows. The salinity script has a hard-coded input path.
- Notebooks and raster/NetCDF files may require additional Python packages and
  storage. Read each notebook before rerunning cells that fetch or overwrite
  data.

