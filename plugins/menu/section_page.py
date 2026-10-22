"""section_page.py - /section/{key} sayfası: bir bölümün altındaki sayfaları kartlar halinde listeler.

Kim kullanır: plugin.py (bu modülü import etmesi sayfayı kaydeder).
Nasıl bağlanır: kernel.collect_nav_items sonucundan parent_key'i "section:<key>"
olan öğeleri alır (gruplar ve başka eklentilerin sayfaları dahil). Hiç öğe
yoksa boş durum kartı gösterir.
"""

from nicegui import ui

from app.core.access import check_page_access
from app.core.kernel import get_kernel
from app.core.layout import create_shell_frame, get_current_user
from app.core.navigation import nav_sort_key
from app.core.text import t
from app.core.theme import LABEL_CLASSES, NAV_ITEM_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import empty_state, page_card


def find_children(all_items: list, parent_key: str) -> list:
    """Verilen ebeveynin doğrudan çocuklarını menü sırasıyla döndürür.

    Parametreler: all_items - NavItem listesi; parent_key - ebeveynin anahtarı.
    """
    children = []
    for item in all_items:
        if item.parent_key == parent_key:
            children.append(item)
    return sorted(children, key=nav_sort_key)


def draw_item_row(item) -> None:
    """Tek bir menü öğesini ikon ve etiketle çizer; adresi varsa tıklanabilir olur."""
    if item.path:
        with ui.link(target=item.path).classes(NAV_ITEM_CLASSES):
            ui.icon(item.icon, size="20px")
            ui.label(item.label)
    else:
        with ui.row().classes("items-center gap-3 px-3 py-2"):
            ui.icon(item.icon, size="20px")
            ui.label(item.label).classes(LABEL_CLASSES)


def draw_item_card(item, all_items: list) -> None:
    """Bir öğeyi kart olarak çizer; grup gibi çocukları olan öğenin çocukları kartın içinde listelenir."""
    with page_card().classes("gap-1"):
        draw_item_row(item)
        for child in find_children(all_items, item.key):
            draw_item_row(child)


@ui.page("/section/{key}")
def section_page(key: str) -> None:
    """Bölüm sayfası: izin kontrolü, çerçeve ve alt öğelerin kartları."""
    kernel = get_kernel()
    if not check_page_access(kernel, "section." + key + ".view"):
        return

    menu = kernel.get_service("menu")
    title = key
    for section in menu.list_sections():
        if section["key"] == key:
            title = menu.pick_label(section["name_tr"], section["name_en"])

    content = create_shell_frame(kernel, title)
    all_items = kernel.collect_nav_items(get_current_user(kernel))
    children = find_children(all_items, "section:" + key)

    with content:
        ui.label(title).classes(PAGE_TITLE_CLASSES)
        if not children:
            empty_state(t("menu.section_empty"))
            return
        with ui.row().classes("w-full gap-4"):
            for item in children:
                draw_item_card(item, all_items)
