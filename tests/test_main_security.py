"""test_main_security.py - app/main.py içindeki canlı ortam güvenlik kontrolünün testleri.

Kim kullanır: pytest.
Nasıl bağlanır: gerçek auth yerine has_default_admin_password döndüren sahte bir servis takılır.
"""

import pytest

from app.core.config import AppConfig
from app.core.kernel import Kernel
from app.main import enforce_security, find_security_problems


class FakeAuth:
    """Yalnızca admin parolasının varsayılan olup olmadığını söyleyen sahte auth servisi."""

    def __init__(self, default_password: bool) -> None:
        """Parametre: default_password - has_default_admin_password'ün döndüreceği değer."""
        self.default_password = default_password

    def has_default_admin_password(self) -> bool:
        """Kurulumda verilen değeri döndürür."""
        return self.default_password


def make_kernel(secret: str, default_password: bool, environment: str) -> Kernel:
    """Verilen ayarlarla sahte auth servisli bir kernel döndürür."""
    config = AppConfig()
    config.storage_secret = secret
    config.environment = environment
    kernel = Kernel(config)
    kernel.register_service("auth", FakeAuth(default_password))
    return kernel


def test_secure_setup_has_no_problems():
    """Uzun gizli anahtar ve değiştirilmiş admin parolası sorun üretmez."""
    kernel = make_kernel("x" * 40, False, "production")
    assert find_security_problems(kernel) == []
    enforce_security(kernel)


def test_default_secret_and_password_are_reported():
    """Varsayılan gizli anahtar ve admin parolası iki ayrı sorun olarak raporlanır."""
    kernel = make_kernel("degistir-beni", True, "development")
    assert len(find_security_problems(kernel)) == 2


def test_development_only_warns():
    """Geliştirme ortamında sorunlar yalnızca loglanır, uygulama durmaz."""
    enforce_security(make_kernel("degistir-beni", True, "development"))


def test_production_refuses_to_start():
    """Canlı ortamda sorun varsa uygulama çıkış koduyla durur."""
    with pytest.raises(SystemExit):
        enforce_security(make_kernel("degistir-beni", False, "production"))
