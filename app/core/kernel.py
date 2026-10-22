"""kernel.py - çekirdek: servis, izin, menü ve ayar paneli kayıt defterleri.

Kim kullanır: eklentiler (setup içinde kernel'a kayıt yapar) ve sayfalar.
Nasıl bağlanır: uygulama başlarken bir Kernel oluşturulup set_kernel() ile
saklanır; her yer get_kernel() ile aynı nesneye ulaşır.
"""

import logging

from app.core.config import AppConfig
from app.core.events import EventBus
from app.core.plugin import NavItem, SettingsPanel, UserMenuItem

logger = logging.getLogger(__name__)


class Kernel:
    """Eklentilerin birbirini tanımadan çalışmasını sağlayan merkez."""

    def __init__(self, config: AppConfig) -> None:
        """Boş kayıt defterleriyle kernel oluşturur.

        Parametre: config - uygulama ayarları. Dönüş: yok.
        """
        self.config = config
        self.events = EventBus()
        self.plugin_status: dict[str, str] = {}
        self.loaded_plugin_folders: list[str] = []
        self.services: dict[str, object] = {}
        self.permissions: dict[str, str] = {}
        self.nav_providers: list = []
        self.settings_panels: list[SettingsPanel] = []
        self.user_menu_items: list[UserMenuItem] = []

    def register_service(self, name: str, service) -> None:
        """Bir servisi adıyla kaydeder. Parametreler: name, service. Dönüş: yok."""
        self.services[name] = service

    def get_service(self, name: str):
        """Servisi döndürür; yoksa None. Parametre: name."""
        return self.services.get(name)

    def register_permission(self, key: str, description: str) -> None:
        """İzin kaydeder; aynı anahtar varsa açıklamayı günceller.

        Neden üzerine yazılır: eklentiler her açılışta yeniden kayıt yapabilir.
        """
        self.permissions[key] = description

    def list_permissions(self) -> dict[str, str]:
        """Kayıtlı izinlerin kopyasını döndürür (anahtar -> açıklama)."""
        return dict(self.permissions)

    def add_nav_provider(self, function) -> None:
        """Menü öğesi üreten fonksiyonu ekler.

        Parametre: function - (user: dict | None) -> list[NavItem]. Dönüş: yok.
        """
        self.nav_providers.append(function)

    def collect_nav_items(self, user: dict | None) -> list[NavItem]:
        """Tüm provider'ları çağırıp menü öğelerini birleştirir.

        Parametre: user - giriş yapmış kullanıcı sözlüğü ya da None.
        Dönüş: NavItem listesi; hata veren provider atlanır.
        """
        items: list[NavItem] = []
        for provider in self.nav_providers:
            # Neden: tek bir bozuk eklenti bütün menüyü bozmamalı.
            try:
                items.extend(provider(user))
            except Exception:
                logger.exception("Menü provider'ı hata verdi")
        return items

    def register_settings_panel(self, panel: SettingsPanel) -> None:
        """Ayarlar sayfasına panel ekler. Parametre: panel. Dönüş: yok."""
        self.settings_panels.append(panel)

    def list_settings_panels(self) -> list[SettingsPanel]:
        """Kayıtlı panellerin kopyasını döndürür."""
        return list(self.settings_panels)

    def add_user_menu_item(self, item: UserMenuItem) -> None:
        """Kullanıcı menüsüne satır ekler (örn. auth'un "Şifremi değiştir"). Parametre: item."""
        self.user_menu_items.append(item)

    def list_user_menu_items(self) -> list[UserMenuItem]:
        """Kayıtlı kullanıcı menüsü satırlarının kopyasını döndürür."""
        return list(self.user_menu_items)


# Neden modül seviyesinde: uygulamada tek kernel var, her yer ona ulaşmalı.
current_kernel: Kernel | None = None


def set_kernel(kernel: Kernel) -> None:
    """Uygulamanın tek kernel'ini saklar. Parametre: kernel. Dönüş: yok."""
    global current_kernel
    current_kernel = kernel


def get_kernel() -> Kernel:
    """Saklanan kernel'i döndürür; henüz set edilmediyse RuntimeError fırlatır."""
    if current_kernel is None:
        raise RuntimeError("Kernel henüz hazır değil: önce set_kernel() çağrılmalı.")
    return current_kernel
