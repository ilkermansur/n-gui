"""plugin.py - auth eklentisi: kullanıcı, rol, oturum ve login sayfası.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: modelleri import eder (tablolar Base'e kaydolsun), "auth"
servisini ve izinleri kaydeder, /login sayfasını ekler ve "database.ready"
olayında hazır rol/admin kayıtlarını oluşturur.
"""

import logging

from app.core.plugin import Plugin
from plugins.auth import models  # noqa: F401  (tabloların Base'e kaydolması için)
from plugins.auth import login_page  # noqa: F401  (import /login sayfasını kaydeder)
from plugins.auth.service import AuthService

logger = logging.getLogger(__name__)


class AuthPlugin(Plugin):
    """Kullanıcı, rol ve giriş yönetimi sağlayan eklenti."""

    plugin_id = "auth"
    name = "auth"
    version = "1.0"
    # Neden boş: i18n yoksa t() anahtarı döndürür; auth tek başına çalışabilir.
    requires = []

    def setup(self, kernel) -> None:
        """Servisi, izinleri ve sayfayı kaydeder; seed'i olaya bağlar.

        Parametre: kernel - çekirdek. Dönüş: yok.
        """
        self.kernel = kernel
        self.service = AuthService(kernel)
        kernel.register_service("auth", self.service)
        kernel.register_permission("settings.users.manage", "auth.permission.users_manage")
        kernel.register_permission("settings.roles.manage", "auth.permission.roles_manage")
        # Neden olayda: tablolar ancak "database.ready" yayınlanınca hazırdır.
        kernel.events.subscribe("database.ready", self.on_database_ready)

    def on_database_ready(self, data: dict) -> None:
        """Hazır rolleri ve admin kullanıcısını oluşturur.

        Parametre: data - olay verisi (kullanılmaz). Dönüş: yok.
        """
        password = self.kernel.config.initial_admin_password
        self.service.seed_defaults(password)
        if password == "admin":
            logger.warning(
                "Admin şifresi varsayılan değerde (\"admin\"); "
                "config.toml içindeki [auth] initial_admin_password değerini değiştirin."
            )
