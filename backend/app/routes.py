from __future__ import annotations

import json

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from .database import db
from .permissions import ROLES, has, permissions_of, tree_for
from .repositories import SettingsRepository
from .services import AuthService, IrrigationService

auth = AuthService(db)
svc = IrrigationService(db)
settings_repo = SettingsRepository(db)


def get_token(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Chưa đăng nhập")
    return authorization[7:].strip()


def current_user(token: str = Depends(get_token)) -> dict:
    user = auth.user_of(token)
    if not user:
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn")
    return user


def need(perm: str):
    def checker(user: dict = Depends(current_user)) -> dict:
        if not has(user["role"], perm):
            raise HTTPException(403, f"Vai trò '{ROLES.get(user['role'], user['role'])}' không có quyền này")
        return user
    return checker


public = APIRouter(prefix="/api")
private = APIRouter(prefix="/api", dependencies=[Depends(current_user)])


class RegisterIn(BaseModel):
    username: str
    full_name: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


class UserIn(RegisterIn):
    role: str = "VIEWER"


class UserUpdateIn(BaseModel):
    full_name: str
    role: str
    new_password: Optional[str] = None


class CropIn(BaseModel):
    name: str
    description: Optional[str] = None


class PlantingIn(BaseModel):
    crop_id: int
    planted_date: date
    daily_quota_liters: float = Field(ge=0)
    max_liters_per_watering: float = Field(gt=0)
    note: Optional[str] = None


class PlantingUpdateIn(BaseModel):
    planted_date: date
    daily_quota_liters: float = Field(ge=0)
    max_liters_per_watering: float = Field(gt=0)


class StageIn(BaseModel):
    name: str
    duration_days: int = Field(gt=0)
    moisture_min: float = Field(ge=0, le=100)
    moisture_max: float = Field(ge=0, le=100)


class ModeIn(BaseModel):
    auto_mode: bool


class PumpRequestIn(BaseModel):
    liters: float = Field(gt=0, le=2)
    reason: str


class ReviewIn(BaseModel):
    note: Optional[str] = None


class OverrideIn(BaseModel):
    volume_liters: float = Field(ge=0)
    reason: str
    valid_to: Optional[datetime] = None


class RejectIn(BaseModel):
    reason: str


class PumpDoneIn(BaseModel):
    device_code: str
    command_id: int
    pumped_sec: int = Field(ge=0)
    final_moisture: Optional[float] = None
    reason: str = ""


class BackgroundIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dim: int = Field(ge=0, le=85)


class ReadingIn(BaseModel):
    device_code: str
    soil_raw: Optional[int] = None
    soil_moisture: float = Field(ge=0, le=100)
    air_temp: Optional[float] = None
    air_humidity: Optional[float] = None


@public.get("/health", tags=["Hệ thống"])
def health():
    ok = db.ping()
    return {"database": ok, "has_user": auth.has_any_user() if ok else None}


@public.post("/auth/register", tags=["Tài khoản"])
def register(body: RegisterIn):
    auth.register_first_admin(body.username, body.full_name, body.password)
    return {"ok": True}


@public.post("/auth/login", tags=["Tài khoản"])
def login(body: LoginIn):
    token, user = auth.login(body.username, body.password)
    return {"token": token, "user": user}


@public.post("/auth/logout", tags=["Tài khoản"])
def logout(token: str = Depends(get_token)):
    auth.logout(token)
    return {"ok": True}


@private.get("/auth/me", tags=["Tài khoản"])
def me(user: dict = Depends(current_user)):
    return {**user, "role_name": ROLES.get(user["role"]), "permissions": permissions_of(user["role"])}


@private.get("/roles", tags=["Tài khoản"])
def roles(user: dict = Depends(current_user)):
    return {"tree": tree_for(user["role"])}


@private.get("/users", tags=["Tài khoản"])
def users(_: dict = Depends(need("user.manage"))):
    return auth.users.list()


@private.post("/users", tags=["Tài khoản"])
def add_user(body: UserIn, _: dict = Depends(need("user.manage"))):
    auth.create_user(body.username, body.full_name, body.password, body.role)
    return {"ok": True}


@private.put("/users/{user_id}", tags=["Tài khoản"])
def update_user(user_id: int, body: UserUpdateIn, actor: dict = Depends(need("user.manage"))):
    auth.update_user(actor["user_id"], user_id, body.full_name, body.role, body.new_password or None)
    return {"ok": True}


@private.delete("/users/{user_id}", tags=["Tài khoản"])
def delete_user(user_id: int, actor: dict = Depends(need("user.manage"))):
    return auth.delete_user(actor["user_id"], user_id)


@private.post("/users/{user_id}/activate", tags=["Tài khoản"])
def activate_user(user_id: int, _: dict = Depends(need("user.manage"))):
    auth.activate_user(user_id)
    return {"ok": True}


BG_DEFAULTS = {
    "login": {"name": "dang-nhap.jpg", "dim": 35},
    "app":   {"name": "background.jpg", "dim": 45},
}


@public.get("/settings/backgrounds", tags=["Hệ thống"])
def get_backgrounds():
    out = {}
    for scope, default in BG_DEFAULTS.items():
        raw = settings_repo.get(f"background.{scope}")
        out[scope] = json.loads(raw) if raw else default
    return out


@private.put("/settings/backgrounds/{scope}", tags=["Hệ thống"])
def set_background(scope: str, body: BackgroundIn, user: dict = Depends(need("settings.edit"))):
    if scope not in BG_DEFAULTS:
        raise HTTPException(400, "scope phải là 'login' hoặc 'app'")
    settings_repo.set(f"background.{scope}", json.dumps(body.model_dump(), ensure_ascii=False), user["user_id"])
    return {"ok": True}


@public.post("/device/readings", tags=["ESP32"])
def device_reading(body: ReadingIn):
    return svc.ingest(body.device_code, body.soil_raw, body.soil_moisture, body.air_temp, body.air_humidity)


@public.get("/device/command", tags=["ESP32"])
def device_command(device_code: str, pump_on: Optional[bool] = None):
    return svc.next_command(device_code, pump_on)


@public.post("/device/pump-done", tags=["ESP32"])
def device_pump_done(body: PumpDoneIn):
    return svc.pump_done(body.command_id, body.pumped_sec, body.final_moisture, body.reason[:200])


@private.get("/crops", tags=["Cây trồng & mùa vụ"])
def crops():
    return svc.crops.list()


@private.post("/crops", tags=["Cây trồng & mùa vụ"])
def add_crop(body: CropIn, user: dict = Depends(need("crop.edit"))):
    return {"crop_id": svc.add_crop(body.name, body.description, user["user_id"])}


@private.put("/crops/{crop_id}", tags=["Cây trồng & mùa vụ"])
def update_crop(crop_id: int, body: CropIn, _: dict = Depends(need("crop.edit"))):
    svc.update_crop(crop_id, body.name, body.description)
    return {"ok": True}


@private.delete("/crops/{crop_id}", tags=["Cây trồng & mùa vụ"])
def delete_crop(crop_id: int, _: dict = Depends(need("crop.edit"))):
    svc.delete_crop(crop_id)
    return {"ok": True}


@private.put("/crops/{crop_id}/stages", tags=["Cây trồng & mùa vụ"])
def save_stages(crop_id: int, body: list[StageIn], _: dict = Depends(need("crop.edit"))):
    svc.save_stages(crop_id, [x.model_dump() for x in body])
    return {"ok": True}


@private.get("/plant", tags=["Cây trồng & mùa vụ"])
def plant():
    return svc.plant_info()


@private.get("/plantings", tags=["Cây trồng & mùa vụ"])
def plantings():
    return svc.plantings.list()


@private.post("/plantings", tags=["Cây trồng & mùa vụ"])
def start_planting(body: PlantingIn, user: dict = Depends(need("planting.edit"))):
    pid = svc.start_planting(body.crop_id, body.planted_date, body.daily_quota_liters,
                             body.max_liters_per_watering, body.note, user["user_id"])
    return {"planting_id": pid}


@private.put("/plantings/active", tags=["Cây trồng & mùa vụ"])
def update_planting(body: PlantingUpdateIn, _: dict = Depends(need("planting.edit"))):
    svc.update_planting(body.planted_date, body.daily_quota_liters, body.max_liters_per_watering)
    return svc.plant_info()


@private.post("/plantings/active/finish", tags=["Cây trồng & mùa vụ"])
def finish_planting(_: dict = Depends(need("planting.edit"))):
    svc.finish_planting()
    return {"ok": True}


@private.post("/plant/mode", tags=["Cây trồng & mùa vụ"])
def set_mode(body: ModeIn, _: dict = Depends(need("auto.toggle"))):
    svc.set_auto(body.auto_mode)
    return {"auto_mode": body.auto_mode}


@private.get("/dashboard", tags=["Theo dõi"])
def dashboard():
    return svc.dashboard()


@private.get("/readings", tags=["Theo dõi"])
def readings(limit: int = Query(60, ge=1, le=1000)):
    return svc.readings.recent(limit)


@private.get("/events", tags=["Theo dõi"])
def events():
    return svc.pumps.events()


@private.get("/pump-requests", tags=["Bơm ngoài đề xuất"])
def pump_requests():
    p = svc.plantings.active()
    return svc.requests.list(p.planting_id) if p else []


@private.post("/pump-requests", tags=["Bơm ngoài đề xuất"])
def request_pump(body: PumpRequestIn, user: dict = Depends(need("pump.request"))):
    return svc.request_pump(body.liters, body.reason, user)


@private.post("/pump-requests/{request_id}/approve", tags=["Bơm ngoài đề xuất"])
def approve_request(request_id: int, body: ReviewIn, user: dict = Depends(need("pump.approve"))):
    return svc.approve_request(request_id, user["user_id"], body.note)


@private.post("/pump-requests/{request_id}/reject", tags=["Bơm ngoài đề xuất"])
def reject_request(request_id: int, body: ReviewIn, user: dict = Depends(need("pump.approve"))):
    return svc.reject_request(request_id, user["user_id"], body.note or "")


@private.post("/pump/stop", tags=["Bơm ngoài đề xuất"])
def stop_pump(user: dict = Depends(need("pump.stop"))):
    return svc.stop_pump(user["user_id"])


@private.get("/recommendations", tags=["Đề xuất tưới"])
def list_recs():
    svc.recs.expire_old()
    p = svc.plantings.active()
    return svc.recs.list(p.planting_id) if p else []


@private.post("/recommendations", tags=["Đề xuất tưới"])
def generate(user: dict = Depends(need("rec.generate"))):
    return svc.generate(user["user_id"])


@private.post("/recommendations/{rec_id}/apply", tags=["Đề xuất tưới"])
def apply(rec_id: int, user: dict = Depends(need("rec.apply"))):
    return svc.apply(rec_id, user["user_id"])


@private.post("/recommendations/{rec_id}/override", tags=["Đề xuất tưới"])
def override(rec_id: int, body: OverrideIn, user: dict = Depends(need("rec.override"))):
    return svc.override(rec_id, body.volume_liters, body.reason, body.valid_to, user["user_id"])


@private.post("/recommendations/{rec_id}/reject", tags=["Đề xuất tưới"])
def reject(rec_id: int, body: RejectIn, user: dict = Depends(need("rec.override"))):
    return svc.reject(rec_id, body.reason, user["user_id"])


@private.get("/recommendations/{rec_id}/overrides", tags=["Đề xuất tưới"])
def overrides(rec_id: int):
    return svc.recs.overrides(rec_id)
