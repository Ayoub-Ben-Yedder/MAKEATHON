import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'inventory.db')}"
SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret"

ROBOT_SIMULATE = True
