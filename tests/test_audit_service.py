"""test_audit_service.py - audit_log eklentisinin servis katmanı testleri (bellek içi DB).

Kim kullanır: pytest.
Nasıl bağlanır: temiz bir sqlite bellek veritabanı kurulur, AuditService olaylara
abone edilir ve olaylar kernel.events üzerinden yayınlanır.
"""

import pytest

from app.core.config import AppConfig
from app.core.db import create_all_tables, init_database
from app.core.kernel import Kernel
from plugins.audit_log import models  # noqa: F401  (tabloların Base'e kaydolması için)
from plugins.audit_log.service import AuditService


@pytest.fixture
def kernel() -> Kernel:
    """Temiz bir veritabanı ve kernel döndürür."""
    init_database("sqlite:///:memory:")
    create_all_tables()
    return Kernel(AppConfig())


@pytest.fixture
def audit(kernel) -> AuditService:
    """Olaylara abone edilmiş bir AuditService döndürür."""
    service = AuditService(kernel)
    service.subscribe_events()
    return service


def test_event_is_written(kernel, audit):
    """script.finished olayı bir satır üretir; success=False ise status error olur."""
    kernel.events.publish(
        "script.finished",
        {"username": "ali", "script_id": "backup", "success": True, "duration_ms": 120, "error_text": ""},
    )
    kernel.events.publish(
        "script.finished",
        {"username": "ali", "script_id": "backup", "success": False, "duration_ms": 5, "error_text": "boom"},
    )
    rows = audit.search(None, "")
    assert len(rows) == 2
    # En yeni kayıt önce gelir.
    assert rows[0]["status"] == "error"
    assert rows[0]["details"] == "boom"
    assert rows[0]["action"] == "script.run"
    assert rows[0]["target"] == "backup"
    assert rows[1]["status"] == "ok"
    assert rows[1]["duration_ms"] == 120


def test_auth_events(kernel, audit):
    """auth olayları action olarak olay adını yazar; login_failed error olur."""
    kernel.events.publish("auth.login", {"username": "ali"})
    kernel.events.publish("auth.login_failed", {"username": "ali"})
    kernel.events.publish("auth.logout", {"username": "ali"})
    rows = audit.search(None, "")
    assert [row["action"] for row in rows] == ["auth.logout", "auth.login_failed", "auth.login"]
    assert rows[1]["status"] == "error"
    assert rows[0]["status"] == "ok"


def test_other_events_tolerate_missing_keys(kernel, audit):
    """scripts.changed ve settings.changed eksik anahtarlarla da yazılır."""
    kernel.events.publish("scripts.changed", {"script_id": "s1", "change": "created"})
    kernel.events.publish("settings.changed", {"username": "admin", "setting": "menu"})
    kernel.events.publish("settings.changed", {})
    rows = audit.search(None, "")
    assert len(rows) == 3
    assert rows[2]["action"] == "scripts.changed"
    assert rows[2]["target"] == "s1"
    assert rows[2]["details"] == "created"
    assert rows[1]["target"] == "menu"


def test_search_filters_status_and_text(audit):
    """Durum ve metin filtreleri birlikte çalışır."""
    audit.write("ali", "script.run", "backup", "ok")
    audit.write("veli", "script.run", "deploy", "error", details="timeout")
    audit.write("veli", "auth.login", "", "ok")
    assert len(audit.search("error", "")) == 1
    assert len(audit.search(None, "veli")) == 2
    assert len(audit.search("ok", "veli")) == 1
    assert len(audit.search(None, "TIMEOUT")) == 1
    assert audit.search(None, "yok-boyle-bir-sey") == []


def test_long_details_truncated(audit):
    """details 4000 karakterde kırpılır."""
    audit.write("ali", "script.run", "x", "error", details="a" * 5000)
    rows = audit.search(None, "")
    assert len(rows[0]["details"]) == 4000
