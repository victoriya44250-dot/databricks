
import argparse
import csv
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import TableProperties, RecordType, StreamConfigurationOptions

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "lab8-ci-cd/data/europe_cereal_yield_climate_1990_2022.csv"

load_dotenv(Path(__file__).with_name(".env"))

parser = argparse.ArgumentParser()
parser.add_argument("--start-row", type=int, default=1)
parser.add_argument("--max-events", type=int, default=10)
parser.add_argument("--rate", type=float, default=10)
args = parser.parse_args()

if args.start_row < 1 or args.max_events < 1 or args.rate <= 0:
    parser.error("start-row, max-events and rate must be positive")

sdk = ZerobusSdk(
    os.environ["ZEROBUS_SERVER_ENDPOINT"],
    os.environ["DATABRICKS_WORKSPACE_URL"]
)

stream = sdk.create_stream(
    os.environ["ZEROBUS_CLIENT_ID"],
    os.environ["ZEROBUS_CLIENT_SECRET"],
    TableProperties(os.environ["ZEROBUS_TABLE_NAME"]),
    StreamConfigurationOptions(record_type=RecordType.JSON)
)

sent = 0

try:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)

        for row_number, row in enumerate(rows, start=1):
            if row_number < args.start_row:
                continue
            if sent >= args.max_events:
                break

            event = {
                "event_id": f"agri-{row_number:06d}",
                "area": row["AREA"],
                "item": row["ITEM"],
                "year": int(row["YEAR"]),
                "crop_yield": float(row["YIELD"]) if row["YIELD"] else None,
                "area_harvested": float(row["AREA_HARVESTED"]) if row["AREA_HARVESTED"] else None,
                "production_quantity": float(row["PRODUCTION_QUANTITY"]) if row["PRODUCTION_QUANTITY"] else None,
                "producer_sent_at": time.time_ns() // 1000
            }

            offset = stream.ingest_record_offset(event)
            sent += 1
            time.sleep(1 / args.rate)

    if sent:
        stream.wait_for_offset(offset)
    print(f"Confirmed {sent} agricultural events")

finally:
    stream.close()
