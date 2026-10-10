"""Reset the working database to the original: copy campus_customs.db -> campus_customs_new.db.

Run before every full ticket run:  python -m backend.reset_db
"""

import shutil

from .config import ORIGINAL_DB, WORKING_DB


def reset_database() -> None:
    if not ORIGINAL_DB.exists():
        raise FileNotFoundError(f"Original database missing: {ORIGINAL_DB}")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)


if __name__ == "__main__":
    reset_database()
    print(f"Reset {WORKING_DB.name} from {ORIGINAL_DB.name}")
