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
    """Tohumlanmış (seed) bir AuthService döndürür; admin parolası "secret123"."""
    init_database("sqlite:///:memory:")
    create_all_tables()
    service = AuthService(Kernel(AppConfig()))
    service.seed_defaults("secret123")
    return service


def test_seed_creates_roles_and_admin(auth):
    """Roller ve admin kullanıcısı oluşur; seed ikinci kez kopya üretmez."""
    auth.seed_defaults("secret123")
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
    user = auth.authenticate("admin", "secret123")
    assert user is not None
    assert user["username"] == "admin"
    assert auth.authenticate("admin", "yanlis") is None
    assert auth.authenticate("yok", "secret123") is None


def test_inactive_user_cannot_login_and_lookup_returns_none(auth):
    """Pasif kullanıcı giriş yapamaz ve id ile aranınca None döner."""
    user = auth.create_user("ali", "Ali Veli", "pw123456", ["viewer"])
    auth.update_user(user["id"], "Ali Veli", False, ["viewer"])
    assert auth.authenticate("ali", "pw123456") is None
    assert auth.get_user_by_id(user["id"]) is None


def test_seed_operator_can_see_log_section(auth):
    """operator rolü Log bölümünü menüde görebilmek için section.log.view iznine sahiptir."""
    auth.seed_defaults("secret123")
    operator = auth.create_user("o", "Operator", "pw123456", ["operator"])
    assert auth.has_permission(operator, "section.log.view")
    assert auth.has_permission(operator, "log.view")


def test_has_permission_wildcard_and_specific(auth):
    """"*" her izni kapsar; diğer roller yalnızca kendi izinlerine sahiptir."""
    admin = auth.authenticate("admin", "secret123")
    assert auth.has_permission(admin, "herhangi.bir.izin")

    viewer = auth.create_user("v", "Viewer", "pw123456", ["viewer"])
    assert auth.has_permission(viewer, "section.dashboard.view")
    assert not auth.has_permission(viewer, "log.view")
    assert not auth.has_permission(None, "section.dashboard.view")


def test_user_permissions_union_of_roles(auth):
    """Kullanıcının izinleri rollerinin izinlerinin birleşimidir."""
    auth.create_role("ozel")
    auth.set_role_permissions("ozel", ["x.y", "log.view"])
    user = auth.create_user("m", "Multi", "pw123456", ["viewer", "ozel"])
    assert "section.dashboard.view" in user["permissions"]
    assert "x.y" in user["permissions"]
    assert "log.view" in user["permissions"]
    # Aynı izin iki rolde olsa bile bir kez görünür.
    assert len(user["permissions"]) == len(set(user["permissions"]))


def test_duplicate_username_raises_valueerror(auth):
    """Aynı kullanıcı adı (büyük/küçük harf fark etmez) ikinci kez açılamaz."""
    with pytest.raises(ValueError):
        auth.create_user("ADMIN", "Baska", "pw123456", [])


def test_username_is_case_insensitive_on_login(auth):
    """"Admin" yazarak da giriş yapılabilir."""
    assert auth.authenticate("  Admin ", "secret123") is not None


def test_create_user_rejects_bad_password_length(auth):
    """Kısa (<8, varsayılan) ve 72 bayttan uzun parolalar ValueError verir; sınır değerleri kabul edilir."""
    with pytest.raises(ValueError):
        auth.create_user("kisa", "Kısa", "abcdefg", [])
    with pytest.raises(ValueError):
        auth.create_user("uzun", "Uzun", "a" * 73, [])
    # Neden: ş 2 bayttır; 37 karakter = 74 bayt, karakter sayısı değil bayt sayılmalı.
    with pytest.raises(ValueError):
        auth.create_user("bayt", "Bayt", "ş" * 37, [])
    auth.create_user("sinir1", "Sınır", "abcdefgh", [])
    auth.create_user("sinir2", "Sınır", "a" * 72, [])


def test_change_password_rejects_bad_password_length(auth):
    """change_password da aynı uzunluk kurallarını uygular."""
    admin_id = auth.list_users()[0]["id"]
    with pytest.raises(ValueError):
        auth.change_password(admin_id, "abc")
    with pytest.raises(ValueError):
        auth.change_password(admin_id, "a" * 73)
    auth.change_password(admin_id, "yenisifre")
    assert auth.authenticate("admin", "yenisifre") is not None


