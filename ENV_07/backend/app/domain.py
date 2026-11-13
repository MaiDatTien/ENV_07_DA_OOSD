from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

MIN_REASON_LENGTH = 10


class DomainError(ValueError):
    pass


@dataclass
class PlantStage:
    order: int
    name: str
    duration_days: int
    moisture_min: float
    moisture_max: float
    stage_id: Optional[int] = None

    def validate(self) -> None:
        if not self.name.strip():
            raise DomainError("Giai đoạn phải có tên")
        if self.duration_days <= 0:
            raise DomainError(f"Giai đoạn '{self.name}': số ngày phải > 0")
        if not (0 <= self.moisture_min < self.moisture_max <= 100):
            raise DomainError(f"Giai đoạn '{self.name}': độ ẩm phải 0 ≤ min < max ≤ 100")

    @property
    def target(self) -> float:
        return round((self.moisture_min + self.moisture_max) / 2, 1)

    def is_dry(self, soil: float) -> bool:
        return soil < self.moisture_min


@dataclass
class Plant:
    name: str
    planted_date: date
    daily_quota_liters: float
    max_liters_per_watering: float
    pump_flow_lpm: float = 2.0
    auto_mode: bool = False
    stages: list[PlantStage] = field(default_factory=list)
    planting_id: Optional[int] = None
    crop_id: Optional[int] = None

    def validate(self) -> None:
        if not self.name.strip():
            raise DomainError("Chưa chọn loại cây")
        if self.daily_quota_liters < 0:
            raise DomainError("Hạn mức nước không được âm")
        if self.max_liters_per_watering <= 0:
            raise DomainError("Lượng nước tối đa mỗi lần tưới phải > 0")
        if self.max_liters_per_watering > self.daily_quota_liters:
            raise DomainError("Tối đa mỗi lần tưới không được lớn hơn hạn mức cả ngày")

    def day_number(self, today: date) -> int:
        return (today - self.planted_date).days + 1

    def current_stage(self, today: date) -> Optional[PlantStage]:
        day = self.day_number(today)
        ordered = sorted(self.stages, key=lambda s: s.order)
        if day < 1 or not ordered:
            return None
        passed = 0
        for st in ordered:
            passed += st.duration_days
            if day <= passed:
                return st
        return ordered[-1]

    def liters_for(self, seconds: float) -> float:
        return round(seconds / 60 * self.pump_flow_lpm, 2)

    def seconds_for(self, liters: float) -> int:
        return max(0, int(round(liters / self.pump_flow_lpm * 60)))


@dataclass
class SensorReading:
    soil_moisture: float
    air_temp: Optional[float] = None
    air_humidity: Optional[float] = None


@dataclass
class WaterQuota:
    limit_liters: float
    used_liters: float = 0.0

    @property
    def remaining(self) -> float:
        return max(0.0, round(self.limit_liters - self.used_liters, 2))

    def allows(self, liters: float) -> bool:
        return liters <= self.remaining + 1e-9


@dataclass
class OverrideRecord:
    action: str
    old_duration: int
    new_duration: Optional[int]
    old_valid_to: datetime
    new_valid_to: Optional[datetime]
    reason: str


