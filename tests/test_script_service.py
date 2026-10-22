"""test_script_service.py - script_engine eklentisinin "scripts" servisi testleri.

Kim kullanır: pytest.
Nasıl bağlanır: her test bellek içi bir sqlite veritabanı ve geçici bir scripts
klasörü (tmp_path) kurar. Kernel'e gerçek "menu" servisi (tohumlanmış) ve
gerçek doğrulama fonksiyonunu kullanan küçük bir "forms" servisi takılır.
ScriptService doğrudan kullanılır; arayüz (NiceGUI) test edilmez.
"""

import os

import pytest

from app.core.config import AppConfig
from app.core.db import create_all_tables, init_database
from app.core.kernel import Kernel
from plugins.forms.validation import convert_and_validate
from plugins.menu import models as menu_models  # noqa: F401  (tabloların Base'e kaydolması için)
from plugins.menu.service import MenuService
from plugins.script_engine import models as script_models  # noqa: F401  (tablolar için)
from plugins.script_engine.service import ScriptService

GOOD_SCRIPT = '''"""Toplama yapar.
---
title: {tr: Toplama, en: Sum}
mode: form
inputs:
  count: {type: int, default: 2, min: 1, max: 10}
---
"""


def run(count: int = 2):
    print("hesaplaniyor")
    return {"count": count, "double": count * 2}
'''

BROKEN_SCRIPT = "def run(:\n    pass\n"


class FakeForms:
    """Yalnızca convert_and_validate sağlayan sahte forms servisi."""

    def convert_and_validate(self, fields, raw_values):
        """Gerçek doğrulama fonksiyonunu çağırır."""
        return convert_and_validate(fields, raw_values)


@pytest.fixture
def kernel(tmp_path) -> Kernel:
    """Bellek içi DB, geçici scripts klasörü ve menu/forms servisli kernel döndürür."""
    init_database("sqlite:///:memory:")
    create_all_tables()
    config = AppConfig()
    config.scripts_folder = str(tmp_path / "scripts")
    kernel = Kernel(config)
    menu = MenuService(kernel)
    menu.seed_defaults()
    kernel.register_service("menu", menu)
    kernel.register_service("forms", FakeForms())
    return kernel


@pytest.fixture
def service(kernel) -> ScriptService:
    """Geçici klasörü kullanan ScriptService döndürür."""
    return ScriptService(kernel)


def publish_default(service, script_id, section_key="operation", group_id=None, roles=None):
    """Testlerde sık kullanılan varsayılan değerlerle publish çağırır."""
    if roles is None:
        roles = []
    service.publish(
        script_id, "Toplama", "Sum", section_key, group_id, "form", roles, 30, 30, ""
    )


def test_service_creates_folder(service, kernel):
    """Klasör yoksa servis onu oluşturur."""
    assert os.path.isdir(kernel.config.scripts_folder)


def test_publish_then_scan_shows_entry(service):
    """Yüklenen ve yayınlanan script taramada kaydıyla görünür; yayınlanmamış olanın kaydı yoktur."""
    service.save_uploaded_file("Toplama.py", GOOD_SCRIPT.encode("utf-8"), False)
    service.save_uploaded_file("ikinci.py", GOOD_SCRIPT.encode("utf-8"), False)

    items = service.scan_folder()
    ids = []
    for item in items:
        ids.append(item["spec"].script_id)
    assert ids == ["ikinci", "toplama"]
    assert items[1]["entry"] is None

    publish_default(service, "toplama")
    items = service.scan_folder()
    entry = items[1]["entry"]
    assert entry is not None
    assert entry["section_key"] == "operation"
    assert entry["title_tr"] == "Toplama"
    assert entry["file_name"] == "toplama.py"
    assert entry["is_enabled"] is True
    assert items[1]["is_orphan"] is False
    assert items[1]["spec"].error == ""
    assert service.get_entry("toplama")["mode"] == "form"


def test_publish_updates_existing_entry(service):
    """İkinci publish yeni kayıt açmaz, var olanı günceller."""
    service.save_uploaded_file("toplama.py", GOOD_SCRIPT.encode("utf-8"), False)
    publish_default(service, "toplama")
    service.publish("toplama", "Yeni", "New", "report", None, "live", ["operator"], 10, 5, "")
    entry = service.get_entry("toplama")
    assert entry["title_tr"] == "Yeni"
    assert entry["section_key"] == "report"
    assert entry["allowed_roles"] == ["operator"]
    assert entry["refresh"] == 5
    assert len(service.scan_folder()) == 1


def test_publish_rejects_script_with_parse_error(service):
    """Parse hatası olan script yayınlanamaz ama taramada hatasıyla görünür."""
    service.save_uploaded_file("bozuk.py", BROKEN_SCRIPT.encode("utf-8"), False)
    with pytest.raises(ValueError):
        publish_default(service, "bozuk")
    items = service.scan_folder()
    assert items[0]["spec"].error != ""
    assert items[0]["entry"] is None


def test_upload_rejects_non_py_and_existing_without_overwrite(service, kernel):
    """.py olmayan dosya ve var olan dosya (overwrite=False) reddedilir."""
    with pytest.raises(ValueError):
        service.save_uploaded_file("notlar.txt", b"x", False)

    path = service.save_uploaded_file("Ping Testi.py", GOOD_SCRIPT.encode("utf-8"), False)
    assert os.path.basename(path) == "ping_testi.py"
    assert os.path.dirname(path) == os.path.abspath(kernel.config.scripts_folder)

    # Farklı ad, aynı kimlik: zaten var sayılır.
    with pytest.raises(ValueError):
        service.save_uploaded_file("ping_testi.py", b"def run():\n    return 1\n", False)

    service.save_uploaded_file("ping_testi.py", b"def run():\n    return 1\n", True)
    with open(path, encoding="utf-8") as script_file:
        assert script_file.read() == "def run():\n    return 1\n"


