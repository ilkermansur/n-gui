"""plugin.py - eklenti sözleşmesi ve eklentilerin çekirdekle paylaştığı veri tipleri.

Kim kullanır: her eklenti (Plugin sınıfından türetir), kernel ve menü/ayar
sayfaları (NavItem, SettingsPanel).
Nasıl bağlanır: loader, eklenti klasöründeki plugin.py içinden Plugin alt
sınıfını bulur ve setup(kernel) metodunu çağırır.
"""

from dataclasses import dataclass


class Plugin:
    """Her eklentinin türetmesi gereken taban sınıf."""

    plugin_id: str = ""
    name: str = ""
    version: str = "1.0"
    # Neden güvenli: bu liste hiçbir yerde değiştirilmez, sadece okunur.
    # Alt sınıflar kendi listesini atayarak üzerine yazar.
    requires: list[str] = []

    def setup(self, kernel) -> None:
        """Eklentiyi kurar (servis, izin, menü, sayfa kaydı yapar).

        Parametre: kernel - çekirdek nesnesi. Dönüş: yok.
        Alt sınıflar bu metodu doldurur.
        """


@dataclass
class NavItem:
    """Yan menüdeki tek bir satır."""

    key: str
    label: str  # zaten çevrilmiş metin
    icon: str
    path: str
    parent_key: str | None = None
    order: int = 100


@dataclass
class SettingsPanel:
    """Ayarlar sayfasında görünen bir panel."""

    key: str
    label_key: str
    icon: str
    permission: str
    build_function: object  # parametre almayan, UI çizen fonksiyon
