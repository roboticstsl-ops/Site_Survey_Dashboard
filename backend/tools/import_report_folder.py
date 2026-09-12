#!/usr/bin/env python3
"""Import one real, already-transcribed survey report into Mongo + file
storage. This does NOT parse the PDF itself -- PDF table layouts vary too
much to trust an automated parser not to silently ship a wrong number into
a real database. The workflow is:

  1. Drop the client's report folder under data/elevatorData/<Site Name>/
     (PDF + Exterior Photos/, Panel/, Elevator Roof Mounting Point/, etc.)
  2. Someone (or Claude, reading the PDF) transcribes the header/elevator/
     railings/rf/integration data into a JSON file matching the Survey
     schema (see backend/tools/reports/*.json for examples) -- everything
     EXCEPT photos and reports, which this script fills in from the folder.
  3. Run this script. It copies the real photos (skipping any folder not
     named in --photo-dirs -- cell-info/speedtest screenshots stay out by
     just not listing those folders), writes FileMeta docs, and inserts one
     Survey document with real, human-verified data. No fake/sample data,
     no guessed numbers.

Usage:
    python tools/import_report_folder.py \\
        --survey-json tools/reports/binghatti_emerald.json \\
        --folder "../data/elevatorData/Binghatti Emerald" \\
        --photo-dir "Exterior Photos:Exterior Photos" \\
        --photo-dir "Panel:Button Panel" \\
        --photo-dir "Elevator Roof Mounting Point:Roof Mounting Point"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.client import get_db  # noqa: E402
from app.storage.local import LocalFileStorage  # noqa: E402
from app.core.config import get_settings  # noqa: E402


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _sorted_files(folder: Path) -> list[Path]:
    return sorted((p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")),
                  key=lambda p: p.name)


async def import_report(*, survey_json_path: str, folder_path: str, photo_dirs: list[tuple[str, str]]) -> str:
    survey_data = json.loads(Path(survey_json_path).read_text())
    folder = Path(folder_path)
    if not folder.is_dir():
        raise SystemExit(f"not a directory: {folder}")

    db = get_db()
    settings = get_settings()
    storage = LocalFileStorage(settings.file_storage_root)

    now = datetime.now(timezone.utc)
    actor = {"user_id": "import-script", "name": "Report Import"}
    survey_number = survey_data["survey_number"]

    survey_data.setdefault("schema_version", 1)
    survey_data["created_at"] = now
    survey_data["created_by"] = actor
    survey_data["updated_at"] = now
    survey_data["updated_by"] = actor
    survey_data.setdefault("revision", 1)
    survey_data.setdefault("is_deleted", False)
    survey_data.setdefault("photos", [])
    survey_data.setdefault("reports", [])
    survey_data.setdefault("legacy", None)

    existing = await db.surveys.find_one({"survey_number": survey_number})
    if existing:
        raise SystemExit(f"survey_number {survey_number!r} already imported (id {existing['_id']}) -- "
                          f"delete it first if you want to re-import.")

    result = await db.surveys.insert_one(survey_data)
    survey_id = str(result.inserted_id)

    photo_refs = []
    sort_order = 0
    for subfolder_name, label_prefix in photo_dirs:
        subfolder = folder / subfolder_name
        if not subfolder.is_dir():
            print(f"  (skip) no such folder: {subfolder_name}")
            continue
        files = _sorted_files(subfolder)
        for i, path in enumerate(files, 1):
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            data = path.read_bytes()
            storage_key = f"reports/{_slugify(survey_number)}/{_slugify(subfolder_name)}/{path.name}"
            storage.put(storage_key, data, content_type)
            await db.files.insert_one({
                "owner_type": "survey", "owner_id": survey_id, "kind": "photo",
                "storage_key": storage_key, "original_filename": path.name,
                "content_type": content_type, "byte_size": len(data), "sha256": "",
                "created_at": now, "created_by": actor, "is_deleted": False,
            })
            photo_refs.append({
                "photo_id": f"{_slugify(subfolder_name)}-{i}",
                "description": f"{label_prefix} {i}",
                "filename": path.name,
                "group": label_prefix,
                "captured_at": now,
                "sort_order": sort_order,
            })
            sort_order += 1
        print(f"  {subfolder_name}: {len(files)} photo(s) imported as '{label_prefix}'")

    await db.surveys.update_one({"_id": result.inserted_id}, {"$set": {"photos": photo_refs}})
    print(f"imported survey_number={survey_number} id={survey_id} photos={len(photo_refs)}")
    return survey_id


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--survey-json", required=True)
    parser.add_argument("--folder", required=True)
    parser.add_argument("--photo-dir", action="append", default=[], metavar="FOLDER:LABEL",
                         help="Repeatable. Only folders listed here are imported (cell-info/speedtest "
                              "folders just aren't listed).")
    args = parser.parse_args()

    photo_dirs = []
    for entry in args.photo_dir:
        if ":" not in entry:
            parser.error(f"--photo-dir must be FOLDER:LABEL, got {entry!r}")
        folder_name, label = entry.split(":", 1)
        photo_dirs.append((folder_name, label))

    asyncio.run(import_report(survey_json_path=args.survey_json, folder_path=args.folder, photo_dirs=photo_dirs))


if __name__ == "__main__":
    main()
