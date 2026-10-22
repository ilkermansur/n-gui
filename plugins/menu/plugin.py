"""plugin.py - menu eklentisi: bölümler ve gruplar veritabanında, menü editörü ayarlarda.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: modelleri import eder (tablolar Base'e kaydolsun), "menu"
servisini, nav provider'ı, izni, /section/{key} sayfasını ve "Menü" ayar
panelini kaydeder; "database.ready" olayında hazır bölümleri ekler.
"""

from app.core.plugin import Plugin, SettingsPanel
from plugins.menu import models  # noqa: F401  (tabloların Base'e kaydolması için)
from plugins.menu import section_page  # noqa: F401  (import /section/{key} sayfasını kaydeder)
from plugins.menu.service import MenuService
from plugins.menu.settings_panel import build_menu_settings_panel


class MenuPlugin(Plugin):
    """Menüyü veriden üreten eklenti."""

    plugin_id = "menu"
    name = "menu"
    version = "1.0"
    # Neden boş: auth ve i18n yoksa menü yine çalışır (süzme/çeviri yapılmaz).
    requires = []

    def setup(self, kernel) -> None:
        """Servisi, izni, menü sağlayıcısını ve ayar panelini kaydeder.

        Parametre: kernel - çekirdek. Dönüş: yok.
        """
        self.kernel = kernel
        self.service = MenuService(kernel)
        kernel.register_service("menu", self.service)
        kernel.register_permission("settings.menu.manage", "menu.permission.menu_manage")
        kernel.add_nav_provider(self.service.build_menu_nav_items)
        kernel.register_settings_panel(
            SettingsPanel(
                key="menu",
                label_key="menu.settings_title",
                icon="menu",
                permission="settings.menu.manage",
                build_function=build_menu_settings_panel,
            )
        )
        # Neden olayda: tablolar ancak "database.ready" yayınlanınca hazırdır.
        kernel.events.subscribe("database.ready", self.on_database_ready)

    def on_database_ready(self, data: dict) -> None:
        """Hazır bölümleri ekler ve tüm bölümlerin izinlerini kaydeder.

        Parametre: data - olay verisi (kullanılmaz). Dönüş: yok.
        """
        self.service.seed_defaults()
        # Neden burada: kernel'in izin kaydı bellektedir, her açılışta yeniden yapılmalı.
        self.service.register_all_section_permissions()
