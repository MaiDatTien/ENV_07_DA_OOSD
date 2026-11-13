import hashlib
from datetime import datetime, timedelta

import pytest

from app.domain import (DomainError, Plant, PlantStage, RecommendationEngine, SensorReading, WaterQuota)
from app.permissions import has, permissions_of, tree_for
from app.security import hash_password, verify_password

NOW = datetime(2026, 11, 12, 8, 0)


def make_plant(days_since_planting: int, max_per_watering: float = 1.5) -> Plant:
    return Plant("Cây thử", NOW.date() - timedelta(days=days_since_planting - 1),
                 daily_quota_liters=10.0, max_liters_per_watering=max_per_watering, pump_flow_lpm=2.0,
                 stages=[PlantStage(1, "GĐ1", 10, 55, 75, 1), PlantStage(2, "GĐ2", 20, 50, 70, 2)])


def test_liters_seconds_with_2_lpm():
    p = make_plant(1)
    assert p.seconds_for(2.0) == 60
    assert p.seconds_for(1.0) == 30
    assert p.seconds_for(0.5) == 15
    assert p.liters_for(60) == 2.0


def test_current_stage():
    assert make_plant(5).current_stage(NOW.date()).name == "GĐ1"
    assert make_plant(11).current_stage(NOW.date()).name == "GĐ2"
    assert make_plant(200).current_stage(NOW.date()).name == "GĐ2"


def test_no_water_when_soil_ok():
    res = RecommendationEngine().propose(make_plant(15), SensorReading(60), WaterQuota(10), NOW)
    assert res.recommendation is None and "Không cần tưới" in res.message


def test_recommendation_in_liters():
    rec = RecommendationEngine().propose(make_plant(15), SensorReading(40, 30, 60), WaterQuota(10), NOW).recommendation
    assert rec.target_moisture == 60
    assert rec.volume_liters == 1.5 and rec.duration_sec == 45
    assert rec.check_scope(NOW + timedelta(hours=1), 45)[0]
    assert not rec.check_scope(NOW + timedelta(hours=7), 45)[0]
    assert not rec.check_scope(NOW, 55)[0]


def test_humid_weather_reduces():
    rec = RecommendationEngine().propose(make_plant(15), SensorReading(40, 25, 90), WaterQuota(10), NOW).recommendation
    assert 1.3 <= rec.volume_liters < 1.5


def test_quota_cap():
    rec = RecommendationEngine().propose(make_plant(15), SensorReading(40), WaterQuota(10, 9.5), NOW).recommendation
    assert rec.volume_liters == 0.5 and rec.duration_sec == 15


def test_override_in_liters_needs_reason():
    p = make_plant(15)
    rec = RecommendationEngine().propose(p, SensorReading(40), WaterQuota(10), NOW).recommendation
    with pytest.raises(DomainError):
        rec.override(0.5, "ngắn", p)
    with pytest.raises(DomainError):
        rec.override(5.0, "Muốn tưới thật nhiều nước", p)
    rec.override(0.5, "Chiều nay dự báo có mưa rào", p)
    assert rec.status == "OVERRIDDEN" and rec.duration_sec == 15 and "đã ghi đè" in rec.scope_note


def test_reject_then_cannot_apply():
    rec = RecommendationEngine().propose(make_plant(15), SensorReading(40), WaterQuota(10), NOW).recommendation
    rec.reject("Vừa tưới tay xong sáng nay")
    with pytest.raises(DomainError):
        rec.apply(NOW)


def test_roles():
    assert has("MANAGER", "rec.override") and not has("FARMER", "rec.override")
    assert has("FARMER", "rec.apply") and not has("VIEWER", "rec.apply")
    assert "user.manage" in permissions_of("ADMIN") and permissions_of("VIEWER") == ["view.all"]
    assert len(tree_for("ADMIN")) == 4
    assert [b["role"] for b in tree_for("FARMER")] == ["FARMER"]


def test_password():
    h = hash_password("ABC", "123456")
    assert h == hashlib.sha256(b"ABC123456").hexdigest().upper()
    assert verify_password("ABC", "123456", h) and not verify_password("ABC", "sai", h)


def test_pump_request_needs_reason_and_max_2_liters():
    from app.domain import PumpRequest
    p = make_plant(5, max_per_watering=2.0)
    with pytest.raises(DomainError):
        PumpRequest.create(1.0, "khô", 7, p)
    with pytest.raises(DomainError):
        PumpRequest.create(3.0, "Lá héo, cần tưới thêm gấp", 7, p)
    req = PumpRequest.create(1.0, "Lá héo, cần tưới thêm gấp", 7, p)
    assert req.duration_sec == 30 and req.status == "PENDING"


def test_pump_request_review():
    from app.domain import PumpRequest
    p = make_plant(5)
    req = PumpRequest.create(0.5, "Đất mặt khô sau nắng gắt", 7, p)
    with pytest.raises(DomainError):
        req.reject(1, "không")
    req.approve(1, "Đồng ý")
    assert req.status == "APPROVED" and req.reviewed_by == 1
    with pytest.raises(DomainError):
        req.approve(1)
