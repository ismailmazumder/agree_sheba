# Data folder guide

This directory contains prepared datasets and the scripts/notebooks used to
collect or transform some of them. The scripts are separate workflows; there
is no single command that rebuilds every file in `datasets/`.

## Folders

- [`datasets/`](datasets/README.md) contains the CSV and JSON files used as
  prepared inputs or analysis outputs. See its guide for a file-by-file index.
- [`datacollect/`](datacollect/README.md) contains data collection and
  processing code, notebooks, intermediate exports, and source files.

## Before running a workflow

- Read the guide in the specific workflow folder first. Some scripts make live
  API requests, need Google Earth Engine authentication, or prompt for a
  location.
- Some older government-data scripts contain absolute paths from another
  computer. Update and verify those paths before running them.
- Treat processed indicators as estimates with the limitations described in
  the root [project README](../README.md); they are not field measurements.
- Check the source, date range, units, processing steps, and redistribution
  terms before reusing or publishing a dataset. The file named
  `nasa_power_location_means_2024_labeled_sensitive.csv` needs a privacy review
  before sharing.

