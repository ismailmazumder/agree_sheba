import csv
import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DATA_DIR = Path(__file__).parent
REQUEST_INTERVAL_SECONDS = 1.1
MAX_RETRIES = 5
REQUEST_TIMEOUT_SECONDS = 30

DISTRICT_CODES = {
    "Cox'sbazar": 2022,
    "Kishoreganj": 3048,
    "Kurigram": 5549,
    "Cumilla": 2019,
    "Kushtia": 4050,
    "Khagrachhari": 2046,
    "Khulna": 4047,
    "Gaibandha": 5532,
    "Gazipur": 3033,
    "Gopalganj": 3035,
    "Chattogram": 2015,
    "Chandpur": 2013,
    "Chapainawabganj": 5070,
    "Chuadanga": 4018,
    "Joypurhat": 5038,
    "Jamalpur": 4539,
    "Jhalokathi": 1042,
    "Jhenaidah": 4044,
    "Tangail": 3093,
    "Thakurgaon": 5594,
    "Dhaka": 3026,
    "Dinajpur": 5527,
    "Naogaon": 5064,
    "Narail": 4065,
    "Narsingdi": 3068,
    "Natore": 5069,
    "Narayanganj": 3067,
    "Nilphamari": 5573,
    "Netrakona": 4572,
    "Noakhali": 2075,
    "Panchagarh": 5577,
    "Patuakhali": 1078,
    "Pabna": 5076,
    "Pirojpur": 1079,
    "Faridpur": 3029,
    "Feni": 2030,
    "Bogura": 5010,
    "Barguna": 1004,
    "Barishal": 1006,
    "Bagerhat": 4001,
    "Bandarban": 2003,
    "Brahamanbaria": 2012,
    "Bhola": 1009,
    "Mymensingh": 4561,
    "Magura": 4055,
    "Madaripur": 3054,
    "Manikganj": 3056,
    "Munshiganj": 3059,
    "Meherpur": 4057,
    "Maulvibazar": 6058,
    "Jashore": 4041,
    "Rangpur": 5585,
    "Rangamati": 2084,
    "Rajbari": 3082,
    "Rajshahi": 5081,
    "Lakshmipur": 2051,
    "Lalmonirhat": 5552,
    "Shariatpur": 3086,
    "Sherpur": 4589,
    "Satkhira": 4087,
    "Sirajganj": 5088,
    "Sylhet": 6091,
    "Sunamganj": 6090,
    "Habiganj": 6036,
}

BASE_URL = "https://api1.cropzoning.gov.bd/api"
DISTRICT_UPAZILAS_URL = BASE_URL + "/crop-suitability-upazilas/{district_code}"
CE_UPAZILAS_URL = BASE_URL + "/ceupazilas/{district_code}"
SUITABILITY_URL = BASE_URL + "/crop-suitability/{upazila_code}"
ECONOMICS_URL = BASE_URL + "/crop-economics/getEcData/{upazila_code}"

LOCATION_FIELDS = (
    "district_name",
    "district_code",
    "upazila_code",
    "thana_name",
    "upz_name_bn",
)
DISTRICT_CSV_FIELDS = LOCATION_FIELDS
DISTRICT_LOCATIONS_CSV_FIELDS = ("district", "location")
SUITABILITY_FIELDS = (
    "crop_id",
    "crop_season",
    "crop_season_bn",
    "crop_name",
    "crop_name_bn",
    "crop_var",
    "crop_var_bn",
    "vs",
    "s",
    "ms",
    "ls",
    "ns",
)
ECONOMICS_FIELDS = (
    "gm_tk_dec",
    "bcr_vc",
    "bcr_tc",
    "crop_name",
    "crop_name_bn",
    "situation_name",
    "situation_name_bn",
    "season_name",
    "season_name_bn",
)
SUITABILITY_MATCH_FIELDS = ("crop_name", "crop_season", "crop_var")
MERGED_ECONOMICS_FIELDS = LOCATION_FIELDS + ECONOMICS_FIELDS + (
    "crop_id",
    "crop_season",
    "crop_season_bn",
    "crop_var",
    "crop_var_bn",
    "vs",
    "s",
    "ms",
    "ls",
    "ns",
)


