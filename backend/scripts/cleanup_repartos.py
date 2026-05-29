"""Utility script to clean planning data for debugging.

Deletes all rows from:
- asignaciones_opl
- repartos

It preserves master data tables (familias, articulos, operarios, etc.).

Usage:
  python backend/scripts/cleanup_repartos.py --dry-run
  python backend/scripts/cleanup_repartos.py --yes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import func

# Permite ejecutar directamente: `python backend/scripts/cleanup_repartos.py`
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from src.database import get_session
from src.database.schema import AsignacionOPL, Reparto


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete all repartos and asignaciones_opl records (debug utility)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many rows would be deleted without applying changes.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation.",
    )
    return parser.parse_args()


def ask_confirmation() -> bool:
    answer = input("This will permanently delete all repartos and asignaciones. Continue? [y/N]: ").strip().lower()
    return answer in {"y", "yes", "s", "si"}


def main() -> int:
    args = parse_args()

    with get_session() as session:
        n_asignaciones = session.query(func.count(AsignacionOPL.id_opl)).scalar() or 0
        n_repartos = session.query(func.count(Reparto.semana)).scalar() or 0

        print(f"Asignaciones actuales: {n_asignaciones}")
        print(f"Repartos actuales: {n_repartos}")

        if args.dry_run:
            print("Dry-run mode: no changes applied.")
            return 0

        if not args.yes and not ask_confirmation():
            print("Cancelled.")
            return 0

        deleted_asignaciones = session.query(AsignacionOPL).delete(synchronize_session=False)
        deleted_repartos = session.query(Reparto).delete(synchronize_session=False)
        session.commit()

        print(f"Deleted asignaciones: {deleted_asignaciones}")
        print(f"Deleted repartos: {deleted_repartos}")
        print("Cleanup completed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
