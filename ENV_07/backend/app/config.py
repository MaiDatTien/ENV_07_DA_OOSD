import os
from pathlib import Path


def _load_env() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env()


class Settings:
    DB_SERVER = os.getenv("DB_SERVER", "localhost")
    DB_NAME = os.getenv("DB_NAME", "ENV07_DB")
    DB_USER = os.getenv("DB_USER", "sa")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

    PUMP_FLOW_LPM = 2.0

    REC_VALID_HOURS = 6
    MAX_PUMP_SEC = 300
    DEVICE_OFFLINE_SEC = 30
    SESSION_HOURS = 12
    PULSE_SEC = 5
    SOAK_SEC = 5
    SOAK_MINUTES = 30
    SOIL_RAW_MIN = 50
    SOIL_RAW_MAX = 4090

    FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def connection_string(self) -> str:
        return (
            f"DRIVER={{{self.DB_DRIVER}}};SERVER={self.DB_SERVER};DATABASE={self.DB_NAME};"
            f"UID={self.DB_USER};PWD={self.DB_PASSWORD};TrustServerCertificate=yes;"
        )


settings = Settings()
