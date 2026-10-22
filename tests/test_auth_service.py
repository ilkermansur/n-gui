"""test_auth_service.py - auth eklentisinin servis katmanı testleri (bellek içi DB).

Kim kullanır: pytest.
Nasıl bağlanır: her test temiz bir sqlite bellek veritabanı kurar, AuthService'i
doğrudan kullanır (web sunucusu gerekmez).
"""

import pytest

from app.core.config import AppConfig
from app.core.db import create_all_tables, init_database
from app.core.kernel import Kernel
from plugins.auth import models  # noqa: F401  (tabloların Base'e kaydolması için)
from plugins.auth.service import AuthService


@pytest.fixture
def auth() -> AuthService:
    """Tohumlanmış (seed) bir AuthService döndürür; admin parolası "secret1"."""
    init_database("sqlite:///:memory:")
    create_all_tables()
    service = AuthService(Kernel(AppConfig()))
    service.seed_defaults("secret1")
    return service


def test_seed_creates_roles_and_admin(auth):
    """Roller ve admin kullanıcısı oluşur; seed ikinci kez kopya üretmez."""
    auth.seed_defaults("secret1")
    role_names = []
    for role in auth.list_roles():
        role_names.append(role["name"])
    assert sorted(role_names) == ["admin", "operator", "viewer"]

    users = auth.list_users()
    assert len(users) == 1
    assert users[0]["username"] == "admin"
    assert users[0]["roles"] == ["admin"]


def test_authenticate_ok_and_wrong_password(auth):
    """Doğru parola kullanıcıyı, yanlış parola None döndürür."""
    user = auth.authenticate("admin", "secret1")
    assert user is not None
    assert user["username"] == "admin"
    assert auth.authenticate("admin", "yanlis") is None
    assert auth.authenticate("yok", "secret1") is None


def test_inactive_user_cannot_login_and_lookup_returns_none(auth):
    """Pasif kullanıcı giriş yapamaz ve id ile aranınca None döner."""
    user = auth.create_user("ali", "Ali Veli", "pw12345", ["viewer"])
    auth.update_user(user["id"], "Ali Veli", False, ["viewer"])
    assert auth.authenticate("ali", "pw12345") is None
    assert auth.get_user_by_id(user["id"]) is None


def test_has_permission_wildcard_and_specific(auth):
    """"*" her izni kapsar; diğer roller yalnızca kendi izinlerine sahiptir."""
    admin = auth.authenticate("admin", "secret1")
    assert auth.has_permission(admin, "herhangi.bir.izin")

    viewer = auth.create_user("v", "Viewer", "pw12345", ["viewer"])
    assert auth.has_permission(viewer, "section.dashboard.view")
    assert not auth.has_permission(viewer, "log.view")
    assert not auth.has_permission(None, "section.dashboard.view")


def test_user_permissions_union_of_roles(auth):
    """Kullanıcının izinleri rollerinin izinlerinin birleşimidir."""
    auth.create_role("ozel")
    auth.set_role_permissions("ozel", ["x.y", "log.view"])
    user = auth.create_user("m", "Multi", "pw12345", ["viewer", "ozel"])
    assert "section.dashboard.view" in user["permissions"]
    assert "x.y" in user["permissions"]
    assert "log.view" in user["permissions"]
    # Aynı izin iki rolde olsa bile bir kez görünür.
    assert len(user["permissions"]) == len(set(user["permissions"]))


def test_duplicate_username_raises_valueerror(auth):
    """Aynı kullanıcı adı (büyük/küçük harf fark etmez) ikinci kez açılamaz."""
    with pytest.raises(ValueError):
        auth.create_user("ADMIN", "Baska", "pw12345", [])


def test_username_is_case_insensitive_on_login(auth):
    """"Admin" yazarak da giriş yapılabilir."""
    assert auth.authenticate("  Admin ", "secret1") is not None
