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
OUTPUT_DIR = SCRIPT_DIR / "location_monthly_2024"
OUTPUT_CSV = OUTPUT_DIR / "nasa_power_monthly_locations_2024.csv"

API_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
PARAMETERS = ("PW", "WS10M", "GWETTOP", "T2M")
COMMUNITY = "AG"
START_YEAR = 2024
END_YEAR = 2024
REQUEST_INTERVAL_SECONDS = 1.1
MAX_RETRIES = 5
REQUEST_TIMEOUT_SECONDS = 60
MONTHS = tuple(f"{START_YEAR}{month:02d}" for month in range(1, 13))
OUTPUT_FIELDS = (
    "district_name",
    "thana_name",
    "upz_name_bn",
    "latitude",
    "longitude",
    "year",
    "month",
    *PARAMETERS,
)


def load_locations():
    required_fields = {
        "district_name",
        "thana_name",
        "upz_name_bn",
        "latitude",
        "longitude",
    }
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
                "district_name": row["district_name"].strip(),
                "thana_name": row["thana_name"].strip(),
                "upz_name_bn": row["upz_name_bn"].strip(),
                "latitude": row["latitude"].strip(),
                "longitude": row["longitude"].strip(),
            }
            if not location["district_name"] or not location["thana_name"]:
                raise ValueError(
                    f"Missing district or upazila name on line {line_number} "
                    f"of {LOCATIONS_CSV}"
                )

            key = location_key(location)
            if key not in seen:
                seen.add(key)
                locations.append(location)
    return locations


def location_key(location):
    return (
        location["district_name"],
        location["thana_name"],
        location["latitude"],
        location["longitude"],
    )


def fetch_monthly_data(location):
    query = urlencode(
        {
            "parameters": ",".join(PARAMETERS),
            "community": COMMUNITY,
            "longitude": location["longitude"],
            "latitude": location["latitude"],
            "start": str(START_YEAR),
            "end": str(END_YEAR),
            "format": "JSON",
        }
    )
    request = Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "BangladeshLocationClimateCollector/1.0"},
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
        raise RuntimeError("Unable to fetch NASA POWER data after retries.")

    header = payload.get("header", {})
    status = header.get("status")
    if status is not None and status != "SUCCESS":
        raise ValueError(f"NASA POWER request failed: {header.get('messages', header)}")

    parameter_data = payload.get("properties", {}).get("parameter", {})
    missing_parameters = set(PARAMETERS) - set(parameter_data)
    if missing_parameters:
        raise ValueError(
            "NASA POWER response is missing parameters: "
            + ", ".join(sorted(missing_parameters))
        )

    rows = []
    for month_key in MONTHS:
        row = dict(location)
        row["year"] = int(month_key[:4])
        row["month"] = int(month_key[4:])
        for parameter in PARAMETERS:
            series = parameter_data[parameter]
            if month_key not in series:
                raise ValueError(
                    f"NASA POWER response is missing {parameter} for {month_key}"
                )
            row[parameter] = series[month_key]
        rows.append(row)
    return rows


def load_completed_locations():
    if not OUTPUT_CSV.exists():
        return set()

    with OUTPUT_CSV.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != list(OUTPUT_FIELDS):
            raise ValueError(f"Unexpected columns in existing file: {OUTPUT_CSV}")
        grouped_rows = {}
        for row in reader:
            key = location_key(row)
            grouped_rows.setdefault(key, []).append(row)

    completed = {
        key
        for key, rows in grouped_rows.items()
        if len(rows) == len(MONTHS)
        and {int(row["month"]) for row in rows} == set(range(1, 13))
    }
    incomplete = set(grouped_rows) - completed
    if incomplete:
        write_rows(
            [
                row
                for key in completed
                for row in grouped_rows[key]
            ],
            append=False,
        )
        print(f"Discarded {len(incomplete)} incomplete saved location(s) before resuming.")
    return completed


def write_rows(rows, append):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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
        description="Collect NASA POWER monthly data for each location in the locations CSV."
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Collect at most this many not-yet-downloaded locations (useful for a test run).",
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
    print(f"NASA POWER monthly parameters: {', '.join(PARAMETERS)}")
    print(f"Period: {START_YEAR}-01 through {END_YEAR}-12")

    if not OUTPUT_CSV.exists():
        write_rows([], append=False)

    last_request_time = None
    for index, location in enumerate(pending, start=1):
        if last_request_time is not None:
            delay = REQUEST_INTERVAL_SECONDS - (time.monotonic() - last_request_time)
            if delay > 0:
                time.sleep(delay)
        monthly_rows = fetch_monthly_data(location)
        last_request_time = time.monotonic()
        write_rows(monthly_rows, append=True)
        completed.add(location_key(location))
        print(
            f"[{index}/{len(pending)}] {location['district_name']} / "
            f"{location['thana_name']}: saved 12 months."
        )

    print(f"Saved monthly records to {OUTPUT_CSV}")
    print(f"Completed locations: {len(completed)} of {len(locations)}")


if __name__ == "__main__":
    main()