def test_remove_deletes_file_and_entry_keeps_runs(service):
    """Kaldırma dosyayı ve kaydı siler, çalışma geçmişi kalır."""
    path = service.save_uploaded_file("toplama.py", GOOD_SCRIPT.encode("utf-8"), False)
    publish_default(service, "toplama")
    service.execute("toplama", {"count": 3}, "ali")

    service.remove("toplama")

    assert not os.path.exists(path)
    assert service.get_entry("toplama") is None
    assert service.scan_folder() == []
    assert len(service.list_runs("toplama")) == 1


def test_can_user_run_roles(service):
    """admin her zaman; boş allowed_roles herkese açık; aksi halde kesişime bakılır."""
    admin = {"username": "admin", "roles": ["admin"], "permissions": ["*"]}
    operator = {"username": "op", "roles": ["operator"], "permissions": []}
    viewer = {"username": "vi", "roles": ["viewer"], "permissions": []}

    open_entry = {"allowed_roles": []}
    operator_entry = {"allowed_roles": ["operator"]}
    nobody_entry = {"allowed_roles": ["auditor"]}

    assert service.can_user_run(admin, nobody_entry) is True
    assert service.can_user_run(viewer, open_entry) is True
    assert service.can_user_run(operator, operator_entry) is True
    assert service.can_user_run(viewer, operator_entry) is False
    assert service.can_user_run(None, open_entry) is False


def test_execute_records_run_and_publishes_event(service, kernel):
    """execute script'i çalıştırır, ScriptRun yazar ve script.finished yayınlar."""
    received = []
    kernel.events.subscribe("script.finished", received.append)
    service.save_uploaded_file("toplama.py", GOOD_SCRIPT.encode("utf-8"), False)
    publish_default(service, "toplama")

    # Formdan metin olarak gelen sayı doğrulamada int'e çevrilir.
    result = service.execute("toplama", {"count": "4"}, "ali")

    assert result.success is True
    assert result.result == {"count": 4, "double": 8}
    assert len(received) == 1
    assert received[0]["username"] == "ali"
    assert received[0]["script_id"] == "toplama"
    assert received[0]["success"] is True

    runs = service.list_runs("toplama")
    assert len(runs) == 1
    assert runs[0]["success"] is True
    assert runs[0]["result"] == {"count": 4, "double": 8}
    assert "hesaplaniyor" in runs[0]["output_text"]
    assert service.last_run("toplama")["id"] == runs[0]["id"]


def test_execute_validation_error_does_not_run(service, kernel):
    """Geçersiz argümanla script çalıştırılmaz; başarısız kayıt ve olay oluşur."""
    received = []
    kernel.events.subscribe("script.finished", received.append)
    service.save_uploaded_file("toplama.py", GOOD_SCRIPT.encode("utf-8"), False)
    publish_default(service, "toplama")

    result = service.execute("toplama", {"count": 99}, "ali")

    assert result.success is False
    assert result.error_text != ""
    assert received[0]["success"] is False
    assert service.last_run("toplama")["success"] is False


def test_orphan_when_section_missing(service, kernel):
    """Bölümü (veya grubu) silinen kayıt is_orphan=True olur."""
    menu = kernel.get_service("menu")
    menu.create_section("network", "Ağ", "Network", "lan")
    group_id = menu.create_group("operation", "Ürün A", "Product A")
    service.save_uploaded_file("toplama.py", GOOD_SCRIPT.encode("utf-8"), False)
    service.save_uploaded_file("ikinci.py", GOOD_SCRIPT.encode("utf-8"), False)
    publish_default(service, "toplama", section_key="network")
    publish_default(service, "ikinci", section_key="operation", group_id=group_id)
    for item in service.scan_folder():
        assert item["is_orphan"] is False

    menu.delete_section("network")
    menu.delete_group(group_id)

    for item in service.scan_folder():
        assert item["is_orphan"] is True


def test_missing_file_entry_still_listed(service):
    """Dosyası diskten silinen kayıt "Dosya bulunamadı" hatasıyla listede kalır."""
    path = service.save_uploaded_file("toplama.py", GOOD_SCRIPT.encode("utf-8"), False)
    publish_default(service, "toplama")
    os.remove(path)

    items = service.scan_folder()
    assert len(items) == 1
    assert items[0]["entry"]["script_id"] == "toplama"
    assert items[0]["spec"].error == "Dosya bulunamadı"


def test_set_enabled_and_changed_events(service, kernel):
    """publish, set_enabled ve remove scripts.changed yayınlar; nav provider devre dışını göstermez."""
    received = []
    kernel.events.subscribe("scripts.changed", received.append)
    service.save_uploaded_file("toplama.py", GOOD_SCRIPT.encode("utf-8"), False)
    publish_default(service, "toplama")

    items = service.build_nav_items(None)
    assert len(items) == 1
    assert items[0].key == "script:toplama"
    assert items[0].parent_key == "section:operation"
    assert items[0].path == "/script/toplama"
    assert items[0].icon == "play_arrow"

    service.set_enabled("toplama", False)
    assert service.get_entry("toplama")["is_enabled"] is False
    assert service.build_nav_items(None) == []

    service.remove("toplama")
    changes = []
    for data in received:
        assert data["script_id"] == "toplama"
        changes.append(data["change"])
    assert changes == ["published", "disabled", "removed"]
