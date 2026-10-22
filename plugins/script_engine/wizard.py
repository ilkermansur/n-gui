"""wizard.py - 3 adımlı script yükleme sihirbazı (dialog içinde ui.stepper).

Kim kullanır: scripts_panel.py ("Yükle" düğmesi ve satırdaki "Düzenle").
Nasıl bağlanır: bütün kalıcı işleri "scripts" servisine yaptırır; bölüm ve
grupları "menu", rolleri "auth", form önizlemesini "forms" servisinden alır.
Adımlar:
1. Dosya: .py yükleme (ui.upload) ya da klasördeki yayınlanmamış bir dosyayı seçme.
2. Önizleme: algılanan alanlar tablosu, formun canlı önizlemesi, varsa parse hatası.
3. Yerleşim: başlık, bölüm, grup (ya da yeni grup), mod, roller, süreler; "Yayınla".
Docstring'deki öneriler (bölüm, grup, mod, roller...) 3. adımda alanlara önceden doldurulur;
script zaten yayındaysa kayıttaki değerler kullanılır.
"""

import os

from nicegui import ui

from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import page_card
from plugins.script_engine.parser import make_script_id
from plugins.script_engine.result_view import show_run_texts

STEP_FILE = "file"
STEP_PREVIEW = "preview"
STEP_PLACEMENT = "placement"

# Grup seçicisinde "grup yok" seçeneğinin değeri. Neden 0: veritabanı id'leri 1'den
# başlar; None ise seçicide "seçim yapılmamış" ile karışır.
NO_GROUP = 0

# Docstring bölüm önermiyorsa moda göre varsayılan bölüm.
DEFAULT_SECTION_BY_MODE = {
    "form": "operation",
    "live": "dashboard",
    "scheduled": "report",
}


def find_section_key(suggestion: str, sections: list[dict]) -> str:
    """Docstring'deki bölüm önerisini bölüm anahtarı ya da adıyla eşleştirir.

    Parametreler: suggestion - örn. "Operation"; sections - seçilebilir bölümler.
    Dönüş: eşleşen bölümün anahtarı; yoksa boş metin. Büyük/küçük harf fark etmez.
    """
    wanted = suggestion.strip().lower()
    if wanted == "":
        return ""
    for section in sections:
        if wanted == section["key"].lower():
            return section["key"]
        if wanted == section["name_tr"].lower() or wanted == section["name_en"].lower():
            return section["key"]
    return ""


def find_group_id(suggestion: str, groups: list[dict]) -> int:
    """Docstring'deki grup önerisini grup adlarıyla eşleştirir.

    Dönüş: eşleşen grubun id'si; yoksa NO_GROUP. Büyük/küçük harf fark etmez.
    """
    wanted = suggestion.strip().lower()
    if wanted == "":
        return NO_GROUP
    for group in groups:
        if wanted == group["name_tr"].lower() or wanted == group["name_en"].lower():
            return group["id"]
    return NO_GROUP


