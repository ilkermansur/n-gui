"""test_menu_service.py - menu eklentisinin servis katmanı testleri (bellek içi DB).

Kim kullanır: pytest.
Nasıl bağlanır: her test temiz bir sqlite bellek veritabanı kurar, MenuService'i
doğrudan kullanır; auth servisi yerine küçük bir sahte servis takılır.
"""

import pytest

from app.core.config import AppConfig
from app.core.db import create_all_tables, init_database
from app.core.kernel import Kernel
from plugins.menu import models  # noqa: F401  (tabloların Base'e kaydolması için)
from plugins.menu.service import MenuService


class FakeAuth:
    """Yalnızca verilen izinlere sahip kullanıcıyı taklit eden sahte auth servisi."""

    def has_permission(self, user: dict, permission: str) -> bool:
        """Kullanıcının izin listesinde varsa True döndürür."""
        return permission in user["permissions"]


@pytest.fixture
def kernel() -> Kernel:
    """Temiz bir veritabanı ve kernel döndürür."""
    init_database("sqlite:///:memory:")
    create_all_tables()
    return Kernel(AppConfig())


@pytest.fixture
def menu(kernel) -> MenuService:
    """Tohumlanmış bir MenuService döndürür."""
    service = MenuService(kernel)
    service.seed_defaults()
    return service


def test_seed_creates_five_sections_once(menu):
    """Seed beş bölüm üretir; ikinci çağrı kopya üretmez."""
    menu.seed_defaults()
    keys = []
    for section in menu.list_sections():
        keys.append(section["key"])
    assert keys == ["dashboard", "operation", "report", "log", "settings"]


def test_create_section_rejects_bad_key(menu):
    """Geçersiz anahtar ValueError verir."""
    with pytest.raises(ValueError):
        menu.create_section("Ürün B", "Ürün B", "Product B", "folder")


def test_create_section_registers_permission(kernel, menu):
    """Yeni bölümün görüntüleme izni kernel'e kaydolur."""
    menu.create_section("network", "Ağ", "Network", "lan")
    assert "section.network.view" in kernel.list_permissions()


def test_delete_system_section_rejected(menu):
    """Sistem bölümü silinemez."""
    with pytest.raises(ValueError):
        menu.delete_section("log")


def test_delete_section_removes_its_groups(menu):
    """Bölüm silinince grupları da gider."""
    menu.create_section("network", "Ağ", "Network", "lan")
    menu.create_group("network", "Switch", "Switch")
    menu.create_group("report", "Aylık", "Monthly")
    menu.delete_section("network")
    assert menu.list_groups("network") == []
    assert len(menu.list_groups()) == 1


def test_nav_items_respect_visibility_and_permission(kernel, menu):
    """Gizli bölüm ve izinsiz bölüm nav öğesi üretmez; grup bölümüyle birlikte gider."""
    kernel.register_service("auth", FakeAuth())
    menu.create_group("operation", "Hatlar", "Lines")
    section = menu.list_sections()[2]  # report
    menu.update_section(section["key"], section["name_tr"], section["name_en"],
                        section["icon"], section["order"], False)
    user = {"permissions": ["section.dashboard.view", "section.report.view"]}

    items = menu.build_menu_nav_items(user)

    keys = []
    for item in items:
        keys.append(item.key)
    # report gizli, operation izinsiz (ve grubu da yok), geri kalanlar izinsiz.
    assert keys == ["section:dashboard"]


def test_nav_items_without_auth_show_all_visible(menu):
    """auth servisi yoksa izin süzmesi yapılmaz; grup ebeveynine bağlanır."""
    menu.create_group("operation", "Hatlar", "Lines")
    items = menu.build_menu_nav_items(None)
    assert len(items) == 6
    assert items[-1].parent_key == "section:operation"
    assert items[-1].key.startswith("group:")
