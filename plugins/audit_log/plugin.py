"""plugin.py - audit_log eklentisi: işlem kayıtları ve /log sayfası.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: modeli import eder (tablo Base'e kaydolsun), "audit" servisini
ve "log.view" iznini kaydeder, olaylara abone olur ve /log sayfasını ekler.
Menüdeki "Log" bölümünü menu eklentisi hazır kayıt olarak zaten oluşturur.
"""

import logging

from nicegui import app

from app.core.plugin import Plugin
from plugins.audit_log import log_page  # noqa: F401  (import /log sayfasını kaydeder)
from plugins.audit_log import models  # noqa: F401  (tablonun Base'e kaydolması için)
from plugins.audit_log.service import AuditService

logger = logging.getLogger(__name__)

# Saklama süresi temizliğinin aralığı (saniye): günde bir.
PURGE_INTERVAL_SECONDS = 24 * 60 * 60


class AuditLogPlugin(Plugin):
    """İşlem kaydı tutan eklenti."""

    plugin_id = "audit_log"
    name = "audit_log"
    version = "1.0"
    # Neden boş: auth yoksa sayfa herkese açık olur, i18n yoksa anahtarlar görünür.
    requires = []

    def setup(self, kernel) -> None:
        """Servisi, izni ve olay aboneliklerini kaydeder.

        Parametre: kernel - çekirdek. Dönüş: yok.
        """
        self.kernel = kernel
        self.service = AuditService(kernel)
        kernel.register_service("audit", self.service)
        kernel.register_permission("log.view", "audit_log.permission.view")
        self.service.subscribe_events()
        # Neden açılışta ve günde bir: [audit] retention_days doluysa eski kayıtlar silinsin.
        kernel.events.subscribe("database.ready", self.on_database_ready)
        app.timer(PURGE_INTERVAL_SECONDS, self.purge_old_entries, immediate=False)

    def on_database_ready(self, data: dict) -> None:
        """Tablolar hazır olunca ilk temizliği yapar. Parametre: data (kullanılmaz)."""
        self.purge_old_entries()

    def purge_old_entries(self) -> None:
        """Saklama süresinden eski Log kayıtlarını siler ve sayıyı loglar. Dönüş: yok."""
        removed = self.service.purge_older_than(self.kernel.config.retention_days)
        if removed > 0:
            logger.info("Saklama süresi dolan %s Log kaydı silindi", removed)
