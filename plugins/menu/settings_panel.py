"""settings_panel.py - Ayarlar sayfasındaki "Menü" paneli (bölüm ve grup editörü).

Kim kullanır: plugin.py, paneli SettingsPanel olarak kaydeder; /settings sayfası
build_menu_settings_panel() fonksiyonunu bir NiceGUI kapsamı içinde çağırır.
Nasıl bağlanır: bütün işi "menu" servisine yaptırır. Panel bir sınıftır
(MenuEditor); her değişiklikten sonra kendini baştan çizer. Ayarlar sayfası
bu paneli yetki kontrolünden sonra çağırır, burada ayrıca kontrol yapılmaz.
"""

from nicegui import ui

from app.core.kernel import get_kernel
from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import page_card


class MenuEditor:
    """Bölüm tablosunu, grup listesini ve dialogları yöneten panel."""

    def __init__(self) -> None:
        """Servisi alır, seçili bölümü boş bırakır. Dönüş: yok."""
        self.menu = get_kernel().get_service("menu")
        self.container = None
        self.table = None
        self.selected_key: str | None = None
        # Dialog alanları: dialog açılınca doldurulur.
        self.dialog = None
        self.key_input = None
        self.name_tr_input = None
        self.name_en_input = None
        self.icon_input = None
        self.order_input = None
        self.editing_key: str | None = None

    # ---------- Çizim ----------

    def build(self) -> None:
        """Panelin kapsayıcısını oluşturur ve ilk kez çizer."""
        self.container = ui.column().classes("w-full gap-4")
        self.render()

    def render(self) -> None:
        """Kapsayıcıyı temizleyip bölüm ve grup kartlarını yeniden çizer."""
        self.container.clear()
        with self.container:
            self.draw_sections_card()
            self.draw_groups_card()

    def draw_sections_card(self) -> None:
        """Bölümler tablosunu ve ekle/düzenle/gizle/sil düğmelerini çizer."""
        columns = [
            {"name": "key", "label": t("menu.col.key"), "field": "key", "align": "left"},
            {"name": "name_tr", "label": t("menu.col.name_tr"), "field": "name_tr", "align": "left"},
            {"name": "name_en", "label": t("menu.col.name_en"), "field": "name_en", "align": "left"},
            {"name": "icon", "label": t("menu.col.icon"), "field": "icon", "align": "left"},
            {"name": "order", "label": t("menu.col.order"), "field": "order"},
            {"name": "visible", "label": t("menu.col.visible"), "field": "visible"},
            {"name": "system", "label": t("menu.col.system"), "field": "system"},
        ]
        rows = []
        for section in self.menu.list_sections():
            rows.append(
                {
                    "key": section["key"],
                    "name_tr": section["name_tr"],
                    "name_en": section["name_en"],
                    "icon": section["icon"],
                    "order": section["order"],
                    "visible": "✓" if section["is_visible"] else "—",
                    "system": "✓" if section["is_system"] else "",
                }
            )

        with page_card():
            ui.label(t("menu.sections")).classes(PAGE_TITLE_CLASSES)
            with ui.row().classes("gap-2"):
                ui.button(t("menu.add"), icon="add", on_click=self.open_add_dialog)
                ui.button(t("menu.edit"), icon="edit", on_click=self.open_edit_dialog).props("flat")
                ui.button(t("menu.hide") + " / " + t("menu.show"), icon="visibility",
                          on_click=self.on_toggle_visible_click).props("flat")
                ui.button(t("menu.delete"), icon="delete",
                          on_click=self.on_delete_section_click).props("flat color=negative")
            self.table = ui.table(columns=columns, rows=rows, row_key="key", selection="single",
                                  on_select=self.on_selection_changed)
            self.table.classes("w-full")
            # Neden seçili satır korunur: yeniden çizimden sonra aynı bölüm seçili kalsın.
            if self.selected_key is not None:
                for row in rows:
                    if row["key"] == self.selected_key:
                        self.table.selected = [row]

    def draw_groups_card(self) -> None:
        """Seçili bölümün gruplarını ve grup ekle/sil düğmelerini çizer."""
        with page_card():
            ui.label(t("menu.groups")).classes(PAGE_TITLE_CLASSES)
            if self.selected_key is None:
                ui.label(t("menu.select_section")).classes(LABEL_CLASSES)
                return
            ui.label(self.selected_key).classes(LABEL_CLASSES)
            groups = self.menu.list_groups(self.selected_key)
            if not groups:
                ui.label(t("menu.no_groups")).classes(LABEL_CLASSES)
            for group in groups:
                with ui.row().classes("w-full items-center gap-2"):
                    ui.icon("folder", size="20px")
                    ui.label(group["name_tr"] + " / " + group["name_en"]).classes("grow")
                    delete_button = ui.button(icon="delete", on_click=self.on_delete_group_click)
                    delete_button.props("flat round dense color=negative")
                    # Neden props: tıklanan düğmenin hangi grubu sildiğini handler buradan okur.
                    delete_button.props["data-group-id"] = group["id"]
            ui.button(t("menu.add_group"), icon="add", on_click=self.open_group_dialog).props("flat")

    # ---------- Seçim ----------

    def on_selection_changed(self, event) -> None:
        """Tablo seçimi değişince seçili anahtarı saklar ve grup kartını yeniler.

        Parametre: event - NiceGUI olayı (kullanılmaz; seçim table.selected'dan okunur).
        """
        if self.table.selected:
            self.selected_key = self.table.selected[0]["key"]
        else:
            self.selected_key = None
        self.render()

    # ---------- Bölüm dialogları ----------

    def open_add_dialog(self) -> None:
        """Boş alanlarla "bölüm ekle" dialogunu açar."""
        self.editing_key = None
        self.open_section_dialog(t("menu.add_section"), "", "", "", "folder", None)

    def open_edit_dialog(self) -> None:
        """Seçili bölümün alanlarıyla "düzenle" dialogunu açar."""
        if self.selected_key is None:
            ui.notify(t("menu.select_section"), type="warning")
            return
        for section in self.menu.list_sections():
            if section["key"] == self.selected_key:
                self.editing_key = section["key"]
                self.open_section_dialog(
                    t("menu.edit_section"),
                    section["key"],
                    section["name_tr"],
                    section["name_en"],
                    section["icon"],
                    section["order"],
                )

    def open_section_dialog(self, title, key, name_tr, name_en, icon, order) -> None:
        """Bölüm dialogunu çizip açar. Düzenlemede anahtar ve sıra da gösterilir/kilitlenir."""
        with ui.dialog() as self.dialog:
            with page_card().classes("min-w-[360px] gap-2"):
                ui.label(title).classes(PAGE_TITLE_CLASSES)
                self.key_input = ui.input(t("menu.col.key"), value=key).props("outlined dense")
                # Neden kilitli: anahtar izinlerin ve menü öğelerinin kimliğidir, sonradan değişmez.
                self.key_input.set_enabled(self.editing_key is None)
                self.name_tr_input = ui.input(t("menu.col.name_tr"), value=name_tr).props("outlined dense")
                self.name_en_input = ui.input(t("menu.col.name_en"), value=name_en).props("outlined dense")
                self.icon_input = ui.input(t("menu.col.icon"), value=icon).props("outlined dense")
                self.order_input = None
                if order is not None:
                    self.order_input = ui.number(t("menu.col.order"), value=order, precision=0)
                    self.order_input.props("outlined dense")
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("menu.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("menu.save"), on_click=self.on_save_section_click)
        self.dialog.open()

    def on_save_section_click(self) -> None:
        """Dialogdaki bilgileri kaydeder (ekleme ya da güncelleme); hatayı bildirimle gösterir."""
        name_tr = (self.name_tr_input.value or "").strip()
        if not name_tr:
            ui.notify(t("menu.name_required"), type="warning")
            return
        name_en = (self.name_en_input.value or "").strip()
        icon = (self.icon_input.value or "").strip()
        try:
            if self.editing_key is None:
                key = (self.key_input.value or "").strip()
                self.menu.create_section(key, name_tr, name_en, icon)
                self.selected_key = key
            else:
                current = self.find_section(self.editing_key)
                self.menu.update_section(
                    self.editing_key, name_tr, name_en, icon,
                    int(self.order_input.value or 0), current["is_visible"],
                )
        except ValueError as error:
            ui.notify(t("menu.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        ui.notify(t("menu.saved"), type="positive")
        self.render()

    def find_section(self, key: str) -> dict:
        """Anahtarı verilen bölümün sözlüğünü döndürür; yoksa ValueError."""
        for section in self.menu.list_sections():
            if section["key"] == key:
                return section
        raise ValueError("Bölüm bulunamadı: " + key)

    # ---------- Gizle/göster ve sil ----------

    def on_toggle_visible_click(self) -> None:
        """Seçili bölümün görünürlüğünü tersine çevirir."""
        if self.selected_key is None:
            ui.notify(t("menu.select_section"), type="warning")
            return
        section = self.find_section(self.selected_key)
        self.menu.update_section(
            section["key"], section["name_tr"], section["name_en"], section["icon"],
            section["order"], not section["is_visible"],
        )
        self.render()

    def on_delete_section_click(self) -> None:
        """Seçili bölüm için onay dialogu açar."""
        if self.selected_key is None:
            ui.notify(t("menu.select_section"), type="warning")
            return
        with ui.dialog() as self.dialog:
            with page_card().classes("gap-2"):
                ui.label(t("menu.confirm_delete_section") + " (" + self.selected_key + ")")
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("menu.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("menu.delete"), on_click=self.on_confirm_delete_section).props("color=negative")
        self.dialog.open()

    def on_confirm_delete_section(self) -> None:
        """Onaydan sonra bölümü siler; sistem bölümünde hatayı bildirimle gösterir."""
        try:
            self.menu.delete_section(self.selected_key)
        except ValueError as error:
            self.dialog.close()
            ui.notify(t("menu.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        self.selected_key = None
        ui.notify(t("menu.deleted"), type="positive")
        self.render()

    # ---------- Gruplar ----------

    def open_group_dialog(self) -> None:
        """Seçili bölüme grup eklemek için dialog açar."""
        self.editing_key = None
        with ui.dialog() as self.dialog:
            with page_card().classes("min-w-[360px] gap-2"):
                ui.label(t("menu.add_group")).classes(PAGE_TITLE_CLASSES)
                self.name_tr_input = ui.input(t("menu.col.name_tr")).props("outlined dense")
                self.name_en_input = ui.input(t("menu.col.name_en")).props("outlined dense")
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("menu.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("menu.save"), on_click=self.on_save_group_click)
        self.dialog.open()

    def on_save_group_click(self) -> None:
        """Dialogdaki grubu seçili bölüme ekler."""
        name_tr = (self.name_tr_input.value or "").strip()
        if not name_tr:
            ui.notify(t("menu.name_required"), type="warning")
            return
        name_en = (self.name_en_input.value or "").strip()
        try:
            self.menu.create_group(self.selected_key, name_tr, name_en)
        except ValueError as error:
            ui.notify(t("menu.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        ui.notify(t("menu.saved"), type="positive")
        self.render()

    def on_delete_group_click(self, event) -> None:
        """Tıklanan düğmenin grubunu siler.

        Parametre: event - tıklama olayı; düğme event.sender ile bulunur.
        """
        group_id = event.sender.props["data-group-id"]
        try:
            self.menu.delete_group(group_id)
        except ValueError as error:
            ui.notify(t("menu.error", message=str(error)), type="negative")
            return
        ui.notify(t("menu.deleted"), type="positive")
        self.render()


def build_menu_settings_panel() -> None:
    """"Menü" ayar panelini o anki NiceGUI kapsamına çizer. Parametre ve dönüş yok."""
    MenuEditor().build()
