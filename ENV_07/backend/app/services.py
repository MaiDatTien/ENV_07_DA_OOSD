from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from .config import settings
from .database import Database
from .domain import (DomainError, Plant, PlantStage, PumpRequest, RecommendationEngine, SensorReading)
from .permissions import ROLES
from .permissions import has
from .repositories import (CropRepository, DeviceRepository, PlantingRepository, PumpRepository,
                           PumpRequestRepository, ReadingRepository, RecommendationRepository,
                           SessionRepository, UserRepository)
from .security import hash_password, new_salt, new_token, verify_password


class NotFound(Exception):
    pass


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, db: Database):
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)

    def has_any_user(self) -> bool:
        return self.users.count() > 0

    def register_first_admin(self, username: str, full_name: str, password: str) -> None:
        if self.has_any_user():
            raise DomainError("Đã có tài khoản quản trị, hãy đăng nhập")
        self.create_user(username, full_name, password, "ADMIN")

    @staticmethod
    def _check_name(full_name: str) -> str:
        full_name = (full_name or "").strip()
        if not full_name:
            raise DomainError("Chưa nhập họ tên")
        if len(full_name) > 100:
            raise DomainError("Họ tên tối đa 100 ký tự")
        return full_name

    @staticmethod
    def _check_password(password: str) -> None:
        if len(password or "") < 6:
            raise DomainError("Mật khẩu ít nhất 6 ký tự")
        if len(password) > 100:
            raise DomainError("Mật khẩu tối đa 100 ký tự")

    @staticmethod
    def _check_role(role: str) -> None:
        if role not in ROLES:
            raise DomainError("Vai trò không hợp lệ")

    def create_user(self, username: str, full_name: str, password: str, role: str) -> None:
        username = (username or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.]{3,50}", username):
            raise DomainError("Tên đăng nhập 3 đến 50 ký tự, chỉ gồm chữ không dấu, số, dấu chấm hoặc gạch dưới")
        full_name = self._check_name(full_name)
        self._check_password(password)
        self._check_role(role)
        if self.users.by_username(username):
            raise DomainError("Tên đăng nhập đã tồn tại")
        salt = new_salt()
        self.users.add(username, full_name, salt, hash_password(salt, password), role)

    def _target(self, user_id: int) -> dict:
        u = self.users.get(user_id)
        if not u:
            raise NotFound("Không có tài khoản này")
        return u

    def _keep_one_admin(self, u: dict) -> None:
        if u["Role"] == "ADMIN" and u["IsActive"] and self.users.count_active_role("ADMIN") <= 1:
            raise DomainError("Phải còn ít nhất 1 Quản trị hệ thống đang hoạt động")

    def update_user(self, actor_id: int, user_id: int, full_name: str, role: str,
                    new_password: Optional[str] = None) -> None:
        u = self._target(user_id)
        full_name = self._check_name(full_name)
        self._check_role(role)
        if u["Role"] == "ADMIN" and role != "ADMIN":
            if user_id == actor_id:
                raise DomainError("Không tự hạ quyền quản trị của chính mình")
            self._keep_one_admin(u)
        self.users.update(user_id, full_name, role)
        if new_password:
            self._check_password(new_password)
            salt = new_salt()
            self.users.set_password(user_id, salt, hash_password(salt, new_password))

    def delete_user(self, actor_id: int, user_id: int) -> dict:
        u = self._target(user_id)
        if user_id == actor_id:
            raise DomainError("Không tự xóa tài khoản đang đăng nhập")
        self._keep_one_admin(u)
        used = self.users.history_count(user_id)
        if used > 0:
            self.users.set_active(user_id, False)
            return {"result": "locked",
                    "message": f"{u['Username']} đã có {used} thao tác trong nhật ký nên được KHÓA để giữ lưu vết"}
        self.users.delete(user_id)
        return {"result": "deleted", "message": f"Đã xóa tài khoản {u['Username']}"}

    def activate_user(self, user_id: int) -> None:
        self._target(user_id)
        self.users.set_active(user_id, True)

    def login(self, username: str, password: str) -> tuple[str, dict]:
        u = self.users.by_username(username.strip())
        if not u or not verify_password(u["Salt"], password, u["PasswordHash"]):
            raise AuthError("Sai tên đăng nhập hoặc mật khẩu")
        if not u["IsActive"]:
            raise AuthError("Tài khoản đã bị khóa, liên hệ Quản trị hệ thống")
        token = new_token()
        self.sessions.add(token, u["UserId"], datetime.now() + timedelta(hours=settings.SESSION_HOURS))
        return token, {"user_id": u["UserId"], "username": u["Username"],
                       "full_name": u["FullName"], "role": u["Role"]}

    def user_of(self, token: str) -> Optional[dict]:
        r = self.sessions.user_of(token)
        if not r:
            return None
        return {"user_id": r["UserId"], "username": r["Username"], "full_name": r["FullName"], "role": r["Role"]}

    def logout(self, token: str) -> None:
        self.sessions.remove(token)


