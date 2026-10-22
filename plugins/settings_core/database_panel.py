"""database_panel.py - Ayarlar > Veritabanı paneli: adres göster, bağlantıyı dene, config.toml'a kaydet.

Kim kullanır: plugin.py paneli SettingsPanel olarak kaydeder; /settings sayfası
build_database_panel() fonksiyonunu yetki kontrolünden sonra çağırır.
Nasıl bağlanır: mevcut adres kernel.config.database_url'den okunur ve
maskelenerek gösterilir; kaydedilen adres kernel.config.config_path dosyasına
save_config_value ile yazılır. Yeni adres ancak yeniden başlatınca geçerli olur.
"""

from nicegui import ui
from sqlalchemy import create_engine

from app.core.config import save_config_value
from app.core.kernel import get_kernel
from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import page_card
from plugins.settings_core.changes import publish_settings_changed
from plugins.settings_core.system_info import mask_database_url


class DatabaseEditor:
    """Adres giriş kutusunu ve test/kaydet düğmelerini yöneten panel."""

    def __init__(self) -> None:
        """Kernel'i alır. Dönüş: yok."""
        self.kernel = get_kernel()
        self.url_input = None

    def build(self) -> None:
        """Paneli çizer."""
        with page_card().classes("gap-3"):
            ui.label(t("settings.database.title")).classes(PAGE_TITLE_CLASSES)
            ui.label(t("settings.database.current")).classes(LABEL_CLASSES)
            ui.label(mask_database_url(self.kernel.config.database_url))
            # Neden boş başlar: mevcut adres şifre içerebilir, giriş kutusuna yazılmaz.
            self.url_input = ui.input(t("settings.database.new_url")).props("outlined dense").classes("w-full")
            with ui.row().classes("gap-2"):
                ui.button(t("settings.database.test"), icon="bolt", on_click=self.on_test_click).props("flat")
                ui.button(t("settings.save"), icon="save", on_click=self.on_save_click)

    def on_test_click(self) -> None:
        """Girilen adrese bağlanmayı dener ve sonucu bildirimle gösterir."""
        url = (self.url_input.value or "").strip()
        if not url:
            ui.notify(t("settings.database.url_required"), type="warning")
            return
        engine = None
        # Neden geniş except: sürücü eksikliği, ağ hatası, bozuk adres gibi her hata "başarısız" sayılır.
        try:
            engine = create_engine(url)
            connection = engine.connect()
            connection.close()
        except Exception as error:
            # Neden maskelenir: hata metni adresi (şifre dahil) içerebilir.
            message = str(error).replace(url, mask_database_url(url))
            ui.notify(t("settings.database.test_failed", message=message[:200]), type="negative")
            return
        finally:
            if engine is not None:
                engine.dispose()
        ui.notify(t("settings.database.test_ok"), type="positive")

    def on_save_click(self) -> None:
        """Adresi config.toml'a yazar ve yeniden başlatma uyarısı gösterir."""
        url = (self.url_input.value or "").strip()
        if not url:
            ui.notify(t("settings.database.url_required"), type="warning")
            return
        save_config_value(self.kernel.config.config_path, "database", "url", url)
        # Neden maskeli: olay günlüğe yazılır, şifre orada görünmemeli.
        publish_settings_changed("database", "adres güncellendi: " + mask_database_url(url))
        ui.notify(t("settings.database.restart"), type="warning")


def build_database_panel() -> None:
    """"Veritabanı" ayar panelini o anki NiceGUI kapsamına çizer. Parametre ve dönüş yok."""
    DatabaseEditor().build()
