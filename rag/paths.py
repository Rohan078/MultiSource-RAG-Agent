from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STORE_DIR = ROOT / "store"
INDEX_PATH = STORE_DIR / "index.json"
DB_PATH = STORE_DIR / "data.db"
