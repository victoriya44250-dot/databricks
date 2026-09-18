import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "synthetic_data" / "turbine_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

start_time = datetime(2026, 9, 1, 0, 0)

for file_number in range(1001, 1011):

    file_path = OUTPUT_DIR / f"turbine_{file_number:04d}.csv"

    with open(file_path, "w", newline="") as file:
        writer = csv.writer(file)

        writer.writerow([
            "timestamp",
            "turbine_id",
            "wind_speed",
            "temperature",
            "power_output",
            "status",
            "maintenance_required"      # NEW COLUMN
        ])

        for row_number in range(10):

            timestamp = start_time + timedelta(
                minutes=(file_number - 1) * 10 + row_number
            )

            writer.writerow([
                timestamp.isoformat(),
                f"WT-{random.randint(1, 10):02d}",
                round(random.uniform(2, 20), 2),
                round(random.uniform(25, 70), 2),
                round(random.uniform(100, 2500), 2),
                random.choice(["running", "running", "running", "idle"]),
                random.choice([True, False])       # NEW VALUE
            ])