@dataclass
class Recommendation:
    valid_from: datetime
    valid_to: datetime
    trigger_below: float
    moisture_at_create: float
    duration_sec: int
    volume_liters: float
    reason: str
    scope_note: str
    stage_name: Optional[str] = None
    stage_id: Optional[int] = None
    status: str = "PROPOSED"
    rec_id: Optional[int] = None
    target_moisture: Optional[float] = None

    @property
    def is_open(self) -> bool:
        return self.status in ("PROPOSED", "OVERRIDDEN")

    def build_scope_note(self, overridden: bool = False) -> str:
        target = f"{self.target_moisture:.0f}%" if self.target_moisture is not None else "mục tiêu"
        note = (f"{self.valid_from:%H:%M %d/%m} → {self.valid_to:%H:%M %d/%m} · bắt đầu khi đất < "
                f"{self.trigger_below:.0f}% · dừng khi đất đạt {target} hoặc đủ "
                f"{self.volume_liters:.2f} L ({self.duration_sec} giây)")
        return note + (" · đã ghi đè" if overridden else "")

    def check_scope(self, now: datetime, soil: float) -> tuple[bool, str]:
        if now < self.valid_from:
            return False, "Chưa tới giờ áp dụng"
        if now > self.valid_to:
            return False, "Đã hết khung giờ áp dụng"
        if soil >= self.trigger_below:
            return False, f"Đất đã đủ ẩm ({soil:.1f}% ≥ {self.trigger_below:.0f}%)"
        return True, "Trong phạm vi áp dụng"

    def apply(self, now: datetime) -> None:
        if not self.is_open:
            raise DomainError(f"Đề xuất đang ở trạng thái {self.status}, không áp dụng được")
        if now > self.valid_to:
            self.status = "EXPIRED"
            raise DomainError("Đề xuất đã hết hạn")
        self.status = "APPLIED"

    @staticmethod
    def _check_reason(reason: str) -> str:
        reason = (reason or "").strip()
        if len(reason) < MIN_REASON_LENGTH:
            raise DomainError(f"Lý do phải có ít nhất {MIN_REASON_LENGTH} ký tự")
        return reason

    def override(self, new_liters: float, reason: str, plant: Plant,
                 new_valid_to: Optional[datetime] = None) -> OverrideRecord:
        reason = self._check_reason(reason)
        if not self.is_open:
            raise DomainError("Chỉ ghi đè được đề xuất đang chờ")
        if new_liters < 0:
            raise DomainError("Lượng nước không được âm")
        if new_liters > plant.max_liters_per_watering:
            raise DomainError(f"Không được vượt {plant.max_liters_per_watering:.2f} L mỗi lần tưới")
        if new_valid_to is not None and new_valid_to <= self.valid_from:
            raise DomainError("Giờ kết thúc mới phải sau giờ bắt đầu")
        new_duration = plant.seconds_for(new_liters)
        rec = OverrideRecord("ADJUST", self.duration_sec, new_duration, self.valid_to, new_valid_to, reason)
        self.volume_liters = round(new_liters, 2)
        self.duration_sec = new_duration
        if new_valid_to is not None:
            self.valid_to = new_valid_to
        self.status = "OVERRIDDEN"
        self.scope_note = self.build_scope_note(overridden=True)
        return rec

    def reject(self, reason: str) -> OverrideRecord:
        reason = self._check_reason(reason)
        if not self.is_open:
            raise DomainError("Chỉ từ chối được đề xuất đang chờ")
        self.status = "REJECTED"
        return OverrideRecord("REJECT", self.duration_sec, None, self.valid_to, None, reason)


MANUAL_MAX_SECONDS = 60


@dataclass
class PumpRequest:
    liters: float
    duration_sec: int
    reason: str
    requested_by: int
    status: str = "PENDING"
    reviewed_by: Optional[int] = None
    review_note: Optional[str] = None
    request_id: Optional[int] = None

    @classmethod
    def create(cls, liters: float, reason: str, requested_by: int, plant: Plant) -> "PumpRequest":
        reason = (reason or "").strip()
        if len(reason) < MIN_REASON_LENGTH:
            raise DomainError(f"Bơm ngoài đề xuất phải ghi lý do ít nhất {MIN_REASON_LENGTH} ký tự")
        if liters <= 0:
            raise DomainError("Số lít phải > 0")
        seconds = plant.seconds_for(liters)
        if seconds > MANUAL_MAX_SECONDS:
            raise DomainError(f"Bơm tay tối đa {plant.liters_for(MANUAL_MAX_SECONDS):.0f} lít ({MANUAL_MAX_SECONDS} giây) mỗi lần")
        if liters > plant.max_liters_per_watering:
            raise DomainError(f"Mùa vụ này mỗi lần tưới tối đa {plant.max_liters_per_watering:.2f} lít")
        return cls(plant.liters_for(seconds), max(1, seconds), reason, requested_by)

    def approve(self, reviewer_id: int, note: Optional[str] = None) -> None:
        if self.status != "PENDING":
            raise DomainError("Yêu cầu này đã được xử lý")
        self.status = "APPROVED"
        self.reviewed_by = reviewer_id
        self.review_note = (note or "").strip() or None

    def reject(self, reviewer_id: int, note: str) -> None:
        if self.status != "PENDING":
            raise DomainError("Yêu cầu này đã được xử lý")
        note = (note or "").strip()
        if len(note) < MIN_REASON_LENGTH:
            raise DomainError(f"Từ chối phải ghi lý do ít nhất {MIN_REASON_LENGTH} ký tự")
        self.status = "REJECTED"
        self.reviewed_by = reviewer_id
        self.review_note = note


