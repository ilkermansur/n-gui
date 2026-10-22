"""system_panel.py - Ayarlar > Sistem paneli: bilgi kartları, eklenti durumları, paket listesi.

Kim kullanır: plugin.py paneli SettingsPanel olarak kaydeder; /settings sayfası
build_system_panel() fonksiyonunu çağırır.
Nasıl bağlanır: bilgiyi system_info.py'den, eklenti durumlarını
kernel.plugin_status sözlüğünden okur; salt okunurdur, olay yayınlamaz.
"""

from nicegui import ui

from app.core.kernel import get_kernel
from app.core.text import t
from app.core.theme import PAGE_TITLE_CLASSES
from app.core.widgets import page_card, stat_card, status_badge
from plugins.settings_core.system_info import collect_system_info, list_installed_packages


def pick_badge_color(status: str) -> str:
    """Eklenti durum metnine göre rozet rengi seçer.

    Parametre: status - "loaded", "disabled", "failed: ..." gibi metin.
    Dönüş: "green", "gray", "yellow" ya da "red".
    """
    if status == "loaded":
        return "green"
    if status in ("disabled", "not selected"):
        return "gray"
    if status.startswith("missing dependency"):
        return "yellow"
    return "red"


def build_system_panel() -> None:
    """"Sistem" ayar panelini o anki NiceGUI kapsamına çizer. Parametre ve dönüş yok."""
    kernel = get_kernel()
    info = collect_system_info(kernel.config.database_url)

    with ui.column().classes("w-full gap-4"):
        with ui.row().classes("w-full gap-4"):
            stat_card(t("settings.system.python"), info["python_version"])
            stat_card(t("settings.system.nicegui"), info["nicegui_version"])
            stat_card(t("settings.system.platform"), info["platform"])
        with page_card():
            ui.label(t("settings.system.database")).classes(PAGE_TITLE_CLASSES)
            ui.label(info["database_url_masked"])

        with page_card():
            ui.label(t("settings.system.plugins")).classes(PAGE_TITLE_CLASSES)
            for plugin_id, status in kernel.plugin_status.items():
                with ui.row().classes("items-center gap-3"):
                    ui.label(plugin_id).classes("w-40")
                    status_badge(status, pick_badge_color(status))

        with page_card():
            ui.label(t("settings.system.packages")).classes(PAGE_TITLE_CLASSES)
            columns = [
                {"name": "name", "label": t("settings.system.col.name"), "field": "name", "align": "left"},
                {"name": "version", "label": t("settings.system.col.version"), "field": "version", "align": "left"},
            ]
            ui.table(columns=columns, rows=list_installed_packages(), row_key="name").classes("w-full")
