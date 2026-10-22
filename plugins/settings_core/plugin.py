"""plugin.py - settings_core eklentisi: /settings sayfası ve Kullanıcılar/Roller/Sistem/Veritabanı panelleri.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: izinleri ve dört ayar panelini kaydeder, /settings sayfasını
import ile ekler. Kullanıcı/rol panelleri "auth" servisine dayandığı için
requires = ["auth"]. Diğer eklentilerin panelleri (örn. menu) sayfada otomatik görünür.
"""

from app.core.plugin import Plugin, SettingsPanel
from plugins.settings_core import settings_page  # noqa: F401  (import /settings sayfasını kaydeder)
from plugins.settings_core.database_panel import build_database_panel
from plugins.settings_core.roles_panel import build_roles_panel
from plugins.settings_core.system_panel import build_system_panel
from plugins.settings_core.users_panel import build_users_panel


class SettingsCorePlugin(Plugin):
    """Ayarlar sayfasını ve çekirdek ayar panellerini sağlayan eklenti."""

    plugin_id = "settings_core"
    name = "settings_core"
    version = "1.0"
    requires = ["auth"]

    def setup(self, kernel) -> None:
        """İzinleri ve panelleri kaydeder.

        Parametre: kernel - çekirdek. Dönüş: yok.
        """
        self.kernel = kernel
        kernel.register_permission("settings.view", "settings.permission.view")
        kernel.register_permission("settings.system.view", "settings.permission.system_view")
        kernel.register_permission("settings.database.manage", "settings.permission.database_manage")

        # users ve roles izinlerini auth eklentisi zaten kaydeder.
        kernel.register_settings_panel(
            SettingsPanel("users", "settings.users.tab", "people", "settings.users.manage", build_users_panel)
        )
        kernel.register_settings_panel(
            SettingsPanel("roles", "settings.roles.tab", "admin_panel_settings", "settings.roles.manage", build_roles_panel)
        )
        kernel.register_settings_panel(
            SettingsPanel("system", "settings.system.tab", "info", "settings.system.view", build_system_panel)
        )
        kernel.register_settings_panel(
            SettingsPanel("database", "settings.database.tab", "storage", "settings.database.manage", build_database_panel)
        )