def fetch_json(url, description):
    for attempt in range(MAX_RETRIES):
        if attempt == 0:
            time.sleep(REQUEST_INTERVAL_SECONDS)
        try:
            request = Request(url, headers={"User-Agent": "MightyCropData/1.0"})
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code != 429 or attempt == MAX_RETRIES - 1:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            print(f"Rate limited while fetching {description}; retrying in {delay} seconds.")
            time.sleep(delay)
    raise RuntimeError(f"Unable to fetch {description} after {MAX_RETRIES} attempts")


def require_records(value, description):
    if not isinstance(value, list):
        raise ValueError(f"Unexpected response for {description}: expected a list")
    for record in value:
        if not isinstance(record, dict):
            raise ValueError(f"Unexpected record for {description}: expected an object")
    return value


def validate_fields(record, fields, description):
    missing_fields = set(fields) - record.keys()
    if missing_fields:
        raise ValueError(
            f"{description} is missing fields: {', '.join(sorted(missing_fields))}"
        )


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows to {path}")


def fetch_locations(endpoint, description):
    locations = []
    seen_codes = set()
    district_count = len(DISTRICT_CODES)

    for index, (district_name, district_code) in enumerate(DISTRICT_CODES.items(), start=1):
        url = endpoint.format(district_code=district_code)
        records = require_records(
            fetch_json(url, f"{description} for {district_name}"),
            f"{description} for {district_name}",
        )
        for record in records:
            validate_fields(record, ("upazila_code", "thana_name", "upz_name_bn"), description)
            upazila_code = str(record["upazila_code"]).strip()
            if not upazila_code:
                raise ValueError(f"{description} returned an empty upazila code")
            if upazila_code in seen_codes:
                raise ValueError(f"{description} returned duplicate upazila code {upazila_code}")
            seen_codes.add(upazila_code)
            locations.append(
                {
                    "district_name": district_name,
                    "district_code": str(district_code),
                    "upazila_code": upazila_code,
                    "thana_name": record["thana_name"],
                    "upz_name_bn": record["upz_name_bn"],
                }
            )
        print(f"{description}: fetched {index}/{district_count} districts.")

    return locations


def fetch_crop_suitability(locations):
    rows = []
    for index, location in enumerate(locations, start=1):
        url = SUITABILITY_URL.format(upazila_code=location["upazila_code"])
        crops = require_records(
            fetch_json(url, f"crop suitability for upazila {location['upazila_code']}"),
            f"crop suitability for upazila {location['upazila_code']}",
        )
        for crop in crops:
            validate_fields(crop, SUITABILITY_FIELDS, "Crop suitability record")
            rows.append(
                {
                    **{field: location[field] for field in LOCATION_FIELDS},
                    **{field: crop[field] for field in SUITABILITY_FIELDS},
                }
            )
        if index % 25 == 0 or index == len(locations):
            print(f"Crop suitability: fetched {index}/{len(locations)} upazilas.")
    return rows


def fetch_crop_economics(locations):
    rows = []
    for index, location in enumerate(locations, start=1):
        url = ECONOMICS_URL.format(upazila_code=location["upazila_code"])
        data = fetch_json(url, f"crop economics for upazila {location['upazila_code']}")
        if not isinstance(data, dict):
            raise ValueError(
                f"Unexpected economics response for upazila {location['upazila_code']}: "
                "expected an object"
            )
        records = require_records(
            data.get("pc_cs"),
            f"crop economics for upazila {location['upazila_code']}",
        )
        for record in records:
            validate_fields(record, ECONOMICS_FIELDS, "Crop economics record")
            rows.append(
                {
                    **{field: location[field] for field in LOCATION_FIELDS},
                    **{field: record[field] for field in ECONOMICS_FIELDS},
                }
            )
        if index % 25 == 0 or index == len(locations):
            print(f"Crop economics: fetched {index}/{len(locations)} upazilas.")
    return rows


