"""Write the canonical DB schema to schema.sql so it can be loaded into Turso:
    python3 scripts/export_schema.py            # writes ./schema.sql
    turso db shell <db> < schema.sql            # load it
Keeps a single source of truth: app.db._SCHEMA."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import _SCHEMA

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.sql")

if __name__ == "__main__":
    with open(OUT, "w") as f:
        f.write("-- Generated from app.db._SCHEMA — do not edit by hand.\n")
        f.write(_SCHEMA.strip() + "\n")
    print("wrote", OUT)
