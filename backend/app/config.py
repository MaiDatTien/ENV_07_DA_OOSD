class Settings:
    DB_SERVER = "localhost"
    DB_NAME = "ENV07_DB"
    DB_USER = "sa"
    DB_PASSWORD = "123"
    DB_DRIVER = "ODBC Driver 17 for SQL Server"

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
