import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://rrii_coach_test:test@db_test:5432/rrii_coach_test",
)
os.environ.setdefault("ASSET_STORAGE_PATH", "/tmp/rrii-coach-test-assets")
