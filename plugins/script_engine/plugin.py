"""plugin.py - script_engine eklentisi: .py script'lerini menüde çalışan sayfalara çevirir.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: modelleri import eder (tablolar Base'e kaydolsun), "scripts"
servisini, "scripts.manage" iznini, nav provider'ı, /script/{script_id}
sayfasını ve "Scriptler" ayar panelini kaydeder. Form üretimi için "forms",
bölüm/grup bilgisi için "menu" eklentisine ihtiyaç duyar; "auth" ve "i18n"
varsa kullanılır (yoksa yetki süzmesi/çeviri yapılmaz).
"""

import logging

from nicegui import app

from app.core.plugin import Plugin, SettingsPanel
from plugins.script_engine import models  # noqa: F401  (tabloların Base'e kaydolması için)
from plugins.script_engine import script_page  # noqa: F401  (import /script/{id} sayfasını kaydeder)
from plugins.script_engine.scripts_panel import build_scripts_settings_panel
from plugins.script_engine.service import ScriptService

logger = logging.getLogger(__name__)

# Saklama süresi temizliğinin aralığı (saniye): günde bir.
PURGE_INTERVAL_SECONDS = 24 * 60 * 60


class ScriptEnginePlugin(Plugin):
    """Script yükleme, yayınlama ve çalıştırma eklentisi."""

    plugin_id = "script_engine"
    name = "script_engine"
    version = "1.0"
    requires = ["forms", "menu"]

    def setup(self, kernel) -> None:
        """Servisi, izni, menü sağlayıcısını ve ayar panelini kaydeder.

        Parametre: kernel - çekirdek. Dönüş: yok.
        """
        self.kernel = kernel
        self.service = ScriptService(kernel)
        kernel.register_service("scripts", self.service)
        kernel.register_permission("scripts.manage", "script_engine.permission.manage")
        kernel.add_nav_provider(self.service.build_nav_items)
        kernel.register_settings_panel(
            SettingsPanel(
                key="scripts",
                label_key="script_engine.settings_title",
                icon="code",
                permission="scripts.manage",
                build_function=build_scripts_settings_panel,
            )
        )
        # Neden açılışta ve günde bir: [audit] retention_days doluysa eski çalışma geçmişi silinsin.
        kernel.events.subscribe("database.ready", self.on_database_ready)
        app.timer(PURGE_INTERVAL_SECONDS, self.purge_old_runs, immediate=False)

    def on_database_ready(self, data: dict) -> None:
        """Tablolar hazır olunca ilk temizliği yapar. Parametre: data (kullanılmaz)."""
        self.purge_old_runs()

    def purge_old_runs(self) -> None:
        """Saklama süresinden eski çalışma kayıtlarını siler ve sayıyı loglar. Dönüş: yok."""
        removed = self.service.purge_runs_older_than(self.kernel.config.retention_days)
        if removed > 0:
            logger.info("Saklama süresi dolan %s script çalışma kaydı silindi", removed)
