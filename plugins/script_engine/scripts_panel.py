"""scripts_panel.py - Ayarlar sayfasındaki "Scriptler" paneli: script listesi ve satır aksiyonları.

Kim kullanır: plugin.py, paneli SettingsPanel olarak kaydeder; /settings sayfası
build_scripts_settings_panel() fonksiyonunu bir NiceGUI kapsamı içinde çağırır.
Nasıl bağlanır: listeyi "scripts" servisinin scan_folder() sonucundan üretir.
Üstte "Yükle" (sihirbazı açar) ve "Yeniden tara" düğmeleri, her satırda
Düzenle (sihirbazı 3. adımdan açar), Devre dışı/Etkin ve Kaldır (onaylı) bulunur.
Ayarlar sayfası paneli "scripts.manage" iznine göre gösterir; burada ayrıca kontrol yapılmaz.
"""

import os

from nicegui import ui

from app.core.kernel import get_kernel
from app.core.layout import refresh_navigation
from app.core.text import t
from app.core.theme import PAGE_TITLE_CLASSES
from app.core.widgets import page_card
from plugins.script_engine.wizard import ScriptWizard

# Satır aksiyon düğmeleri: Quasar şablonu. Neden $parent.$emit: tablo hücresindeki
# düğme, tıklamayı satır verisiyle birlikte Python'daki table.on(...) handler'ına iletir.
ACTIONS_SLOT = (
    '<q-td :props="props" class="text-right">'
    '<q-btn flat dense round icon="edit" :disable="props.row.has_error"'
    " @click=\"$parent.$emit('edit_script', props.row)\" />"
    '<q-btn v-if="props.row.has_entry" flat dense round'
    " :icon=\"props.row.is_enabled ? 'toggle_on' : 'toggle_off'\""
    " :color=\"props.row.is_enabled ? 'positive' : 'grey'\""
    " @click=\"$parent.$emit('toggle_script', props.row)\" />"
    '<q-btn flat dense round icon="delete" color="negative"'
    " @click=\"$parent.$emit('remove_script', props.row)\" />"
    "</q-td>"
)

# Durum rozeti: renk satırdaki status_color alanından gelir (pill görünüm için rounded).
STATUS_SLOT = (
    '<q-td :props="props">'
    '<q-badge rounded :color="props.row.status_color" :label="props.value" />'
    "</q-td>"
)


def compute_status(item: dict) -> tuple[str, str]:
    """Tarama öğesinin durum metnini ve rozet rengini hesaplar.

    Öncelik: hatalı > yayınlanmamış > atanmamış > devre dışı > yayında.
    Dönüş: (çeviri anahtarı, Quasar renk adı).
    """
    if item["spec"].error != "":
        return "script_engine.status.error", "negative"
    entry = item["entry"]
    if entry is None:
        return "script_engine.status.unpublished", "grey"
    if item["is_orphan"]:
        return "script_engine.status.orphan", "warning"
    if not entry["is_enabled"]:
        return "script_engine.status.disabled", "grey-7"
    return "script_engine.status.published", "positive"


