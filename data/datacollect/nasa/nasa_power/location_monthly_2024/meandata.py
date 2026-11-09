import csv
from collections import defaultdict
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent
INPUT_CSV = DATA_DIR / "nasa_power_monthly_locations_2024.csv"
OUTPUT_CSV = DATA_DIR / "nasa_power_location_means_2024.csv"

LOCATION_FIELDS = (
    "district_name",
    "thana_name",
    "upz_name_bn",
    "latitude",
    "longitude",
    "year",
)
PARAMETERS = ("PW", "WS10M", "GWETTOP", "T2M")
FILL_VALUE = -999.0
OUTPUT_FIELDS = LOCATION_FIELDS + tuple(f"mean_{name}" for name in PARAMETERS)


def main():
    groups = {}
    with INPUT_CSV.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_fields = set(LOCATION_FIELDS) | {"month", *PARAMETERS}
        missing_fields = required_fields - set(reader.fieldnames or ())
        if missing_fields:
            raise ValueError(
                f"Input CSV is missing columns: {', '.join(sorted(missing_fields))}"
            )

        for line_number, row in enumerate(reader, start=2):
            location = tuple(row[field].strip() for field in LOCATION_FIELDS)
            key = location
            group = groups.setdefault(
                key,
                {
                    "months": set(),
                    "sums": {parameter: 0.0 for parameter in PARAMETERS},
                    "counts": {parameter: 0 for parameter in PARAMETERS},
                },
            )

            try:
                month = int(row["month"])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid month on input line {line_number}") from error
            if not 1 <= month <= 12:
                raise ValueError(f"Month out of range on input line {line_number}")
            if month in group["months"]:
                raise ValueError(
                    f"Duplicate month {month} for {location[0]} / {location[1]}"
                )
            group["months"].add(month)

            for parameter in PARAMETERS:
                try:
                    value = float(row[parameter])
                except (TypeError, ValueError) as error:
                    raise ValueError(
                        f"Invalid {parameter} value on input line {line_number}"
                    ) from error
                if value != FILL_VALUE:
                    group["sums"][parameter] += value
                    group["counts"][parameter] += 1

    summary_rows = []
    for location, group in sorted(
        groups.items(), key=lambda item: (item[0][0].casefold(), item[0][1].casefold())
    ):
        if group["months"] != set(range(1, 13)):
            raise ValueError(
                f"Incomplete monthly data for {location[0]} / {location[1]}: "
                f"found months {sorted(group['months'])}"
            )
        summary = dict(zip(LOCATION_FIELDS, location))
        for parameter in PARAMETERS:
            count = group["counts"][parameter]
            if count == 0:
                raise ValueError(
                    f"No valid {parameter} values for {location[0]} / {location[1]}"
                )
            summary[f"mean_{parameter}"] = f"{group['sums'][parameter] / count:.6f}"
        summary_rows.append(summary)

    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Saved mean data for {len(summary_rows)} locations to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()