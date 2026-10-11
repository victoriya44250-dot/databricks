
import csv
from pathlib import Path

# Folder containing this script
data_dir = Path(__file__).resolve().parent

source_file = data_dir / "europe_cereal_yield_climate_1990_2022.csv"

# Read the source CSV
with source_file.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    columns = reader.fieldnames

    if not columns:
        raise ValueError("CSV header is missing")

    # Take 20 rows for the streaming demonstration
    rows = []

    for row in reader:
        rows.append(row)
        if len(rows) == 20:
            break

if len(rows) < 20:
    raise ValueError("Source CSV contains fewer than 20 data rows")

# Create two files with different rows
parts = {
    "climate_part_01.csv": rows[:10],
    "climate_part_02.csv": rows[10:20],
}

for filename, part_rows in parts.items():
    output_file = data_dir / filename

    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(part_rows)

    print(f"Created: {output_file.name} ({len(part_rows)} rows)")