def test_duplicate_role_names_are_ignored(auth):
    """Aynı rol adı iki kez verilince tek bağ oluşur (hata yok)."""
    user = auth.create_user("cift", "Çift", "secret123", ["viewer", "viewer"])
    assert user["roles"] == ["viewer"]


def make_auth_with_config(config: AppConfig) -> AuthService:
    """Verilen ayarlarla temiz bir veritabanı üzerinde tohumlanmış AuthService döndürür."""
    init_database("sqlite:///:memory:")
    create_all_tables()
    service = AuthService(Kernel(config))
    service.seed_defaults("secret123")
    return service


def test_min_password_length_comes_from_config():
    """En kısa parola uzunluğu [auth] min_password_length ayarından gelir."""
    config = AppConfig()
    config.min_password_length = 12
    auth = make_auth_with_config(config)
    with pytest.raises(ValueError):
        auth.create_user("kisa", "Kısa", "a" * 11, [])
    auth.create_user("uzun", "Uzun", "a" * 12, [])


def test_seed_accepts_short_initial_password():
    """İlk admin parolası kural dışı kısa olsa da admin oluşur (geliştirme kolaylığı)."""
    init_database("sqlite:///:memory:")
    create_all_tables()
    service = AuthService(Kernel(AppConfig()))
    service.seed_defaults("admin")
    assert service.authenticate("admin", "admin") is not None
    assert service.has_default_admin_password() is True


def test_has_default_admin_password_false_after_change(auth):
    """Admin parolası "admin" değilse has_default_admin_password False döner."""
    assert auth.has_default_admin_password() is False


class FakeClock:
    """Testte zamanı elle ilerletmek için sahte saat (saniye)."""

    def __init__(self) -> None:
        """Saat 1000. saniyeden başlar."""
        self.now = 1000.0

    def __call__(self) -> float:
        """Şu anki sahte zamanı döndürür."""
        return self.now


def test_login_is_locked_after_too_many_failures(auth):
    """Üst üste hatalı denemeler hesabı kilitler; süre dolunca kilit açılır."""
    clock = FakeClock()
    auth.clock = clock
    auth.kernel.config.max_login_attempts = 3
    auth.kernel.config.lockout_minutes = 10
    for attempt in range(3):
        assert auth.authenticate("admin", "yanlis") is None
    assert auth.is_locked_out("admin") is True
    # Neden: kilitliyken doğru parola da reddedilir.
    assert auth.authenticate("admin", "secret123") is None
    clock.now += 10 * 60 + 1
    assert auth.is_locked_out("admin") is False
    assert auth.authenticate("admin", "secret123") is not None


def test_successful_login_resets_failure_counter(auth):
    """Başarılı giriş hatalı deneme sayacını sıfırlar."""
    auth.kernel.config.max_login_attempts = 3
    auth.authenticate("admin", "yanlis")
    auth.authenticate("admin", "yanlis")
    assert auth.authenticate("admin", "secret123") is not None
    auth.authenticate("admin", "yanlis")
    auth.authenticate("admin", "yanlis")
    assert auth.is_locked_out("admin") is False


def test_lockout_disabled_when_max_attempts_zero(auth):
    """max_login_attempts 0 ise kilitleme yapılmaz."""
    auth.kernel.config.max_login_attempts = 0
    for attempt in range(20):
        auth.authenticate("admin", "yanlis")
    assert auth.is_locked_out("admin") is False


def test_change_own_password_requires_current_password(auth):
    """Kullanıcı kendi parolasını ancak mevcut parolayı bilerek değiştirebilir."""
    admin_id = auth.list_users()[0]["id"]
    with pytest.raises(ValueError):
        auth.change_own_password(admin_id, "yanlis", "yeniparola1")
    with pytest.raises(ValueError):
        auth.change_own_password(admin_id, "secret123", "kisa")
    auth.change_own_password(admin_id, "secret123", "yeniparola1")
    assert auth.authenticate("admin", "yeniparola1") is not None


def test_delete_role_rules(auth):
    """Kullanılmayan rol silinir; admin rolü ve kullanıcıya atanmış rol silinemez."""
    auth.create_role("gecici")
    auth.delete_role("gecici")
    names = []
    for role in auth.list_roles():
        names.append(role["name"])
    assert "gecici" not in names
    with pytest.raises(ValueError):
        auth.delete_role("admin")
    auth.create_user("v1", "Viewer", "pw123456", ["viewer"])
    with pytest.raises(ValueError):
        auth.delete_role("viewer")
    with pytest.raises(ValueError):
        auth.delete_role("yok")
