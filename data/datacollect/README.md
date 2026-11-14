# Data collection and processing

This folder contains scripts, notebooks, and supporting files from separate
government-data and NASA/satellite workflows. The directory is a collection of
work products, not a single ordered pipeline.

## Workflow groups

- [`gov/README.md`](gov/README.md) — Bangladesh Crop Zoning and BAMIS-related
  crop information, including crop-specific CSV/JSON processing.
- [`nasa/README.md`](nasa/README.md) — NASA POWER, rainfall, water-demand,
  salinity, and flood/satellite work.

## Running scripts safely

1. Read the script and its folder guide to confirm inputs, outputs, and date
   ranges.
2. Check for absolute paths and update them for your machine. Some older
   government-data scripts still point to folders outside this repository.
3. Expect network access for API collectors. The Earth Engine workflow also
   requires a configured Google Earth Engine account.
4. Preserve source files and review generated CSVs before replacing anything
   in [`../datasets/`](../datasets/README.md).

No project-wide offline cache, fixture fallback, or one-command data rebuild
is currently documented or implemented.

