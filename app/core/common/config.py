import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR / "seed"
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"
DATA_DIR = Path(os.getenv("OPS_ASSISTANT_DATA_DIR", SEED_DIR))
KNOWLEDGE_FILE = os.getenv("OPS_ASSISTANT_KNOWLEDGE_FILE", "knowledge.json")
METRICS_FILE = os.getenv("OPS_ASSISTANT_METRICS_FILE", "metrics.json")
PUBLIC_TAGS_FILE = os.getenv("OPS_ASSISTANT_PUBLIC_TAGS_FILE", "public_tags.json")