def merge_economics_with_suitability(economics, suitability):
    suitability_by_key = {}
    for crop in suitability:
        key = (
            crop["upazila_code"].strip(),
            crop["crop_name"].strip().casefold(),
            crop["crop_season"].strip().casefold(),
            crop["crop_var"].strip().casefold(),
        )
        suitability_by_key.setdefault(key, []).append(crop)

    merged_rows = []
    matched_records = 0
    for record in economics:
        key = (
            record["upazila_code"].strip(),
            record["crop_name"].strip().casefold(),
            record["season_name"].strip().casefold(),
            record["situation_name"].strip().casefold(),
        )
        matches = suitability_by_key.get(key, [])
        if not matches:
            merged_rows.append(
                {
                    **{field: record[field] for field in LOCATION_FIELDS},
                    **{field: record[field] for field in ECONOMICS_FIELDS},
                    **{
                        field: ""
                        for field in MERGED_ECONOMICS_FIELDS
                        if field not in LOCATION_FIELDS + ECONOMICS_FIELDS
                    },
                }
            )
            continue

        matched_records += 1
        for crop in matches:
            if record["district_code"].strip() != crop["district_code"].strip():
                raise ValueError(
                    f"District-code mismatch for upazila {record['upazila_code']}: "
                    f"{record['district_code']} != {crop['district_code']}"
                )
            merged_rows.append(
                {
                    **{field: record[field] for field in LOCATION_FIELDS},
                    **{field: record[field] for field in ECONOMICS_FIELDS},
                    **{
                        field: crop[field]
                        for field in MERGED_ECONOMICS_FIELDS
                        if field not in LOCATION_FIELDS + ECONOMICS_FIELDS
                    },
                }
            )

    print(f"Economics/suitability: matched {matched_records} of {len(economics)} economics records.")
    return merged_rows


def merge_ce_locations_with_suitability(ce_locations, suitability):
    ce_codes = {location["upazila_code"] for location in ce_locations}
    location_by_code = {location["upazila_code"]: location for location in ce_locations}
    merged_rows = []
    matched_codes = set()

    for crop in suitability:
        upazila_code = crop["upazila_code"].strip()
        location = location_by_code.get(upazila_code)
        if location is None:
            continue
        if location["district_code"] != crop["district_code"].strip():
            raise ValueError(
                f"District-code mismatch for upazila {upazila_code}: "
                f"{location['district_code']} != {crop['district_code']}"
            )
        merged_rows.append(
            {
                **{field: location[field] for field in LOCATION_FIELDS},
                **{field: crop[field] for field in SUITABILITY_FIELDS},
            }
        )
        matched_codes.add(upazila_code)

    print(
        f"CE/suitability: matched {len(matched_codes)} of {len(ce_codes)} CE upazilas."
    )
    return merged_rows


def main():
    print("Step 1/5: Fetching crop-zoning upazila locations.")
    locations = fetch_locations(DISTRICT_UPAZILAS_URL, "Crop-zoning upazilas")
    if not locations:
        raise ValueError("The crop-zoning API returned no upazilas.")
    write_csv(DATA_DIR / "district_code.csv", DISTRICT_CSV_FIELDS, locations)
    district_locations = [
        {
            "district": location["district_name"],
            "location": location["thana_name"],
        }
        for location in locations
    ]
    write_csv(
        DATA_DIR / "district_locations.csv",
        DISTRICT_LOCATIONS_CSV_FIELDS,
        district_locations,
    )

    print("Step 2/5: Fetching CE upazila locations.")
    ce_locations = fetch_locations(CE_UPAZILAS_URL, "CE upazilas")
    write_csv(DATA_DIR / "ceupazilas.csv", DISTRICT_CSV_FIELDS, ce_locations)

    print("Step 3/5: Fetching crop-suitability records.")
    suitability = fetch_crop_suitability(locations)
    write_csv(
        DATA_DIR / "crop_suitability.csv",
        LOCATION_FIELDS + SUITABILITY_FIELDS,
        suitability,
    )

    print("Step 4/5: Fetching crop-economics records.")
    economics = fetch_crop_economics(locations)
    write_csv(
        DATA_DIR / "crop_economics.csv",
        LOCATION_FIELDS + ECONOMICS_FIELDS,
        economics,
    )

    print("Step 5/5: Creating merged CSV files.")
    economics_suitability = merge_economics_with_suitability(economics, suitability)
    write_csv(
        DATA_DIR / "crop_economics_suitability.csv",
        MERGED_ECONOMICS_FIELDS,
        economics_suitability,
    )

    ce_suitability = merge_ce_locations_with_suitability(ce_locations, suitability)
    write_csv(
        DATA_DIR / "crop_suitability_ceupazilas.csv",
        LOCATION_FIELDS + SUITABILITY_FIELDS,
        ce_suitability,
    )
    print("All data collection and merge steps completed.")


if __name__ == "__main__":
    main()
