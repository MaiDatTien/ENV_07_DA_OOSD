from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from .config import settings
from .database import Database
from .domain import OverrideRecord, Plant, PlantStage, PumpRequest, Recommendation, WaterQuota


def _as_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return v


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    def count(self) -> int:
        return self.db.query_one("SELECT COUNT(*) AS n FROM Users")["n"]

    def by_username(self, username: str) -> Optional[dict]:
        return self.db.query_one("SELECT * FROM Users WHERE Username = ?", username)

    def add(self, username, full_name, salt, pw_hash, role) -> None:
        self.db.execute("""INSERT INTO Users (Username, FullName, Salt, PasswordHash, Role)
                           VALUES (?, ?, ?, ?, ?)""", username, full_name, salt, pw_hash, role)

    def list(self) -> list[dict]:
        return self.db.query("""SELECT UserId, Username, FullName, Role, IsActive, CreatedAt
                                FROM Users ORDER BY IsActive DESC, UserId""")

    def get(self, user_id: int) -> Optional[dict]:
        return self.db.query_one("SELECT * FROM Users WHERE UserId = ?", user_id)

    def count_active_role(self, role: str) -> int:
        return self.db.query_one("SELECT COUNT(*) AS n FROM Users WHERE Role = ? AND IsActive = 1", role)["n"]

    def update(self, user_id: int, full_name: str, role: str) -> None:
        self.db.execute("UPDATE Users SET FullName = ?, Role = ? WHERE UserId = ?", full_name, role, user_id)

    def set_password(self, user_id: int, salt: str, pw_hash: str) -> None:
        with self.db.transaction() as cur:
            cur.execute("UPDATE Users SET Salt = ?, PasswordHash = ? WHERE UserId = ?", salt, pw_hash, user_id)
            cur.execute("DELETE FROM Sessions WHERE UserId = ?", user_id)

    def set_active(self, user_id: int, active: bool) -> None:
        with self.db.transaction() as cur:
            cur.execute("UPDATE Users SET IsActive = ? WHERE UserId = ?", int(active), user_id)
            if not active:
                cur.execute("DELETE FROM Sessions WHERE UserId = ?", user_id)

    def history_count(self, user_id: int) -> int:
        return self.db.query_one("""
            SELECT (SELECT COUNT(*) FROM Crops WHERE CreatedBy = ?)
                 + (SELECT COUNT(*) FROM Plantings WHERE CreatedBy = ?)
                 + (SELECT COUNT(*) FROM Recommendations WHERE CreatedBy = ? OR AppliedBy = ?)
                 + (SELECT COUNT(*) FROM RecommendationOverrides WHERE UserId = ?)
                 + (SELECT COUNT(*) FROM PumpRequests WHERE RequestedBy = ? OR ReviewedBy = ?)
                 + (SELECT COUNT(*) FROM PumpCommands WHERE IssuedBy = ?)
                 + (SELECT COUNT(*) FROM IrrigationEvents WHERE IssuedBy = ?)
                 + (SELECT COUNT(*) FROM AppSettings WHERE UpdatedBy = ?) AS n""", *([user_id] * 10))["n"]

    def delete(self, user_id: int) -> None:
        with self.db.transaction() as cur:
            cur.execute("DELETE FROM Sessions WHERE UserId = ?", user_id)
            cur.execute("DELETE FROM Users WHERE UserId = ?", user_id)


class SessionRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, token: str, user_id: int, expires: datetime) -> None:
        self.db.execute("DELETE FROM Sessions WHERE ExpiresAt < SYSDATETIME()")
        self.db.execute("INSERT INTO Sessions (Token, UserId, ExpiresAt) VALUES (?, ?, ?)", token, user_id, expires)

    def user_of(self, token: str) -> Optional[dict]:
        return self.db.query_one("""
            SELECT u.UserId, u.Username, u.FullName, u.Role
            FROM Sessions s JOIN Users u ON u.UserId = s.UserId
            WHERE s.Token = ? AND s.ExpiresAt > SYSDATETIME() AND u.IsActive = 1""", token)

    def remove(self, token: str) -> None:
        self.db.execute("DELETE FROM Sessions WHERE Token = ?", token)


