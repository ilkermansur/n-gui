"""plugin.py - audit_log eklentisi: işlem kayıtları ve /log sayfası.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: modeli import eder (tablo Base'e kaydolsun), "audit" servisini
ve "log.view" iznini kaydeder, olaylara abone olur ve /log sayfasını ekler.
Menüdeki "Log" bölümünü menu eklentisi hazır kayıt olarak zaten oluşturur.
"""

from app.core.plugin import Plugin
from plugins.audit_log import log_page  # noqa: F401  (import /log sayfasını kaydeder)
from plugins.audit_log import models  # noqa: F401  (tablonun Base'e kaydolması için)
from plugins.audit_log.service import AuditService


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
