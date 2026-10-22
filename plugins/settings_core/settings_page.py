"""settings_page.py - /settings sayfası: kayıtlı ayar panellerini sekmeler halinde gösterir.

Kim kullanır: plugin.py (bu modülü import etmesi sayfayı kaydeder).
Nasıl bağlanır: kernel.list_settings_panels() ile tüm eklentilerin panellerini
(menu eklentisinin "Menü" paneli dahil) alır, kullanıcının iznine göre süzer ve
her birini ui.tab_panel içinde çizer. Sayfa "settings.view" izni ister.
"""

from nicegui import ui

from app.core.access import check_page_access
from app.core.kernel import get_kernel
from app.core.layout import create_shell_frame
from app.core.text import t
from app.core.widgets import empty_state

# Sekme sırası: bilinen anahtarlar bu sırayla, bilinmeyenler kayıt sırasıyla sona eklenir.
PANEL_ORDER = ["users", "roles", "menu", "system", "database"]


def sort_panels(panels: list) -> list:
    """Panelleri PANEL_ORDER'a göre dizer.

    Parametre: panels - SettingsPanel listesi.
    Dönüş: yeni sıralı liste; bilinmeyen anahtarlılar kayıt sırasını korur.
    """
    sorted_panels = []
    for key in PANEL_ORDER:
        for panel in panels:
            if panel.key == key:
                sorted_panels.append(panel)
    for panel in panels:
        if panel.key not in PANEL_ORDER:
            sorted_panels.append(panel)
    return sorted_panels


def find_allowed_panels(kernel) -> list:
    """Kullanıcının iznine sahip olduğu panelleri sıralı döndürür.

    Parametre: kernel - çekirdek. "auth" servisi yoksa bütün paneller döner.
    """
    auth = kernel.get_service("auth")
    allowed = []
    for panel in sort_panels(kernel.list_settings_panels()):
        if auth is None or auth.has_permission(auth.current_user(), panel.permission):
            allowed.append(panel)
    return allowed


@ui.page("/settings")
def settings_page() -> None:
    """Ayarlar sayfası: izin kontrolü, çerçeve ve sekmeli paneller."""
    kernel = get_kernel()
    if not check_page_access(kernel, "settings.view"):
        return

    content = create_shell_frame(kernel, t("settings.title"))
    panels = find_allowed_panels(kernel)
    with content:
        if not panels:
            empty_state(t("settings.no_panels"))
            return

        with ui.tabs().classes("w-full") as tabs:
            tab_list = []
            for panel in panels:
                tab_list.append(ui.tab(panel.key, label=t(panel.label_key), icon=panel.icon))
        with ui.tab_panels(tabs, value=tab_list[0]).classes("w-full bg-transparent"):
            for index in range(len(panels)):
                with ui.tab_panel(tab_list[index]).classes("p-0 pt-4"):
                    panels[index].build_function()