class CropRepository:

    def __init__(self, db: Database):
        self.db = db

    def stages(self, crop_id: int) -> list[PlantStage]:
        rows = self.db.query("SELECT * FROM CropStages WHERE CropId = ? ORDER BY StageOrder", crop_id)
        return [PlantStage(r["StageOrder"], r["Name"], r["DurationDays"],
                           r["MoistureMin"], r["MoistureMax"], r["StageId"]) for r in rows]

    def list(self) -> list[dict]:
        crops = self.db.query("""
            SELECT c.CropId, c.Name, c.Description, c.CreatedAt, u.FullName AS CreatedByName,
                   (SELECT COUNT(*) FROM Plantings p WHERE p.CropId = c.CropId) AS PlantingCount
            FROM Crops c LEFT JOIN Users u ON u.UserId = c.CreatedBy ORDER BY c.Name""")
        stages = self.db.query("SELECT * FROM CropStages ORDER BY CropId, StageOrder")
        for c in crops:
            c["Stages"] = [st for st in stages if st["CropId"] == c["CropId"]]
        return crops

    def get(self, crop_id: int) -> Optional[dict]:
        return self.db.query_one("SELECT * FROM Crops WHERE CropId = ?", crop_id)

    def by_name(self, name: str) -> Optional[dict]:
        return self.db.query_one("SELECT * FROM Crops WHERE Name = ?", name)

    def add(self, name: str, description: Optional[str], user_id: int) -> int:
        with self.db.transaction() as cur:
            cur.execute("""INSERT INTO Crops (Name, Description, CreatedBy) OUTPUT INSERTED.CropId
                           VALUES (?, ?, ?)""", name, description, user_id)
            return int(cur.fetchone()[0])

    def update(self, crop_id: int, name: str, description: Optional[str]) -> None:
        self.db.execute("UPDATE Crops SET Name = ?, Description = ? WHERE CropId = ?", name, description, crop_id)

    def delete(self, crop_id: int) -> None:
        self.db.execute("DELETE FROM Crops WHERE CropId = ?", crop_id)

    def replace_stages(self, crop_id: int, stages: list[PlantStage]) -> None:
        with self.db.transaction() as cur:
            cur.execute("DELETE FROM CropStages WHERE CropId = ?", crop_id)
            for st in stages:
                cur.execute("""INSERT INTO CropStages (CropId, StageOrder, Name, DurationDays, MoistureMin, MoistureMax)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            crop_id, st.order, st.name, st.duration_days, st.moisture_min, st.moisture_max)


class PlantingRepository:

    def __init__(self, db: Database):
        self.db = db
        self.crops = CropRepository(db)

    def active(self) -> Optional[Plant]:
        r = self.db.query_one("""
            SELECT p.*, c.Name AS CropName FROM Plantings p JOIN Crops c ON c.CropId = p.CropId
            WHERE p.Status = 'ACTIVE'""")
        if not r:
            return None
        return Plant(r["CropName"], _as_date(r["PlantedDate"]), r["DailyQuotaLiters"], r["MaxLitersPerWatering"],
                     settings.PUMP_FLOW_LPM, bool(r["AutoMode"]), self.crops.stages(r["CropId"]),
                     planting_id=r["PlantingId"], crop_id=r["CropId"])

    def list(self) -> list[dict]:
        return self.db.query("""
            SELECT p.PlantingId, p.CropId, c.Name AS CropName, p.PlantedDate, p.DailyQuotaLiters,
                   p.MaxLitersPerWatering, p.Status, p.Note, p.CreatedAt, p.EndedAt, u.FullName AS CreatedByName,
                   (SELECT ISNULL(SUM(EstimatedLiters), 0) FROM IrrigationEvents e WHERE e.PlantingId = p.PlantingId) AS TotalLiters
            FROM Plantings p JOIN Crops c ON c.CropId = p.CropId LEFT JOIN Users u ON u.UserId = p.CreatedBy
            ORDER BY CASE p.Status WHEN 'ACTIVE' THEN 0 ELSE 1 END, p.CreatedAt DESC""")

    def start(self, p: Plant, note: Optional[str], user_id: int) -> int:
        with self.db.transaction() as cur:
            cur.execute("UPDATE Plantings SET Status = 'FINISHED', EndedAt = SYSDATETIME() WHERE Status = 'ACTIVE'")
            cur.execute("""INSERT INTO Plantings (CropId, PlantedDate, DailyQuotaLiters, MaxLitersPerWatering, Note, CreatedBy)
                           OUTPUT INSERTED.PlantingId VALUES (?, ?, ?, ?, ?, ?)""",
                        p.crop_id, p.planted_date, p.daily_quota_liters, p.max_liters_per_watering, note, user_id)
            return int(cur.fetchone()[0])

    def update_active(self, planted_date, quota: float, max_per: float) -> None:
        self.db.execute("""UPDATE Plantings SET PlantedDate = ?, DailyQuotaLiters = ?, MaxLitersPerWatering = ?
                           WHERE Status = 'ACTIVE'""", planted_date, quota, max_per)

    def finish_active(self) -> int:
        return self.db.execute("UPDATE Plantings SET Status = 'FINISHED', EndedAt = SYSDATETIME() WHERE Status = 'ACTIVE'")

    def set_auto(self, auto: bool) -> None:
        self.db.execute("UPDATE Plantings SET AutoMode = ? WHERE Status = 'ACTIVE'", int(auto))

    def quota_today(self) -> WaterQuota:
        r = self.db.query_one("SELECT LimitLiters, UsedLiters FROM vw_QuotaToday")
        return WaterQuota(r["LimitLiters"], r["UsedLiters"]) if r else WaterQuota(0, 0)


class DeviceRepository:
    def __init__(self, db: Database):
        self.db = db

    def touch(self, code: str, pump_on: Optional[bool] = None) -> None:
        if self.db.execute("UPDATE DeviceStatus SET DeviceCode = ?, LastSeen = SYSDATETIME() WHERE Id = 1", code) == 0:
            self.db.execute("INSERT INTO DeviceStatus (Id, DeviceCode, LastSeen) VALUES (1, ?, SYSDATETIME())", code)
        if pump_on is not None:
            self.db.execute("UPDATE DeviceStatus SET PumpIsOn = ? WHERE Id = 1", int(pump_on))

    def status(self) -> Optional[dict]:
        return self.db.query_one("SELECT * FROM DeviceStatus WHERE Id = 1")


class ReadingRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, soil_raw, soil, temp, hum) -> None:
        self.db.execute("""INSERT INTO SensorReadings (SoilRaw, SoilMoisture, AirTemp, AirHumidity)
                           VALUES (?, ?, ?, ?)""", soil_raw, soil, temp, hum)

    def latest(self) -> Optional[dict]:
        return self.db.query_one("SELECT TOP 1 * FROM SensorReadings ORDER BY ReadingId DESC")

    def recent(self, limit: int) -> list[dict]:
        rows = self.db.query("SELECT TOP (?) * FROM SensorReadings ORDER BY ReadingId DESC", limit)
        return list(reversed(rows))


class RecommendationRepository:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _entity(r: dict) -> Recommendation:
        return Recommendation(
            valid_from=r["ValidFrom"], valid_to=r["ValidTo"], trigger_below=r["TriggerBelow"],
            moisture_at_create=r["MoistureAtCreate"], duration_sec=r["DurationSec"],
            volume_liters=r["VolumeLiters"], reason=r["Reason"], scope_note=r["ScopeNote"],
            stage_name=r["StageName"], stage_id=r["StageId"], status=r["Status"], rec_id=r["RecId"],
            target_moisture=r.get("TargetMoisture"))

    def expire_old(self) -> None:
        self.db.query("EXEC sp_ExpireRecommendations")

    def get(self, rec_id: int) -> Optional[Recommendation]:
        r = self.db.query_one("SELECT * FROM Recommendations WHERE RecId = ?", rec_id)
        return self._entity(r) if r else None

    def open_one(self, planting_id: int) -> Optional[Recommendation]:
        r = self.db.query_one("""SELECT TOP 1 * FROM Recommendations
                                 WHERE PlantingId = ? AND Status IN ('PROPOSED', 'OVERRIDDEN')
                                 ORDER BY RecId DESC""", planting_id)
        return self._entity(r) if r else None

    def list(self, planting_id: int, limit: int = 50) -> list[dict]:
        return self.db.query("""
            SELECT TOP (?) r.*, uc.FullName AS CreatedByName, ua.FullName AS AppliedByName,
                   (SELECT COUNT(*) FROM RecommendationOverrides o WHERE o.RecId = r.RecId) AS OverrideCount
            FROM Recommendations r
            LEFT JOIN Users uc ON uc.UserId = r.CreatedBy
            LEFT JOIN Users ua ON ua.UserId = r.AppliedBy
            WHERE r.PlantingId = ? ORDER BY r.RecId DESC""", limit, planting_id)

    def add(self, rec: Recommendation, planting_id: int, created_by: Optional[int]) -> int:
        with self.db.transaction() as cur:
            cur.execute("""
                INSERT INTO Recommendations (PlantingId, CreatedBy, StageId, StageName, ValidFrom, ValidTo, TriggerBelow,
                                             MoistureAtCreate, TargetMoisture, DurationSec, VolumeLiters, Reason, ScopeNote, Status)
                OUTPUT INSERTED.RecId VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        planting_id, created_by, rec.stage_id, rec.stage_name, rec.valid_from, rec.valid_to,
                        rec.trigger_below, rec.moisture_at_create, rec.target_moisture, rec.duration_sec,
                        rec.volume_liters, rec.reason, rec.scope_note, rec.status)
            rec.rec_id = int(cur.fetchone()[0])
        return rec.rec_id

    @staticmethod
    def save_state(cur, rec: Recommendation) -> None:
        cur.execute("""UPDATE Recommendations SET DurationSec = ?, VolumeLiters = ?, ValidTo = ?, ScopeNote = ?, Status = ?
                       WHERE RecId = ?""", rec.duration_sec, rec.volume_liters, rec.valid_to, rec.scope_note,
                    rec.status, rec.rec_id)

    @staticmethod
    def mark_applied(cur, rec_id: int, user_id: Optional[int]) -> None:
        cur.execute("UPDATE Recommendations SET AppliedBy = ?, AppliedAt = SYSDATETIME() WHERE RecId = ?", user_id, rec_id)

    @staticmethod
    def add_override(cur, rec_id: int, user_id: int, o: OverrideRecord) -> None:
        cur.execute("""INSERT INTO RecommendationOverrides
                         (RecId, UserId, Action, OldDurationSec, NewDurationSec, OldValidTo, NewValidTo, Reason)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    rec_id, user_id, o.action, o.old_duration, o.new_duration, o.old_valid_to, o.new_valid_to, o.reason)

    def overrides(self, rec_id: int) -> list[dict]:
        return self.db.query("SELECT * FROM vw_OverrideHistory WHERE RecId = ? ORDER BY CreatedAt DESC", rec_id)


class PumpRequestRepository:

    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _entity(r: dict) -> PumpRequest:
        return PumpRequest(r["Liters"], r["DurationSec"], r["Reason"], r["RequestedBy"], r["Status"],
                           r["ReviewedBy"], r["ReviewNote"], r["RequestId"])

    def get(self, request_id: int) -> Optional[PumpRequest]:
        r = self.db.query_one("SELECT * FROM PumpRequests WHERE RequestId = ?", request_id)
        return self._entity(r) if r else None

    def add(self, req: PumpRequest, planting_id: int) -> int:
        with self.db.transaction() as cur:
            cur.execute("""INSERT INTO PumpRequests (PlantingId, Liters, DurationSec, Reason, RequestedBy)
                           OUTPUT INSERTED.RequestId VALUES (?, ?, ?, ?, ?)""",
                        planting_id, req.liters, req.duration_sec, req.reason, req.requested_by)
            req.request_id = int(cur.fetchone()[0])
        return req.request_id

    @staticmethod
    def save_review(cur, req: PumpRequest) -> None:
        cur.execute("""UPDATE PumpRequests SET Status = ?, ReviewedBy = ?, ReviewedAt = SYSDATETIME(), ReviewNote = ?
                       WHERE RequestId = ?""", req.status, req.reviewed_by, req.review_note, req.request_id)

    def list(self, planting_id: int, limit: int = 50) -> list[dict]:
        return self.db.query("""
            SELECT TOP (?) r.*, ur.FullName AS RequestedByName, uv.FullName AS ReviewedByName,
                   c.Status AS CommandStatus, c.PumpedSec
            FROM PumpRequests r
            JOIN Users ur ON ur.UserId = r.RequestedBy
            LEFT JOIN Users uv ON uv.UserId = r.ReviewedBy
            LEFT JOIN PumpCommands c ON c.RequestId = r.RequestId AND c.Action = 'ON'
            WHERE r.PlantingId = ? ORDER BY r.RequestId DESC""", limit, planting_id)

    def pending_count(self, planting_id: int) -> int:
        return self.db.query_one("SELECT COUNT(*) AS n FROM PumpRequests WHERE PlantingId = ? AND Status = 'PENDING'",
                                 planting_id)["n"]


class PumpRepository:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def queue(cur, action: str, duration: int, source: str, issued_by: Optional[int], rec_id=None,
              request_id=None, stop_at=None, pulse_sec=None, soak_sec=None) -> None:
        cur.execute("UPDATE PumpCommands SET Status = 'CANCELLED' WHERE Status = 'PENDING'")
        cur.execute("""INSERT INTO PumpCommands (Action, DurationSec, StopAtMoisture, PulseSec, SoakSec, Source,
                                                 RecId, RequestId, IssuedBy)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    action, duration, stop_at, pulse_sec, soak_sec, source, rec_id, request_id, issued_by)

    def take_pending(self) -> Optional[dict]:
        with self.db.transaction() as cur:
            cur.execute("""UPDATE TOP (1) PumpCommands
                           SET Status = 'DELIVERED', DeliveredAt = SYSDATETIME()
                           OUTPUT INSERTED.CommandId, INSERTED.Action, INSERTED.DurationSec,
                                  INSERTED.StopAtMoisture, INSERTED.PulseSec, INSERTED.SoakSec
                           WHERE Status = 'PENDING'""")
            row = cur.fetchone()
            if not row:
                return None
            return {"command_id": row[0], "action": row[1], "duration_sec": row[2],
                    "stop_at": float(row[3]) if row[3] is not None else -1,
                    "pulse_sec": row[4] or row[2], "soak_sec": row[5] or 0}

    def get(self, command_id: int) -> Optional[dict]:
        return self.db.query_one("SELECT * FROM PumpCommands WHERE CommandId = ?", command_id)

    def in_progress(self) -> bool:
        r = self.db.query_one("""SELECT COUNT(*) AS n FROM PumpCommands
                                 WHERE Action = 'ON' AND Status IN ('PENDING', 'DELIVERED')
                                   AND CreatedAt > DATEADD(MINUTE, -10, SYSDATETIME())""")
        return r["n"] > 0

    def active_command(self) -> Optional[dict]:
        return self.db.query_one("""
            SELECT TOP 1 c.CommandId, c.DurationSec, c.StopAtMoisture, c.Source, c.RecId, c.RequestId,
                   c.CreatedAt, c.DeliveredAt, c.Status, u.FullName AS IssuedByName
            FROM PumpCommands c LEFT JOIN Users u ON u.UserId = c.IssuedBy
            WHERE c.Action = 'ON' AND c.Status IN ('PENDING', 'DELIVERED')
              AND c.CreatedAt > DATEADD(MINUTE, -10, SYSDATETIME())
            ORDER BY c.CommandId DESC""")

    @staticmethod
    def release_running(cur) -> None:
        cur.execute("""UPDATE PumpCommands SET Status = 'CANCELLED'
                       WHERE Action = 'ON' AND Status IN ('PENDING', 'DELIVERED')""")

    @staticmethod
    def finish(cur, command_id: int, pumped_sec: int, final_moisture, reason: str) -> None:
        cur.execute("""UPDATE PumpCommands SET Status = 'DONE', FinishedAt = SYSDATETIME(),
                              PumpedSec = ?, FinalMoisture = ?, StopReason = ?
                       WHERE CommandId = ?""", pumped_sec, final_moisture, reason, command_id)

    @staticmethod
    def log_event(cur, planting_id, cmd: dict, duration: int, liters: float, final_moisture, reason: str) -> None:
        cur.execute("""INSERT INTO IrrigationEvents
                         (PlantingId, CommandId, RecId, RequestId, IssuedBy, DurationSec, EstimatedLiters,
                          FinalMoisture, StopReason, Source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    planting_id, cmd["CommandId"], cmd["RecId"], cmd["RequestId"], cmd["IssuedBy"],
                    duration, liters, final_moisture, reason, cmd["Source"])

    def last_event_time(self):
        r = self.db.query_one("SELECT TOP 1 StartedAt FROM IrrigationEvents ORDER BY EventId DESC")
        return r["StartedAt"] if r else None

    def events(self, limit: int = 100) -> list[dict]:
        return self.db.query("SELECT TOP (?) * FROM vw_IrrigationLog ORDER BY EventId DESC", limit)


class SettingsRepository:

    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str) -> Optional[str]:
        r = self.db.query_one("SELECT SettingValue FROM AppSettings WHERE SettingKey = ?", key)
        return r["SettingValue"] if r else None

    def set(self, key: str, value: str, user_id: int) -> None:
        if self.db.execute("UPDATE AppSettings SET SettingValue = ?, UpdatedBy = ?, UpdatedAt = SYSDATETIME() "
                           "WHERE SettingKey = ?", value, user_id, key) == 0:
            self.db.execute("INSERT INTO AppSettings (SettingKey, SettingValue, UpdatedBy) VALUES (?, ?, ?)",
                            key, value, user_id)