class ScriptWizard:
    """Yükleme sihirbazının dialogunu, adımlarını ve seçimlerini tutar."""

    def __init__(self, kernel, on_published) -> None:
        """Parametreler: kernel; on_published - yayın sonrası çağrılacak fonksiyon (panel yenileme)."""
        self.kernel = kernel
        self.service = kernel.get_service("scripts")
        self.menu = kernel.get_service("menu")
        self.on_published = on_published
        self.script_id = None
        self.spec = None
        self.entry = None
        # Arayüz öğeleri: build_dialog içinde oluşturulur.
        self.dialog = None
        self.stepper = None
        self.upload = None
        self.overwrite_switch = None
        self.unpublished_select = None
        self.preview_container = None
        self.preview_next_button = None
        self.placement_container = None
        self.title_tr_input = None
        self.title_en_input = None
        self.section_select = None
        self.group_select = None
        self.new_group_input = None
        self.mode_select = None
        self.roles_select = None
        self.timeout_input = None
        self.refresh_input = None
        self.schedule_input = None

    # ---------- Açma ----------

    def open_new(self) -> None:
        """Sihirbazı 1. adımdan (dosya seçimi) açar."""
        self.build_dialog()
        self.dialog.open()

    def open_for_edit(self, script_id: str) -> None:
        """Sihirbazı verilen script için doğrudan 3. adımdan (yerleşim) açar."""
        self.build_dialog()
        self.load_script(script_id)
        self.render_preview()
        self.render_placement()
        self.stepper.set_value(STEP_PLACEMENT)
        self.dialog.open()

    def load_script(self, script_id: str) -> None:
        """Script'i diskten taze okur ve (varsa) yayın kaydını alır."""
        self.script_id = script_id
        self.spec = self.service.parse(script_id)
        self.entry = self.service.get_entry(script_id)

    # ---------- Dialog ----------

    def build_dialog(self) -> None:
        """Dialogu ve üç adımlı stepper'ı çizer."""
        with ui.dialog() as self.dialog:
            with page_card().classes("w-[960px] max-w-[95vw] gap-2"):
                with ui.row().classes("w-full items-center"):
                    ui.label(t("script_engine.wizard.title")).classes(PAGE_TITLE_CLASSES)
                    ui.space()
                    ui.button(icon="close", on_click=self.dialog.close).props("flat round dense")
                with ui.stepper(value=STEP_FILE).props("flat animated").classes("w-full") as self.stepper:
                    with ui.step(STEP_FILE, title=t("script_engine.wizard.step_file"), icon="upload_file"):
                        self.draw_file_step()
                    with ui.step(STEP_PREVIEW, title=t("script_engine.wizard.step_preview"), icon="preview"):
                        self.preview_container = ui.column().classes("w-full gap-4")
                        with ui.stepper_navigation():
                            ui.button(t("script_engine.back"), on_click=self.on_back_click).props("flat")
                            self.preview_next_button = ui.button(
                                t("script_engine.next"), on_click=self.on_preview_next_click
                            )
                    with ui.step(STEP_PLACEMENT, title=t("script_engine.wizard.step_placement"), icon="place"):
                        self.placement_container = ui.column().classes("w-full gap-4")
                        with ui.stepper_navigation():
                            ui.button(t("script_engine.back"), on_click=self.on_back_click).props("flat")
                            ui.button(t("script_engine.publish"), icon="publish", on_click=self.on_publish_click)

    # ---------- 1. adım: dosya ----------

    def draw_file_step(self) -> None:
        """Yükleme kutusunu ve yayınlanmamış dosya seçicisini çizer."""
        ui.label(t("script_engine.wizard.upload_hint")).classes(LABEL_CLASSES)
        self.upload = ui.upload(
            label=t("script_engine.wizard.upload_label"),
            auto_upload=True,
            max_files=1,
            on_upload=self.on_upload,
        )
        self.upload.props("accept=.py flat bordered").classes("w-full")
        self.overwrite_switch = ui.switch(t("script_engine.wizard.overwrite"), value=False)

        ui.separator()
        ui.label(t("script_engine.wizard.pick_existing")).classes(LABEL_CLASSES)
        options = {}
        for item in self.service.scan_folder():
            if item["entry"] is None:
                spec = item["spec"]
                options[spec.script_id] = os.path.basename(spec.file_path)
        self.unpublished_select = ui.select(options, label=t("script_engine.wizard.unpublished"))
        self.unpublished_select.props("outlined").classes("w-full")
        if len(options) == 0:
            ui.label(t("script_engine.wizard.no_unpublished")).classes(LABEL_CLASSES)
        with ui.stepper_navigation():
            ui.button(t("script_engine.next"), on_click=self.on_file_next_click)

    async def on_upload(self, event) -> None:
        """Yüklenen dosyayı scripts klasörüne kaydeder ve önizleme adımına geçer.

        Parametre: event - NiceGUI upload olayı (event.file.name, await event.file.read()).
        """
        content = await event.file.read()
        try:
            path = self.service.save_uploaded_file(event.file.name, content, self.overwrite_switch.value)
        except ValueError as error:
            ui.notify(t("script_engine.error", message=str(error)), type="negative")
            self.upload.reset()
            return
        ui.notify(t("script_engine.wizard.uploaded", name=os.path.basename(path)), type="positive")
        self.load_script(make_script_id(os.path.basename(path)))
        self.render_preview()
        self.stepper.set_value(STEP_PREVIEW)

    def on_file_next_click(self) -> None:
        """Listeden seçilen yayınlanmamış dosyayla önizleme adımına geçer."""
        if not self.unpublished_select.value:
            ui.notify(t("script_engine.wizard.choose_file"), type="warning")
            return
        self.load_script(self.unpublished_select.value)
        self.render_preview()
        self.stepper.set_value(STEP_PREVIEW)

    def on_back_click(self) -> None:
        """Bir önceki adıma döner."""
        self.stepper.previous()

    # ---------- 2. adım: önizleme ----------

    def render_preview(self) -> None:
        """Algılanan alanlar tablosunu, form önizlemesini ve varsa parse hatasını çizer."""
        self.preview_container.clear()
        with self.preview_container:
            ui.label(os.path.basename(self.spec.file_path) or self.script_id).classes(
                "text-lg font-semibold text-slate-800 dark:text-white"
            )
            if self.spec.description:
                ui.label(self.spec.description).classes(LABEL_CLASSES + " whitespace-pre-wrap")
            if self.spec.error != "":
                show_run_texts("", self.spec.error)
                self.preview_next_button.disable()
                return
            self.preview_next_button.enable()
            self.draw_fields_table()
            ui.label(t("script_engine.wizard.form_preview")).classes(LABEL_CLASSES)
            with ui.column().classes("w-full rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-4"):
                if len(self.spec.fields) == 0:
                    ui.label(t("script_engine.no_inputs")).classes(LABEL_CLASSES)
                self.kernel.get_service("forms").build_form(self.spec.fields)

    def draw_fields_table(self) -> None:
        """Script'ten okunan form alanlarını tablo olarak çizer."""
        columns = [
            {"name": "name", "label": t("script_engine.col.field"), "field": "name", "align": "left"},
            {"name": "type", "label": t("script_engine.col.type"), "field": "type", "align": "left"},
            {"name": "label", "label": t("script_engine.col.label"), "field": "label", "align": "left"},
            {"name": "required", "label": t("script_engine.col.required"), "field": "required", "align": "left"},
            {"name": "default", "label": t("script_engine.col.default"), "field": "default", "align": "left"},
            {"name": "options", "label": t("script_engine.col.options"), "field": "options", "align": "left"},
        ]
        rows = []
        for field in self.spec.fields:
            option_texts = []
            for option in field.options:
                option_texts.append(str(option))
            default_text = ""
            if field.default is not None:
                default_text = str(field.default)
            rows.append(
                {
                    "name": field.name,
                    "type": field.field_type,
                    "label": field.label_tr,
                    "required": "✓" if field.required else "",
                    "default": default_text,
                    "options": ", ".join(option_texts),
                }
            )
        ui.table(columns=columns, rows=rows, row_key="name").classes("w-full").props("flat dense")

    def on_preview_next_click(self) -> None:
        """Yerleşim adımını önerilerle doldurup ona geçer."""
        self.render_placement()
        self.stepper.set_value(STEP_PLACEMENT)

    # ---------- 3. adım: yerleşim ----------

    def list_selectable_sections(self) -> list[dict]:
        """Script konulabilecek bölümleri döndürür (sistem bölümleri log ve settings hariç)."""
        sections = []
        for section in self.menu.list_sections():
            if not section["is_system"]:
                sections.append(section)
        return sections

    def build_group_options(self, section_key: str) -> dict:
        """Bölümün grupları için seçici seçeneklerini üretir ("grup yok" dahil)."""
        options = {NO_GROUP: t("script_engine.wizard.no_group")}
        if not section_key:
            return options
        for group in self.menu.list_groups(section_key):
            options[group["id"]] = self.menu.pick_label(group["name_tr"], group["name_en"])
        return options

    def list_role_names(self) -> list[str]:
        """Seçilebilecek rol adlarını "auth" servisinden okur; servis yoksa boş liste."""
        auth = self.kernel.get_service("auth")
        if auth is None:
            return []
        names = []
        for role in auth.list_roles():
            names.append(role["name"])
        return names

    def compute_initial_values(self, sections: list[dict]) -> dict:
        """3. adımın başlangıç değerlerini hesaplar.

        Script yayındaysa kayıttaki değerler, değilse docstring önerileri kullanılır.
        Dönüş: alan adı -> değer sözlüğü.
        """
        if self.entry is not None:
            group_id = self.entry["group_id"]
            if group_id is None:
                group_id = NO_GROUP
            return {
                "title_tr": self.entry["title_tr"],
                "title_en": self.entry["title_en"],
                "section_key": self.entry["section_key"],
                "group_id": group_id,
                "new_group": "",
                "mode": self.entry["mode"],
                "roles": list(self.entry["allowed_roles"]),
                "timeout": self.entry["timeout"],
                "refresh": self.entry["refresh"],
                "schedule": self.entry["schedule"],
            }

        section_key = find_section_key(self.spec.suggested_section, sections)
        if section_key == "":
            section_key = DEFAULT_SECTION_BY_MODE.get(self.spec.mode, "")
        section_found = False
        for section in sections:
            if section["key"] == section_key:
                section_found = True
        if not section_found:
            section_key = ""
            if len(sections) > 0:
                section_key = sections[0]["key"]

        group_id = NO_GROUP
        new_group = ""
        if section_key:
            group_id = find_group_id(self.spec.suggested_group, self.menu.list_groups(section_key))
        # Neden: önerilen grup henüz yoksa adı "Yeni grup" kutusuna yazılır; yayınlanınca oluşturulur.
        if group_id == NO_GROUP:
            new_group = self.spec.suggested_group

        return {
            "title_tr": self.spec.title_tr,
            "title_en": self.spec.title_en,
            "section_key": section_key,
            "group_id": group_id,
            "new_group": new_group,
            "mode": self.spec.mode,
            "roles": list(self.spec.roles),
            "timeout": self.spec.timeout,
            "refresh": self.spec.refresh,
            "schedule": self.spec.schedule,
        }

    def render_placement(self) -> None:
        """Başlık, bölüm, grup, mod, rol ve süre alanlarını önerilerle doldurarak çizer."""
        sections = self.list_selectable_sections()
        values = self.compute_initial_values(sections)

        section_options = {}
        for section in sections:
            section_options[section["key"]] = self.menu.pick_label(section["name_tr"], section["name_en"])
        mode_options = {
            "form": t("script_engine.mode.form"),
            "live": t("script_engine.mode.live"),
            "scheduled": t("script_engine.mode.scheduled"),
        }
        role_names = self.list_role_names()
        # Neden süzülür: seçicide olmayan bir rol değeri hata verir (docstring'de yazım hatası olabilir).
        selected_roles = []
        for role in values["roles"]:
            if role in role_names:
                selected_roles.append(role)

        section_value = values["section_key"]
        if section_value not in section_options:
            section_value = None

        self.placement_container.clear()
        with self.placement_container:
            with ui.grid(columns=2).classes("w-full gap-4"):
                self.title_tr_input = ui.input(t("script_engine.wizard.title_tr"), value=values["title_tr"])
                self.title_tr_input.props("outlined").classes("w-full")
                self.title_en_input = ui.input(t("script_engine.wizard.title_en"), value=values["title_en"])
                self.title_en_input.props("outlined").classes("w-full")

                self.section_select = ui.select(
                    section_options,
                    label=t("script_engine.wizard.section"),
                    value=section_value,
                    on_change=self.on_section_change,
                )
                self.section_select.props("outlined").classes("w-full")
                group_options = self.build_group_options(section_value)
                group_value = values["group_id"]
                if group_value not in group_options:
                    group_value = NO_GROUP
                self.group_select = ui.select(
                    group_options, label=t("script_engine.wizard.group"), value=group_value
                )
                self.group_select.props("outlined").classes("w-full")

                self.new_group_input = ui.input(t("script_engine.wizard.new_group"), value=values["new_group"])
                self.new_group_input.props("outlined").classes("w-full")
                self.mode_select = ui.select(
                    mode_options,
                    label=t("script_engine.wizard.mode"),
                    value=values["mode"],
                    on_change=self.on_mode_change,
                )
                self.mode_select.props("outlined").classes("w-full")

                self.roles_select = ui.select(
                    role_names, label=t("script_engine.wizard.roles"), value=selected_roles, multiple=True
                )
                self.roles_select.props("outlined use-chips").classes("w-full")
                self.timeout_input = ui.number(
                    t("script_engine.wizard.timeout"), value=values["timeout"], min=1, precision=0
                )
                self.timeout_input.props("outlined").classes("w-full")

                self.refresh_input = ui.number(
                    t("script_engine.wizard.refresh"), value=values["refresh"], min=1, precision=0
                )
                self.refresh_input.props("outlined").classes("w-full")
                self.schedule_input = ui.input(t("script_engine.wizard.schedule"), value=values["schedule"])
                self.schedule_input.props("outlined").classes("w-full")
            ui.label(t("script_engine.wizard.roles_hint")).classes(LABEL_CLASSES)
        self.update_mode_fields()

    def on_section_change(self, event) -> None:
        """Bölüm değişince grup seçicisini o bölümün gruplarıyla doldurur."""
        self.group_select.set_options(self.build_group_options(event.value), value=NO_GROUP)

    def on_mode_change(self, event) -> None:
        """Mod değişince yalnızca ilgili süre alanlarını gösterir."""
        self.update_mode_fields()

    def update_mode_fields(self) -> None:
        """refresh yalnızca live, schedule yalnızca scheduled modunda görünür."""
        mode = self.mode_select.value
        self.refresh_input.set_visibility(mode == "live")
        self.schedule_input.set_visibility(mode == "scheduled")

    def on_publish_click(self) -> None:
        """Seçimleri doğrular, gerekirse yeni grubu oluşturur ve script'i yayınlar."""
        title_tr = (self.title_tr_input.value or "").strip()
        title_en = (self.title_en_input.value or "").strip()
        section_key = self.section_select.value
        if title_tr == "":
            ui.notify(t("script_engine.wizard.title_required"), type="warning")
            return
        if not section_key:
            ui.notify(t("script_engine.wizard.section_required"), type="warning")
            return

        timeout = int(self.timeout_input.value or 60)
        refresh = int(self.refresh_input.value or 30)
        schedule = (self.schedule_input.value or "").strip()
        new_group_name = (self.new_group_input.value or "").strip()
        was_new = self.entry is None

        try:
            group_id = self.group_select.value
            if new_group_name != "":
                group_id = self.menu.create_group(section_key, new_group_name, new_group_name)
            if group_id == NO_GROUP:
                group_id = None
            self.service.publish(
                self.script_id,
                title_tr,
                title_en,
                section_key,
                group_id,
                self.mode_select.value,
                list(self.roles_select.value or []),
                timeout,
                refresh,
                schedule,
                username=self.current_username(),
            )
        except ValueError as error:
            ui.notify(t("script_engine.error", message=str(error)), type="negative")
            return

        self.dialog.close()
        ui.notify(t("script_engine.published"), type="positive")
        # Neden yeni script'e gidilir: yan menü sayfa açılırken çizilir; yeni sayfaya
        # geçince script menüde (seçili olarak) görünür ve hemen denenebilir.
        # Neden panel o zaman yenilenmez: panel yenilenince bu dialog (ve tıklanan
        # düğme) silinir; silinmiş öğenin bağlamından yönlendirme yapılamaz.
        if was_new:
            ui.navigate.to("/script/" + self.script_id)
            return
        self.on_published()

    def current_username(self) -> str:
        """Giriş yapmış kullanıcının adını döndürür; "auth" yoksa boş metin."""
        auth = self.kernel.get_service("auth")
        if auth is None:
            return ""
        user = auth.current_user()
        if user is None:
            return ""
        return user["username"]
