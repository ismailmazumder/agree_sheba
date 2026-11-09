import argparse
import csv
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]
LOCATIONS_CSV = PROJECT_ROOT / "data" / "datasets" / "location_with_lat_lon.csv"
OUTPUT_CSV = SCRIPT_DIR / "rainfall_overall_mean_by_location_2001_2024.csv"

API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETER = "PRECTOTCORR"
COMMUNITY = "AG"
START_YEAR = 2001
END_YEAR = 2024
FILL_VALUE = -999.0
REQUEST_INTERVAL_SECONDS = 1.1
MAX_RETRIES = 5
REQUEST_TIMEOUT_SECONDS = 120

LOCATION_FIELDS = (
    "district_name",
    "thana_name",
    "upz_name_bn",
    "latitude",
    "longitude",
)
OUTPUT_FIELDS = LOCATION_FIELDS + ("overall_mean_daily_rain_mm",)


def location_key(location):
    return (
        location["district_name"],
        location["thana_name"],
        location["latitude"],
        location["longitude"],
    )


def load_locations():
    required_fields = set(LOCATION_FIELDS)
    with LOCATIONS_CSV.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_fields = required_fields - set(reader.fieldnames or ())
        if missing_fields:
            raise ValueError(
                f"{LOCATIONS_CSV} is missing columns: {', '.join(sorted(missing_fields))}"
            )

        locations = []
        seen = set()
        for line_number, row in enumerate(reader, start=2):
            try:
                latitude = float(row["latitude"])
                longitude = float(row["longitude"])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid coordinates on line {line_number} of {LOCATIONS_CSV}"
                ) from error
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError(
                    f"Coordinates out of range on line {line_number} of {LOCATIONS_CSV}"
                )

            location = {
                field: row[field].strip()
                for field in LOCATION_FIELDS
            }
            if not location["district_name"] or not location["thana_name"]:
                raise ValueError(
                    f"Missing district or upazila name on line {line_number} "
                    f"of {LOCATIONS_CSV}"
                )
            key = location_key(location)
            if key not in seen:
                locations.append(location)
                seen.add(key)
    return locations


def fetch_rainfall(location):
    query = urlencode(
        {
            "parameters": PARAMETER,
            "community": COMMUNITY,
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "start": f"{START_YEAR}0101",
            "end": f"{END_YEAR}1231",
            "format": "JSON",
        }
    )
    request = Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "BangladeshLocationRainfallCollector/1.0"},
    )

    for attempt in range(MAX_RETRIES):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.load(response)
            break
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == MAX_RETRIES - 1:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = (
                int(retry_after)
                if retry_after and retry_after.isdigit()
                else 2**attempt
            )
            print(f"NASA POWER returned HTTP {error.code}; retrying in {delay}s.")
            time.sleep(delay)
        except URLError:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = 2**attempt
            print(f"NASA POWER request failed; retrying in {delay}s.")
            time.sleep(delay)
    else:
        raise RuntimeError("Unable to fetch NASA POWER rainfall after retries.")

    header = payload.get("header", {})
    status = header.get("status")
    if status is not None and status != "SUCCESS":
        raise ValueError(f"NASA POWER request failed: {header.get('messages', header)}")
    rainfall = payload.get("properties", {}).get("parameter", {}).get(PARAMETER)
    if not isinstance(rainfall, dict) or not rainfall:
        raise ValueError(f"NASA POWER response has no {PARAMETER} rainfall series.")
    return rainfall


def summarize_rainfall(location, rainfall):
    overall_sum = 0.0
    overall_count = 0

    for date_string, raw_value in rainfall.items():
        try:
            value = float(raw_value)
            year = int(date_string[:4])
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid rainfall observation {date_string}: {raw_value!r}"
            ) from error
        if value == FILL_VALUE or value < 0:
            continue
        if START_YEAR <= year <= END_YEAR:
            overall_sum += value
            overall_count += 1

    if overall_count == 0:
        raise ValueError(
            f"No valid rainfall observations for {location['district_name']} / "
            f"{location['thana_name']}"
        )

    return {
        **location,
        "overall_mean_daily_rain_mm": f"{overall_sum / overall_count:.6f}",
    }


def load_completed_locations():
    if not OUTPUT_CSV.exists():
        return set()
    with OUTPUT_CSV.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != list(OUTPUT_FIELDS):
            raise ValueError(f"Unexpected columns in existing file: {OUTPUT_CSV}")
        completed = set()
        for row in reader:
            key = location_key(row)
            if key in completed:
                raise ValueError(f"Duplicate location record in {OUTPUT_CSV}: {key}")
            completed.add(key)
    return completed


def write_rows(rows, append):
    mode = "a" if append else "w"
    encoding = "utf-8" if append else "utf-8-sig"
    with OUTPUT_CSV.open(mode, encoding=encoding, newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        if not append:
            writer.writeheader()
        writer.writerows(rows)
        csv_file.flush()
        os.fsync(csv_file.fileno())


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect yearly NASA POWER rainfall statistics for each location."
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Collect at most this many pending locations (useful for testing).",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero.")
    return args


def main():
    args = parse_args()
    locations = load_locations()
    completed = load_completed_locations()
    pending = [location for location in locations if location_key(location) not in completed]
    if args.limit is not None:
        pending = pending[: args.limit]

    print(f"Locations in source CSV: {len(locations)}")
    print(f"Already collected: {len(completed)}")
    print(f"Locations to fetch this run: {len(pending)}")
    print(f"Parameter: {PARAMETER} (daily corrected precipitation, mm/day)")
    print(f"Period: {START_YEAR}-01-01 through {END_YEAR}-12-31")

    if not OUTPUT_CSV.exists():
        write_rows([], append=False)

    last_request_time = None
    for index, location in enumerate(pending, start=1):
        if last_request_time is not None:
            delay = REQUEST_INTERVAL_SECONDS - (time.monotonic() - last_request_time)
            if delay > 0:
                time.sleep(delay)
        rainfall = fetch_rainfall(location)
        last_request_time = time.monotonic()
        summary = summarize_rainfall(location, rainfall)
        write_rows([summary], append=True)
        completed.add(location_key(location))
        print(
            f"[{index}/{len(pending)}] {location['district_name']} / "
            f"{location['thana_name']}: saved overall mean "
            f"{summary['overall_mean_daily_rain_mm']} mm/day."
        )

    print(f"Saved rainfall data to {OUTPUT_CSV}")
    print(f"Completed locations: {len(completed)} of {len(locations)}")


if __name__ == "__main__":
    main()
