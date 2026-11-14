# AgriSheba documentation

AgriSheba is a research prototype for agricultural decision support in Bangladesh. It combines crop suitability data, climate and rainfall information, crop-water demand estimates, and salinity-related agronomic indicators to help compare crops and seasonal planning options.

## Project goal

The project explores how environmental, agronomic, and economic information can be combined to support crop selection and rotation planning. The focus is on location-aware recommendations that can be traced back to source data and scientific assumptions.

## Main components

- Web interface: `index.html` and related HTML demos in the project root
- Data collection scripts: `data/datacollect/`
- NASA and climate-related processing: `data/nasa/`
- Processed datasets: `data/datasets/`
- Project summary: `README.md`

## Quick start

To view the interface locally:

```bash
cd "E:\Users\ismail\Desktop\agree_sheba"
python -m http.server 8000
```

Then open:

- http://localhost:8000/
- or http://localhost:8000/index.html

If you prefer to open the file directly in a browser, you can also double-click `index.html`. The local web server is recommended because some pages may assume a static file context and behave more reliably via HTTP.

## Repository layout

### `data/datacollect/`

Contains scripts for collecting and transforming source agricultural data. This includes government crop-zoning data and crop-specific metadata.

Examples:

- `data/datacollect/gov/mighty_crop_data.py`
- `data/datacollect/gov/each_crop_data/`

### `data/nasa/`

Contains scripts and processed outputs related to climate, rainfall, flood, vegetation, and remote-sensing indicators.

Examples:

- `data/nasa/rain_mean/`
- `data/nasa/flood/`
- `data/nasa/lswi/`
- `data/nasa/crop_water_demand/`

### `data/datasets/`

Stores cleaned and derived datasets used by the project, including CSV and JSON data files that feed analysis and the web interface.

## Data workflow

1. Collect raw or semi-structured data from government or remote-sensing sources.
2. Process and normalize it into crop, climate, and location datasets.
3. Derive agronomic indicators such as water demand, salinity tolerance, and rainfall measures.
4. Use those indicators to assess crop suitability and seasonal suitability.

## Notes for contributors

- Keep data provenance and conversion steps documented when adding new sources.
- Prefer reproducible scripts over manual edits whenever possible.
- When new outputs are added, place them in the appropriate subfolder under `data/` rather than mixing raw and processed files.
- If the project interface is updated, keep the HTML and generated data inputs consistent.

## Useful references

- `README.md` for the high-level product description
- `data/README.md` for dataset-facing notes
- `data/datacollect/README.md` and related subfolder READMEs for collection details

## Suggested next steps

- Add a small project status page or landing page
- Document the expected input/output schema for each dataset
- Add a reproducible command or script for generating the final combined crop dataset
- Standardize naming across the duplicate `index*.html` demo files
