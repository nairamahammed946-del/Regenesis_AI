"""Import a source-attributed factory/facility CSV into ReGenesis.

All imported facilities remain UNVERIFIED. This script does not imply they produce
or consume a particular waste stream; add those facts as separate listings only
when confirmed by the facility or a reliable source.
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.models.user import Factory

REQUIRED = {"name", "sector", "role", "city"}
OPTIONAL = {"address", "latitude", "longitude", "contact_email", "contact_phone", "description", "source_name", "source_url", "source_date"}


def as_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Import facilities from a CSV file")
    parser.add_argument("csv_file", help="CSV file encoded as UTF-8 or UTF-8-SIG")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing")
    args = parser.parse_args()
    path = Path(args.csv_file)
    if not path.is_file():
        raise SystemExit(f"File not found: {path}")
    Base.metadata.create_all(bind=engine)
    added = skipped = invalid = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED - fields
        if missing:
            raise SystemExit("Missing required CSV columns: " + ", ".join(sorted(missing)))
        unknown = fields - REQUIRED - OPTIONAL
        if unknown:
            print("Ignoring unknown columns:", ", ".join(sorted(unknown)))
        with SessionLocal() as db:
            for line, row in enumerate(reader, start=2):
                name = (row.get("name") or "").strip()
                city = (row.get("city") or "").strip()
                sector = (row.get("sector") or "").strip()
                role = (row.get("role") or "").strip()
                if not all((name, city, sector, role)):
                    invalid += 1
                    print(f"Line {line}: skipped (name/sector/role/city required)")
                    continue
                exists = db.query(Factory).filter(Factory.name == name).first()
                if exists:
                    skipped += 1
                    continue
                provenance = " | ".join(x for x in [
                    f"Source: {row.get('source_name','').strip()}" if row.get("source_name") else "",
                    f"Source URL: {row.get('source_url','').strip()}" if row.get("source_url") else "",
                    f"Source date: {row.get('source_date','').strip()}" if row.get("source_date") else "",
                ] if x)
                description = (row.get("description") or "").strip()
                if provenance:
                    description = (description + "\n" + provenance).strip()
                if args.dry_run:
                    added += 1
                    continue
                db.add(Factory(
                    name=name, sector=sector, role=role, city=city,
                    address=(row.get("address") or None),
                    latitude=as_float(row.get("latitude")), longitude=as_float(row.get("longitude")),
                    contact_email=(row.get("contact_email") or None), contact_phone=(row.get("contact_phone") or None),
                    description=description or "Imported public facility record; details require confirmation.",
                    is_verified=False,
                    data_origin="public_directory",
                    source_name=(row.get("source_name") or None),
                    source_url=(row.get("source_url") or None),
                    source_date=(row.get("source_date") or None),
                ))
                added += 1
            if not args.dry_run:
                db.commit()
    print(f"Imported/new: {added}; already existed: {skipped}; invalid rows: {invalid}; dry_run={args.dry_run}")
    print("Imported facilities are unverified. Do not treat them as active suppliers/buyers until they confirm their profile and listings.")

if __name__ == "__main__":
    main()
