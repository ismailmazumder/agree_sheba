"""Assess possible inundation signals at the supplied locations with NASA OPERA DSWx-S1.

Authenticate Earth Engine before running, for example with ``earthengine authenticate``.
The result is an observational indicator, not an official flood-risk prediction.
"""

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import ee


START_DATE = "2022-09-01"
DEFAULT_PROJECT = "nasaproject-513305"
BANGLADESH_BOUNDS = (88.0, 20.0, 93.0, 27.0)
PERMANENT_WATER_THRESHOLD = 90
MINIMUM_WATER_DETECTIONS = 2
DEFAULT_BATCH_SIZE = 100

RESULT_FIELDS = [
    "assessment_start_date",
    "assessment_end_date",
    "permanent_water_occurrence_pct",
    "water_detections",
    "valid_observations",
    "possible_inundation_frequency_pct",
    "possible_inundation_status",
    "flood_status",
]


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Add a NASA OPERA DSWx-S1 inundation signal assessment to each input location."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=script_dir / "location_with_lat_lon.csv",
        help="Input CSV containing latitude and longitude columns.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "location_flood_assessment.csv",
        help="Path for the results CSV.",
    )
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help="Google Cloud project enabled for Earth Engine.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of unique locations queried per Earth Engine request.",
    )
    return parser.parse_args()


