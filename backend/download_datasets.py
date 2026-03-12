#!/usr/bin/env python3
"""
download_datasets.py

Download external dialogue datasets for CMS experiments and save them locally.

Supported datasets:
- DailyDialog  -> roskoN/dailydialog
- SAMSum       -> knkarthick/samsum
- SwDA         -> cgpotts/swda

Examples:
    python3 download_datasets.py
    python3 download_datasets.py --datasets dailydialog samsum
    python3 download_datasets.py --format jsonl --output-dir experiments/data/external
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from datasets import DatasetDict, load_dataset


DATASET_REGISTRY = {
    "dailydialog": {
        "hf_id": "roskoN/dailydialog",
        "subset": None,
    },
    "samsum": {
        "hf_id": "knkarthick/samsum",
        "subset": None,
    },
    "swda": {
        "hf_id": "cgpotts/swda",
        "subset": None,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download real datasets for CMS / dialogue experiments."
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=sorted(DATASET_REGISTRY.keys()),
        default=sorted(DATASET_REGISTRY.keys()),
        help="Datasets to download.",
    )
    parser.add_argument(
        "--output-dir",
        default="experiments/data/external",
        help="Directory where datasets will be saved.",
    )
    parser.add_argument(
        "--format",
        choices=["parquet", "jsonl"],
        default="parquet",
        help="Output format per split.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload/rewrite local files if they already exist.",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_jsonl(records: Iterable[dict], output_file: Path) -> None:
    with output_file.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def export_split(split_dataset, output_file: Path, file_format: str) -> None:
    if file_format == "parquet":
        split_dataset.to_parquet(str(output_file))
    elif file_format == "jsonl":
        write_jsonl(split_dataset, output_file)
    else:
        raise ValueError(f"Unsupported format: {file_format}")


def normalize_loaded_dataset(obj) -> DatasetDict:
    if isinstance(obj, DatasetDict):
        return obj
    return DatasetDict({"train": obj})


def download_one(
    dataset_name: str,
    output_dir: Path,
    file_format: str,
    force: bool = False,
) -> None:
    config = DATASET_REGISTRY[dataset_name]
    hf_id = config["hf_id"]
    subset = config["subset"]

    print(f"[+] Downloading {dataset_name} from {hf_id} ...")
    loaded = load_dataset(hf_id, subset) if subset else load_dataset(hf_id)
    ds = normalize_loaded_dataset(loaded)

    dataset_dir = output_dir / dataset_name
    ensure_dir(dataset_dir)

    metadata = {
        "dataset_name": dataset_name,
        "hf_id": hf_id,
        "subset": subset,
        "splits": list(ds.keys()),
        "num_rows": {split: ds[split].num_rows for split in ds.keys()},
        "features": {
            split: {k: str(v) for k, v in ds[split].features.items()}
            for split in ds.keys()
        },
    }

    metadata_file = dataset_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    suffix = "parquet" if file_format == "parquet" else "jsonl"

    for split_name, split_dataset in ds.items():
        output_file = dataset_dir / f"{split_name}.{suffix}"

        if output_file.exists() and not force:
            print(f"    [-] Skipping existing {output_file}")
            continue

        print(f"    [>] Saving split={split_name} rows={split_dataset.num_rows} -> {output_file}")
        export_split(split_dataset, output_file, file_format)

    print(f"[✓] Finished {dataset_name}\n")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    try:
        for dataset_name in args.datasets:
            download_one(
                dataset_name=dataset_name,
                output_dir=output_dir,
                file_format=args.format,
                force=args.force,
            )
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\n[!] Failed: {exc}", file=sys.stderr)
        return 1

    print("[✓] All requested datasets downloaded successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