class ScriptsPanel:
    """Script tablosunu, dialogları ve sihirbazı yöneten panel."""

    def __init__(self) -> None:
        """Servisleri alır. Dönüş: yok."""
        self.kernel = get_kernel()
        self.service = self.kernel.get_service("scripts")
        self.menu = self.kernel.get_service("menu")
        self.container = None
        self.table = None
        self.dialog = None
        self.pending_remove_id = None

    # ---------- Çizim ----------

    def build(self) -> None:
        """Panelin kapsayıcısını oluşturur ve ilk kez çizer."""
        self.container = ui.column().classes("w-full gap-4")
        self.render()

    def render(self) -> None:
        """Kapsayıcıyı temizleyip script kartını yeniden çizer (klasör yeniden taranır)."""
        self.container.clear()
        with self.container:
            with page_card().classes("gap-4"):
                with ui.row().classes("w-full items-center gap-2"):
                    ui.label(t("script_engine.settings_title")).classes(PAGE_TITLE_CLASSES)
                    ui.space()
                    ui.button(t("script_engine.upload"), icon="upload", on_click=self.on_upload_click)
                    ui.button(t("script_engine.rescan"), icon="refresh", on_click=self.on_rescan_click).props("flat")
                self.draw_table()

    def redraw_after_change(self) -> None:
        """Bir script yayınlanınca, değişince ya da kaldırılınca listeyi ve sol menüyü yeniler."""
        # Neden önce menü: render() tıklanan düğmeyi siler; ondan sonra NiceGUI
        # bağlamı (hangi tarayıcı sekmesi) bulunamaz.
        refresh_navigation()
        self.render()

    def build_place_text(self, entry: dict | None) -> str:
        """Kaydın menüdeki yerini "Bölüm / Grup" metni olarak üretir."""
        if entry is None:
            return ""
        section_text = entry["section_key"]
        group_text = ""
        for section in self.menu.list_sections():
            if section["key"] == entry["section_key"]:
                section_text = self.menu.pick_label(section["name_tr"], section["name_en"])
        if entry["group_id"] is not None:
            group_text = "#" + str(entry["group_id"])
            for group in self.menu.list_groups(entry["section_key"]):
                if group["id"] == entry["group_id"]:
                    group_text = self.menu.pick_label(group["name_tr"], group["name_en"])
        if group_text == "":
            return section_text
        return section_text + " / " + group_text

    def draw_table(self) -> None:
        """Taranan script'leri tablo olarak çizer ve satır aksiyonlarını bağlar."""
        columns = [
            {"name": "title", "label": t("script_engine.col.title"), "field": "title", "align": "left", "sortable": True},
            {"name": "file", "label": t("script_engine.col.file"), "field": "file", "align": "left"},
            {"name": "place", "label": t("script_engine.col.place"), "field": "place", "align": "left"},
            {"name": "mode", "label": t("script_engine.col.mode"), "field": "mode", "align": "left"},
            {"name": "status", "label": t("script_engine.col.status"), "field": "status", "align": "left"},
            {"name": "actions", "label": "", "field": "actions", "align": "right"},
        ]
        rows = []
        for item in self.service.scan_folder():
            spec = item["spec"]
            entry = item["entry"]
            status_key, status_color = compute_status(item)
            if entry is not None:
                title = self.service.pick_title(entry)
                mode = entry["mode"]
                is_enabled = entry["is_enabled"]
            else:
                title = self.menu.pick_label(spec.title_tr, spec.title_en)
                mode = spec.mode
                is_enabled = False
            rows.append(
                {
                    "script_id": spec.script_id,
                    "title": title,
                    "file": os.path.basename(spec.file_path),
                    "place": self.build_place_text(entry),
                    "mode": t("script_engine.mode." + mode),
                    "status": t(status_key),
                    "status_color": status_color,
                    "error": spec.error,
                    "has_error": spec.error != "",
                    "has_entry": entry is not None,
                    "is_enabled": is_enabled,
                }
            )

        self.table = ui.table(columns=columns, rows=rows, row_key="script_id").classes("w-full").props("flat")
        self.table.add_slot("body-cell-status", STATUS_SLOT)
        self.table.add_slot("body-cell-actions", ACTIONS_SLOT)
        self.table.on("edit_script", self.on_edit_event)
        self.table.on("toggle_script", self.on_toggle_event)
        self.table.on("remove_script", self.on_remove_event)
        if len(rows) == 0:
            ui.label(t("script_engine.no_scripts")).classes("text-sm text-slate-500 dark:text-slate-400")
        # Hatalı script'lerin mesajı tablonun altında listelenir; admin nedenini görsün.
        for row in rows:
            if row["has_error"]:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("error", size="18px").classes("text-red-500")
                    ui.label(row["file"] + ": " + row["error"]).classes("text-sm text-red-600 dark:text-red-300")

    # ---------- Üst düğmeler ----------

    def on_upload_click(self) -> None:
        """Yükleme sihirbazını 1. adımdan açar."""
        ScriptWizard(self.kernel, self.redraw_after_change).open_new()

    def on_rescan_click(self) -> None:
        """Klasörü yeniden tarar (elle bırakılan dosyalar listeye gelir)."""
        self.render()
        ui.notify(t("script_engine.rescanned"), type="info")

    # ---------- Satır aksiyonları ----------

    def on_edit_event(self, event) -> None:
        """Satırdaki "Düzenle": sihirbazı bu script için 3. adımdan açar.

        Parametre: event - event.args tıklanan satırın verisidir.
        """
        ScriptWizard(self.kernel, self.redraw_after_change).open_for_edit(event.args["script_id"])

    def on_toggle_event(self, event) -> None:
        """Satırdaki etkin/devre dışı düğmesi: durumu tersine çevirir."""
        if not self.service.current_user_can_manage():
            ui.notify(t("shell.forbidden"), type="negative")
            return
        script_id = event.args["script_id"]
        entry = self.service.get_entry(script_id)
        if entry is None:
            return
        try:
            self.service.set_enabled(script_id, not entry["is_enabled"], username=self.service.current_username())
        except ValueError as error:
            ui.notify(t("script_engine.error", message=str(error)), type="negative")
            return
        ui.notify(t("script_engine.saved"), type="positive")
        self.redraw_after_change()

    def on_remove_event(self, event) -> None:
        """Satırdaki "Kaldır": onay dialogu açar."""
        self.pending_remove_id = event.args["script_id"]
        with ui.dialog() as self.dialog:
            with page_card().classes("gap-2"):
                ui.label(t("script_engine.confirm_remove", name=event.args["file"]))
                ui.label(t("script_engine.remove_hint")).classes("text-sm text-slate-500 dark:text-slate-400")
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("script_engine.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("script_engine.remove"), on_click=self.on_confirm_remove).props("color=negative")
        self.dialog.open()

    def on_confirm_remove(self) -> None:
        """Onaydan sonra script'i menüden ve diskten kaldırır."""
        if not self.service.current_user_can_manage():
            self.dialog.close()
            ui.notify(t("shell.forbidden"), type="negative")
            return
        try:
            self.service.remove(self.pending_remove_id, username=self.service.current_username())
        except (ValueError, OSError) as error:
            self.dialog.close()
            ui.notify(t("script_engine.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        ui.notify(t("script_engine.removed"), type="positive")
        self.redraw_after_change()



def build_scripts_settings_panel() -> None:
    """"Scriptler" ayar panelini o anki NiceGUI kapsamına çizer. Parametre ve dönüş yok."""
    ScriptsPanel().build()
