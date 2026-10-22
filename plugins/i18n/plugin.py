"""plugin.py - i18n eklentisi: çeviri servisini kurar.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: "i18n" servisini kaydeder ve "plugins.loaded" olayında çekirdeğin
ve yüklenen her eklentinin locales klasöründeki tr.json / en.json dosyalarını yükler.
"""

import os

from app.core.plugin import Plugin
from plugins.i18n.translator import Translator

# Çekirdeğin kabuk metinleri: app/core/locales
CORE_LOCALES_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..", "app", "core", "locales")


class I18nPlugin(Plugin):
    """Çok dilli metin desteği (tr/en) sağlayan eklenti."""

    plugin_id = "i18n"
    name = "i18n"
    version = "1.0"
    requires = []

    def setup(self, kernel) -> None:
        """Servisi kaydeder ve çeviri yüklemesini olaya bağlar.

        Parametre: kernel - çekirdek. Dönüş: yok.
        """
        self.kernel = kernel
        self.translator = Translator(kernel.config.default_language)
        kernel.register_service("i18n", self.translator)
        # Neden olayda yüklenir: diğer eklentiler setup'ta henüz yüklenmemiş olabilir;
        # "plugins.loaded" hepsi hazır olunca yayınlanır.
        kernel.events.subscribe("plugins.loaded", self.on_plugins_loaded)

    def on_plugins_loaded(self, data: dict) -> None:
        """Çekirdek ve eklenti çevirilerini yükler.

        Parametre: data - olay verisi (kullanılmaz). Dönüş: yok.
        """
        self.translator.load_folder(CORE_LOCALES_FOLDER)
        for plugin_folder in self.kernel.loaded_plugin_folders:
            self.translator.load_folder(os.path.join(plugin_folder, "locales"))