def read_locations(path: Path) -> tuple[list[dict[str, str]], list[str], dict[tuple[float, float], int]]:
    with path.open(encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames is None:
            raise ValueError(f"{path} does not contain a CSV header.")
        fieldnames = list(reader.fieldnames)
        missing_columns = {"latitude", "longitude"}.difference(fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{path} is missing required column(s): {missing}")

        rows = list(reader)

    coordinates: dict[tuple[float, float], int] = {}
    for row_number, row in enumerate(rows, start=2):
        try:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid latitude or longitude on CSV row {row_number}."
            ) from error

        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError(
                f"Latitude or longitude is out of range on CSV row {row_number}."
            )
        coordinates.setdefault((latitude, longitude), len(coordinates))

    return rows, fieldnames, coordinates


def is_in_analysis_area(latitude: float, longitude: float) -> bool:
    min_longitude, min_latitude, max_longitude, max_latitude = BANGLADESH_BOUNDS
    return (
        min_latitude <= latitude <= max_latitude
        and min_longitude <= longitude <= max_longitude
    )


def make_observation(image: ee.Image) -> ee.Image:
    water = image.select("BWTR_Binary_water")
    valid = water.lt(250)
    water_observation = (
        water.eq(1).updateMask(valid).unmask(0).rename("water_detections")
    )
    valid_observation = valid.unmask(0).rename("valid_observations")
    return (
        water_observation.addBands(valid_observation)
        .copyProperties(image, ["system:time_start"])
    )


def get_location_values(
    coordinates: list[tuple[float, float]],
    water_count: ee.Image,
    valid_count: ee.Image,
    permanent_water: ee.Image,
    batch_size: int,
) -> dict[int, dict[str, Any]]:
    image = ee.Image.cat(
        [
            permanent_water.rename("permanent_water_occurrence_pct"),
            water_count.rename("water_detections"),
            valid_count.rename("valid_observations"),
        ]
    )
    results: dict[int, dict[str, Any]] = {}

    for start in range(0, len(coordinates), batch_size):
        batch = coordinates[start : start + batch_size]
        points = ee.FeatureCollection(
            [
                ee.Feature(
                    ee.Geometry.Point([longitude, latitude]),
                    {"point_id": start + offset},
                )
                for offset, (latitude, longitude) in enumerate(batch)
            ]
        )
        sampled = image.reduceRegions(
            collection=points,
            reducer=ee.Reducer.first(),
            scale=30,
            tileScale=4,
        ).getInfo()

        for feature in sampled["features"]:
            properties = feature["properties"]
            point_id = int(properties["point_id"])
            results[point_id] = properties

    if len(results) != len(coordinates):
        raise RuntimeError(
            f"Earth Engine returned {len(results)} of {len(coordinates)} sampled locations."
        )
    return results


def assess_location(values: dict[str, Any]) -> dict[str, Any]:
    occurrence = values.get("permanent_water_occurrence_pct")
    detections = values.get("water_detections")
    observations = values.get("valid_observations")
    frequency = ""

    if detections is not None and observations is not None and observations > 0:
        frequency = round(100 * detections / observations, 2)

    if observations is None or detections is None or observations < 2:
        status = "INSUFFICIENT_DATA"
    elif occurrence is not None and occurrence >= PERMANENT_WATER_THRESHOLD:
        status = "NOT_CLASSIFIED_PERMANENT_WATER"
    elif occurrence is None and detections >= MINIMUM_WATER_DETECTIONS:
        status = "POSSIBLE_SIGNAL_PERMANENT_WATER_UNKNOWN"
    elif occurrence is None:
        status = "NO_REPEATED_SIGNAL_PERMANENT_WATER_UNKNOWN"
    elif detections >= MINIMUM_WATER_DETECTIONS:
        status = "POSSIBLE_INUNDATION_SIGNAL"
    else:
        status = "NO_REPEATED_SIGNAL"

    flood_status = (
        "floody"
        if status
        in {
            "POSSIBLE_INUNDATION_SIGNAL",
            "POSSIBLE_SIGNAL_PERMANENT_WATER_UNKNOWN",
        }
        else "not floody"
    )

    return {
        "permanent_water_occurrence_pct": occurrence if occurrence is not None else "",
        "water_detections": detections if detections is not None else "",
        "valid_observations": observations if observations is not None else "",
        "possible_inundation_frequency_pct": frequency,
        "possible_inundation_status": status,
        "flood_status": flood_status,
    }


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1.")

    rows, input_fields, coordinate_ids = read_locations(args.input)
    today = date.today()
    end_date = (today + timedelta(days=1)).isoformat()
    start_date = START_DATE
    output_fields = input_fields + [
        field for field in RESULT_FIELDS if field not in input_fields
    ]

    inside_coordinates = [
        coordinate
        for coordinate in coordinate_ids
        if is_in_analysis_area(*coordinate)
    ]
    assessments: dict[tuple[float, float], dict[str, Any]] = {}

    if inside_coordinates:
        ee.Initialize(project=args.project)
        analysis_area = ee.Geometry.Rectangle(list(BANGLADESH_BOUNDS))
        collection = (
            ee.ImageCollection("OPERA/DSWX/L3_V1/S1")
            .filterBounds(analysis_area)
            .filterDate(start_date, end_date)
            .select("BWTR_Binary_water")
        )
        if collection.size().getInfo() == 0:
            raise RuntimeError(
                "No OPERA DSWx-S1 observations were found for the requested period."
            )

        summary = collection.map(make_observation).sum().clip(analysis_area)
        water_count = summary.select("water_detections")
        valid_count = summary.select("valid_observations")
        permanent_water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select(
            "occurrence"
        )

        sampled = get_location_values(
            inside_coordinates,
            water_count,
            valid_count,
            permanent_water,
            args.batch_size,
        )
        for point_id, coordinate in enumerate(inside_coordinates):
            assessments[coordinate] = assess_location(sampled[point_id])

    with args.output.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=output_fields)
        writer.writeheader()
        for row in rows:
            coordinate = (float(row["latitude"]), float(row["longitude"]))
            result = assessments.get(coordinate)
            if result is None:
                result = {
                    "permanent_water_occurrence_pct": "",
                    "water_detections": "",
                    "valid_observations": "",
                    "possible_inundation_frequency_pct": "",
                    "possible_inundation_status": "OUTSIDE_ANALYSIS_AREA",
                    "flood_status": "not floody",
                }
            writer.writerow(
                {
                    **row,
                    **result,
                    "assessment_start_date": start_date,
                    "assessment_end_date": today.isoformat(),
                }
            )

    print(
        f"Wrote {len(rows)} locations to {args.output} "
        f"({len(inside_coordinates)} unique coordinates queried)."
    )


if __name__ == "__main__":
    main()