class WeatherAdjuster:

    def factor(self, r: SensorReading) -> tuple[float, list[str]]:
        f, notes = 1.0, []
        if r.air_temp is not None and r.air_temp >= 33:
            notes.append(f"trời nóng {r.air_temp:.0f}°C")
        if r.air_humidity is not None:
            if r.air_humidity <= 40:
                notes.append(f"không khí khô {r.air_humidity:.0f}%")
            elif r.air_humidity >= 85:
                f = 0.9
                notes.append(f"không khí ẩm {r.air_humidity:.0f}% (giảm 10%)")
        return f, notes


@dataclass
class EngineResult:
    recommendation: Optional[Recommendation]
    message: str


class RecommendationEngine:

    def __init__(self, valid_hours: int = 6, max_pump_sec: int = 300,
                 weather: Optional[WeatherAdjuster] = None):
        self.valid_hours = valid_hours
        self.max_pump_sec = max_pump_sec
        self.weather = weather or WeatherAdjuster()

    def propose(self, plant: Plant, reading: SensorReading, quota: WaterQuota,
                now: datetime) -> EngineResult:
        stage = plant.current_stage(now.date())
        if stage is None:
            return EngineResult(None, "Chưa khai báo giai đoạn sinh trưởng hoặc chưa tới ngày trồng")

        soil = reading.soil_moisture
        if not stage.is_dry(soil):
            return EngineResult(None, f"Không cần tưới: đất đang {soil:.1f}%, giai đoạn '{stage.name}' "
                                      f"chỉ tưới khi đất dưới {stage.moisture_min:.0f}%")
        if quota.remaining <= 0:
            return EngineResult(None, f"Đất khô nhưng đã hết hạn mức hôm nay "
                                      f"({quota.used_liters:.2f}/{quota.limit_liters:.2f} L)")

        target = stage.target
        w, w_notes = self.weather.factor(reading)
        liters = plant.max_liters_per_watering * w
        notes = [f"Ngày {plant.day_number(now.date())}, giai đoạn '{stage.name}' cần "
                 f"{stage.moisture_min:.0f}–{stage.moisture_max:.0f}%, đất đang {soil:.1f}%",
                 f"tưới từng nhịp lên {target:.0f}% rồi dừng"] + w_notes

        caps = [(quota.remaining, "hạn mức còn lại hôm nay"),
                (plant.liters_for(self.max_pump_sec), f"an toàn {self.max_pump_sec} giây/lần")]
        for cap, label in caps:
            if liters > cap:
                liters = cap
                notes.append(f"giới hạn {cap:.2f} L ({label})")

        liters = round(liters, 2)
        seconds = max(1, plant.seconds_for(liters))
        liters = plant.liters_for(seconds)
        notes.append(f"tối đa {liters:.2f} L = {seconds} giây bơm (bơm {plant.pump_flow_lpm:g} L/phút)")

        valid_to = now + timedelta(hours=self.valid_hours)
        rec = Recommendation(
            valid_from=now, valid_to=valid_to, trigger_below=stage.moisture_min,
            moisture_at_create=soil, duration_sec=seconds, volume_liters=liters,
            reason="; ".join(notes), scope_note="",
            stage_name=stage.name, stage_id=stage.stage_id, target_moisture=target)
        rec.scope_note = rec.build_scope_note()
        return EngineResult(rec, "Đã tạo đề xuất")