class IrrigationService:
    def __init__(self, db: Database):
        self.db = db
        self.crops = CropRepository(db)
        self.plantings = PlantingRepository(db)
        self.devices = DeviceRepository(db)
        self.readings = ReadingRepository(db)
        self.recs = RecommendationRepository(db)
        self.requests = PumpRequestRepository(db)
        self.pumps = PumpRepository(db)
        self.engine = RecommendationEngine(settings.REC_VALID_HOURS, settings.MAX_PUMP_SEC)

    def _plant(self) -> Plant:
        p = self.plantings.active()
        if not p:
            raise NotFound("Chưa có mùa vụ nào đang chạy")
        return p

    def device_info(self) -> dict:
        dev = self.devices.status()
        if not dev:
            return {"connected": False, "never": True, "message": "ESP32 chưa từng kết nối"}
        age = (datetime.now() - dev["LastSeen"]).total_seconds()
        online = age <= settings.DEVICE_OFFLINE_SEC
        return {**dev, "connected": online, "never": False, "seconds_ago": int(age),
                "PumpIsOn": bool(dev["PumpIsOn"]) and online,
                "message": "Đang kết nối" if online else f"Mất kết nối từ {dev['LastSeen']:%H:%M %d/%m}"}

    def _require_device(self) -> None:
        info = self.device_info()
        if not info["connected"]:
            raise DomainError(f"Không thể bơm: {info['message']}. Kiểm tra nguồn và WiFi của ESP32.")

    @staticmethod
    def _check_crop(name: str, description: Optional[str]) -> tuple[str, Optional[str]]:
        name = (name or "").strip()
        description = (description or "").strip() or None
        if not name:
            raise DomainError("Chưa nhập tên loại cây")
        if len(name) > 100:
            raise DomainError("Tên loại cây tối đa 100 ký tự")
        if description and len(description) > 300:
            raise DomainError("Ghi chú loại cây tối đa 300 ký tự")
        return name, description

    def add_crop(self, name: str, description: Optional[str], user_id: int) -> int:
        name, description = self._check_crop(name, description)
        if self.crops.by_name(name):
            raise DomainError("Loại cây này đã có")
        return self.crops.add(name, description, user_id)

    def update_crop(self, crop_id: int, name: str, description: Optional[str]) -> None:
        if not self.crops.get(crop_id):
            raise NotFound("Không có loại cây này")
        name, description = self._check_crop(name, description)
        other = self.crops.by_name(name)
        if other and other["CropId"] != crop_id:
            raise DomainError("Tên loại cây bị trùng")
        self.crops.update(crop_id, name, description)

    def delete_crop(self, crop_id: int) -> None:
        crop = next((c for c in self.crops.list() if c["CropId"] == crop_id), None)
        if not crop:
            raise NotFound("Không có loại cây này")
        if crop["PlantingCount"] > 0:
            raise DomainError("Loại cây đã có mùa vụ, không xóa được (giữ lịch sử)")
        self.crops.delete(crop_id)

    def save_stages(self, crop_id: int, items: list[dict]) -> None:
        if not self.crops.get(crop_id):
            raise NotFound("Không có loại cây này")
        if not items:
            raise DomainError("Cần ít nhất 1 giai đoạn")
        stages = [PlantStage(i + 1, it["name"].strip(), it["duration_days"], it["moisture_min"], it["moisture_max"])
                  for i, it in enumerate(items)]
        for st in stages:
            st.validate()
        names = [st.name.lower() for st in stages]
        if len(set(names)) != len(names):
            raise DomainError("Tên các giai đoạn không được trùng nhau")
        self.crops.replace_stages(crop_id, stages)

    def plant_info(self) -> Optional[dict]:
        p = self.plantings.active()
        if not p:
            return None
        today = date.today()
        stage = p.current_stage(today)
        return {**{k: v for k, v in p.__dict__.items() if k != "stages"},
                "stages": [st.__dict__ for st in p.stages],
                "day": p.day_number(today),
                "current_stage": stage.__dict__ if stage else None}

    @staticmethod
    def _check_planting(p: Plant) -> None:
        p.validate()
        if p.planted_date > date.today():
            raise DomainError("Ngày trồng không được ở tương lai")
        if p.seconds_for(p.max_liters_per_watering) > settings.MAX_PUMP_SEC:
            raise DomainError(f"Mỗi lần tưới tối đa {p.liters_for(settings.MAX_PUMP_SEC):g} lít "
                              f"({settings.MAX_PUMP_SEC} giây bơm)")

    def start_planting(self, crop_id: int, planted_date: date, quota: float, max_per: float,
                       note: Optional[str], user_id: int) -> int:
        crop = self.crops.get(crop_id)
        if not crop:
            raise NotFound("Không có loại cây này")
        if not self.crops.stages(crop_id):
            raise DomainError(f"Loại cây '{crop['Name']}' chưa có lịch giai đoạn, hãy nhập trước")
        if self.pumps.in_progress():
            raise DomainError("Đang có lần tưới chưa xong, dừng bơm trước khi đổi mùa vụ")
        p = Plant(crop["Name"], planted_date, quota, max_per, settings.PUMP_FLOW_LPM, crop_id=crop_id)
        self._check_planting(p)
        note = (note or "").strip() or None
        if note and len(note) > 300:
            raise DomainError("Ghi chú mùa vụ tối đa 300 ký tự")
        return self.plantings.start(p, note, user_id)

    def update_planting(self, planted_date: date, quota: float, max_per: float) -> None:
        cur = self._plant()
        p = Plant(cur.name, planted_date, quota, max_per, settings.PUMP_FLOW_LPM)
        self._check_planting(p)
        self.plantings.update_active(planted_date, quota, max_per)

    def finish_planting(self) -> None:
        self._plant()
        if self.pumps.in_progress():
            raise DomainError("Đang có lần tưới chưa xong, dừng bơm trước")
        self.plantings.finish_active()

    def set_auto(self, auto: bool) -> None:
        self._plant()
        self.plantings.set_auto(auto)

    def dashboard(self) -> dict:
        self.recs.expire_old()
        plant = self.plantings.active()
        q = self.plantings.quota_today()
        open_rec = self.recs.open_one(plant.planting_id) if plant else None
        return {
            "plant": self.plant_info(),
            "device": self.device_info(),
            "latest": self.readings.latest(),
            "quota": {"limit": q.limit_liters, "used": q.used_liters, "remaining": q.remaining},
            "open_recommendation": open_rec and open_rec.__dict__,
            "active_command": self.pumps.active_command(),
            "pending_requests": self.requests.pending_count(plant.planting_id) if plant else 0,
        }

    def ingest(self, code: str, soil_raw, soil, temp, hum) -> dict:
        self.devices.touch(code)
        self.readings.add(soil_raw, soil, temp, hum)
        plant = self.plantings.active()
        if plant and plant.auto_mode:
            return {"saved": True, "auto": self._auto_cycle(plant, SensorReading(soil, temp, hum), soil_raw)}
        return {"saved": True}

    def _auto_cycle(self, plant: Plant, reading: SensorReading, soil_raw: Optional[int]) -> str:
        now = datetime.now()
        if soil_raw is not None and (soil_raw <= settings.SOIL_RAW_MIN or soil_raw >= settings.SOIL_RAW_MAX):
            return f"Cảm biến đất báo số bất thường (ADC {soil_raw}), không tự tưới"
        self.recs.expire_old()
        if self.pumps.in_progress():
            return "Đang có lần tưới chưa xong"
        last = self.pumps.last_event_time()
        if last is not None:
            wait = timedelta(minutes=settings.SOAK_MINUTES) - (now - last)
            if wait.total_seconds() > 0:
                return f"Vừa tưới lúc {last:%H:%M}, chờ nước thấm thêm {int(wait.total_seconds() // 60) + 1} phút"

        rec = self.recs.open_one(plant.planting_id)
        if rec is None:
            res = self.generate(None, reading)
            if not res["created"]:
                return res["message"]
            rec = self.recs.get(res["recommendation"]["rec_id"])
        if rec.status == "OVERRIDDEN":
            return f"Đề xuất #{rec.rec_id} đã được ghi đè, chờ người dùng bấm Áp dụng"
        ok, why = rec.check_scope(now, reading.soil_moisture)
        if not ok:
            return why
        self.apply(rec.rec_id, user_id=None, source="AUTO")
        return f"Đã tự tưới theo đề xuất #{rec.rec_id}"

    def next_command(self, code: str, pump_on: Optional[bool]) -> dict:
        self.devices.touch(code, pump_on)
        return self.pumps.take_pending() or {"action": "NONE", "duration_sec": 0}

    def pump_done(self, command_id: int, pumped_sec: int, final_moisture, reason: str) -> dict:
        cmd = self.pumps.get(command_id)
        if not cmd:
            raise NotFound(f"Không có lệnh bơm #{command_id}")
        if cmd["Status"] == "DONE":
            return {"ok": True, "duplicate": True}
        plant = self.plantings.active()
        pumped_sec = max(0, int(pumped_sec))
        liters = round(pumped_sec / 60 * settings.PUMP_FLOW_LPM, 2)
        with self.db.transaction() as cur:
            self.pumps.finish(cur, command_id, pumped_sec, final_moisture, reason)
            if pumped_sec > 0:
                self.pumps.log_event(cur, plant and plant.planting_id, cmd, pumped_sec, liters, final_moisture, reason)
        return {"ok": True, "liters": liters}

    def generate(self, user_id: Optional[int], reading: Optional[SensorReading] = None) -> dict:
        plant = self._plant()
        self.recs.expire_old()
        latest = self.readings.latest()
        if reading is None:
            if not latest:
                raise DomainError("Chưa có số đo nào từ ESP32")
            reading = SensorReading(latest["SoilMoisture"], latest["AirTemp"], latest["AirHumidity"])
        used = {"soil": reading.soil_moisture, "air_temp": reading.air_temp,
                "air_humidity": reading.air_humidity, "read_at": latest and latest["ReadAt"]}

        opened = self.recs.open_one(plant.planting_id)
        if opened:
            return {"created": False, "existing": True, "reading": used, "recommendation": opened.__dict__,
                    "message": f"Đang có đề xuất #{opened.rec_id} chờ xử lý. Hãy áp dụng, ghi đè hoặc từ chối trước."}

        res = self.engine.propose(plant, reading, self.plantings.quota_today(), datetime.now())
        if res.recommendation:
            self.recs.add(res.recommendation, plant.planting_id, user_id)
        return {"created": res.recommendation is not None, "existing": False, "reading": used,
                "message": res.message, "recommendation": res.recommendation and res.recommendation.__dict__}

    def _rec(self, rec_id: int):
        rec = self.recs.get(rec_id)
        if not rec:
            raise NotFound(f"Không có đề xuất #{rec_id}")
        return rec

    def apply(self, rec_id: int, user_id: Optional[int], source: str = "RECOMMENDATION") -> dict:
        self._plant()
        rec = self._rec(rec_id)
        self._require_device()
        if self.pumps.in_progress():
            raise DomainError("Đang có lần tưới chưa xong")
        quota = self.plantings.quota_today()
        if not quota.allows(rec.volume_liters):
            raise DomainError(f"Vượt hạn mức: còn {quota.remaining:.2f} L, đề xuất tối đa {rec.volume_liters:.2f} L")
        rec.apply(datetime.now())
        max_sec = min(rec.duration_sec, settings.MAX_PUMP_SEC)
        if max_sec <= 0:
            raise DomainError("Đề xuất có lượng nước 0 L, không cần bơm")
        with self.db.transaction() as cur:
            self.recs.save_state(cur, rec)
            self.recs.mark_applied(cur, rec.rec_id, user_id)
            self.pumps.queue(cur, "ON", max_sec, source, user_id, rec_id=rec.rec_id,
                             stop_at=rec.target_moisture, pulse_sec=settings.PULSE_SEC, soak_sec=settings.SOAK_SEC)
        return {"status": rec.status, "duration_sec": max_sec, "liters": rec.volume_liters,
                "target": rec.target_moisture}

    def override(self, rec_id: int, new_liters: float, reason: str,
                 new_valid_to: Optional[datetime], user_id: int) -> dict:
        plant = self._plant()
        rec = self._rec(rec_id)
        record = rec.override(new_liters, reason, plant, new_valid_to)
        with self.db.transaction() as cur:
            self.recs.save_state(cur, rec)
            self.recs.add_override(cur, rec.rec_id, user_id, record)
        return rec.__dict__

    def reject(self, rec_id: int, reason: str, user_id: int) -> dict:
        rec = self._rec(rec_id)
        record = rec.reject(reason)
        with self.db.transaction() as cur:
            self.recs.save_state(cur, rec)
            self.recs.add_override(cur, rec.rec_id, user_id, record)
        return rec.__dict__

    def request_pump(self, liters: float, reason: str, user: dict) -> dict:
        plant = self._plant()
        req = PumpRequest.create(liters, reason, user["user_id"], plant)
        can_approve = has(user["role"], "pump.approve")
        if can_approve:
            self._require_device()
        quota = self.plantings.quota_today()
        if not quota.allows(req.liters):
            raise DomainError(f"Bơm {req.liters:.2f} L sẽ vượt hạn mức (hôm nay còn {quota.remaining:.2f} L)")
        self.requests.add(req, plant.planting_id)
        if can_approve:
            return self.approve_request(req.request_id, user["user_id"], "Tự duyệt (có quyền duyệt)")
        return {"status": "PENDING", "request_id": req.request_id,
                "message": "Đã gửi yêu cầu, chờ Kỹ sư canh tác hoặc Quản trị duyệt"}

    def approve_request(self, request_id: int, reviewer_id: int, note: Optional[str]) -> dict:
        req = self.requests.get(request_id)
        if not req:
            raise NotFound("Không có yêu cầu này")
        self._require_device()
        if self.pumps.in_progress():
            raise DomainError("Đang có lần tưới chưa xong")
        quota = self.plantings.quota_today()
        if not quota.allows(req.liters):
            raise DomainError(f"Bơm {req.liters:.2f} L sẽ vượt hạn mức (hôm nay còn {quota.remaining:.2f} L)")
        req.approve(reviewer_id, note)
        with self.db.transaction() as cur:
            self.requests.save_review(cur, req)
            self.pumps.queue(cur, "ON", req.duration_sec, "MANUAL", reviewer_id, request_id=req.request_id)
        return {"status": "APPROVED", "request_id": req.request_id, "liters": req.liters,
                "duration_sec": req.duration_sec, "message": f"Đã duyệt, gửi lệnh bơm {req.liters:.2f} L ({req.duration_sec} giây)"}

    def reject_request(self, request_id: int, reviewer_id: int, note: str) -> dict:
        req = self.requests.get(request_id)
        if not req:
            raise NotFound("Không có yêu cầu này")
        req.reject(reviewer_id, note)
        with self.db.transaction() as cur:
            self.requests.save_review(cur, req)
        return {"status": "REJECTED", "request_id": req.request_id}

    def stop_pump(self, user_id: int) -> dict:
        with self.db.transaction() as cur:
            self.pumps.queue(cur, "OFF", 0, "MANUAL", user_id)
            self.pumps.release_running(cur)
        return {"action": "OFF"}
