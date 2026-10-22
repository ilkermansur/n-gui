"""script_page.py - /script/{script_id} sayfası: script'i moduna göre çalıştırır ve sonucu gösterir.

Kim kullanır: plugin.py (bu modülü import etmesi sayfayı kaydeder); menüdeki
script öğeleri bu adrese gider.
Nasıl bağlanır: önce check_page_access ile giriş, sonra "scripts" servisinin
can_user_run kuralıyla yetki denetlenir. Form "forms" servisiyle çizilir.
Script, arayüzü kilitlememek için `await run.io_bound(service.execute, ...)` ile
ayrı bir thread'de çalıştırılır. Modlar:
- form: form kartı -> "Çalıştır" -> sonuç kartı
- live: varsayılan değerlerle açılışta bir kez ve her `refresh` saniyede bir çalışır
- scheduled: elle çalıştırma formu ve geçmiş çalıştırmalar tablosu
"""

from datetime import datetime

from nicegui import run, ui

from app.core.access import check_page_access
from app.core.kernel import get_kernel
from app.core.layout import create_shell_frame
from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import page_card, status_badge
from plugins.script_engine.result_view import show_empty_result, show_result, show_run_texts


def user_may_run(kernel, service, entry: dict) -> bool:
    """Giriş yapmış kullanıcı bu kaydı çalıştırabilir mi? "auth" yoksa herkes çalıştırır."""
    auth = kernel.get_service("auth")
    if auth is None:
        return True
    return service.can_user_run(auth.current_user(), entry)


def draw_message_page(kernel, icon: str, text: str) -> None:
    """Kabuk çerçevesi içinde ortalanmış ikonlu tek bir mesaj kartı çizer.

    Parametreler: kernel; icon - Material ikon adı; text - mesaj. Dönüş: yok.
    """
    content = create_shell_frame(kernel, text)
    with content:
        with page_card().classes("items-center py-12"):
            ui.icon(icon, size="48px").classes("text-red-400")
            ui.label(text).classes("text-lg font-semibold text-slate-700 dark:text-slate-200")


def format_time(value) -> str:
    """datetime değerini "2026-10-22 08:00:05" biçiminde metne çevirir; None ise boş."""
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def draw_run_header(success: bool, duration_ms: int, started_text: str) -> None:
    """Sonuç kartının üst satırını çizer: başlık, başarı rozeti, süre ve zaman."""
    with ui.row().classes("w-full items-center gap-3"):
        ui.label(t("script_engine.result")).classes("text-lg font-semibold text-slate-800 dark:text-white")
        if success:
            status_badge(t("script_engine.status_success"), "green")
        else:
            status_badge(t("script_engine.status_failed"), "red")
        ui.space()
        ui.label(t("script_engine.duration", ms=duration_ms)).classes(LABEL_CLASSES)
        if started_text:
            ui.label(started_text).classes(LABEL_CLASSES)


class ScriptPageView:
    """Bir script sayfasının durumunu (form, sonuç kartı, zamanlayıcı) tutar."""

    def __init__(self, kernel, service, entry: dict) -> None:
        """Parametreler: kernel; service - "scripts" servisi; entry - yayın kaydı."""
        self.kernel = kernel
        self.service = service
        self.entry = entry
        self.script_id = entry["script_id"]
        self.spec = None
        self.form = None
        self.run_button = None
        self.spinner = None
        self.result_container = None
        self.runs_table = None
        self.runs_by_id = {}
        self.timer = None
        self.live_first_run_done = False
        self.updated_label = None
        self.run_dialog = None

    # ---------- Çizim ----------

    def build(self) -> None:
        """Başlık kartını ve moda göre gövdeyi çizer."""
        self.spec = self.service.parse(self.script_id)
        self.draw_header_card()
        if self.spec.error != "":
            with page_card():
                show_run_texts("", self.spec.error)
            return

        mode = self.entry["mode"]
        if mode == "live":
            self.build_live()
        elif mode == "scheduled":
            self.build_form_card()
            self.result_container = ui.column().classes("w-full gap-4")
            self.build_runs_card()
        else:
            self.build_form_card()
            self.result_container = ui.column().classes("w-full gap-4")

    def draw_header_card(self) -> None:
        """Başlık, açıklama, mod rozeti ve (varsa) zamanlama bilgisini çizer."""
        with page_card().classes("gap-2"):
            with ui.row().classes("w-full items-center gap-3"):
                ui.label(self.service.pick_title(self.entry)).classes(PAGE_TITLE_CLASSES)
                status_badge(t("script_engine.mode." + self.entry["mode"]), "gray")
            if self.spec.description:
                ui.label(self.spec.description).classes(LABEL_CLASSES + " whitespace-pre-wrap")
            if self.entry["mode"] == "scheduled" and self.entry["schedule"]:
                ui.label(t("script_engine.schedule_info", schedule=self.entry["schedule"])).classes(LABEL_CLASSES)

    def build_form_card(self) -> None:
        """Form kartını, "Çalıştır" düğmesini ve spinner'ı çizer."""
        forms = self.kernel.get_service("forms")
        with page_card().classes("gap-4"):
            if len(self.spec.fields) == 0:
                ui.label(t("script_engine.no_inputs")).classes(LABEL_CLASSES)
            self.form = forms.build_form(self.spec.fields)
            with ui.row().classes("items-center gap-3"):
                self.run_button = ui.button(t("script_engine.run"), icon="play_arrow", on_click=self.on_run_click)
                self.spinner = ui.spinner(size="md")
                self.spinner.set_visibility(False)

    def build_live(self) -> None:
        """Canlı mod: bilgi satırı, sonuç alanı ve yenileme zamanlayıcısı."""
        with page_card().classes("gap-1"):
            with ui.row().classes("w-full items-center gap-3"):
                ui.icon("monitor_heart", size="20px").classes("text-primary")
                ui.label(t("script_engine.live_info", seconds=self.entry["refresh"])).classes(LABEL_CLASSES)
                ui.space()
                self.spinner = ui.spinner(size="sm")
                self.spinner.set_visibility(False)
                self.updated_label = ui.label("").classes(LABEL_CLASSES)
        self.result_container = ui.column().classes("w-full gap-4")
        with self.result_container:
            show_empty_result()
        # Neden durdurmaya gerek yok: ui.timer bir sayfa öğesidir. İstemci ayrılınca
        # NiceGUI sayfanın öğelerini siler; Timer._handle_delete zamanlayıcıyı (o an
        # süren çağrıyla birlikte) iptal eder ve _should_stop() istemci yoksa döngüyü
        # bitirir (nicegui/elements/timer.py). Not: NiceGUI istemciyi, yeniden
        # bağlanabilsin diye birkaç saniye bekledikten sonra siler; bu arada bir
        # tetiklenme daha olabilir. immediate=True olduğu için ilk
        # çalıştırma sayfa açılınca hemen yapılır.
        self.timer = ui.timer(self.entry["refresh"], self.refresh_live_result)

    def build_runs_card(self) -> None:
        """Geçmiş çalıştırmalar tablosunu çizer; satıra tıklayınca sonuç dialogu açılır."""
        columns = [
            {"name": "started_at", "label": t("script_engine.col.time"), "field": "started_at", "align": "left"},
            {"name": "username", "label": t("script_engine.col.user"), "field": "username", "align": "left"},
            {"name": "status", "label": t("script_engine.col.status"), "field": "status", "align": "left"},
            {"name": "duration_ms", "label": t("script_engine.col.duration"), "field": "duration_ms", "align": "right"},
        ]
        with page_card().classes("gap-2"):
            ui.label(t("script_engine.history")).classes("text-lg font-semibold text-slate-800 dark:text-white")
            self.runs_table = ui.table(columns=columns, rows=[], row_key="id").classes("w-full").props("flat")
            # Neden slot: durum düz metin değil renkli rozet olmalı (Quasar badge).
            self.runs_table.add_slot(
                "body-cell-status",
                '<q-td :props="props">'
                '<q-badge rounded :color="props.row.success ? \'positive\' : \'negative\'"'
                ' :label="props.value" />'
                "</q-td>",
            )
            self.runs_table.on("rowClick", self.on_run_row_click)
        self.refresh_runs_table()

    # ---------- Çalıştırma ----------

    def collect_default_values(self) -> dict:
        """Canlı mod için alanların varsayılan değerlerinden argüman sözlüğü üretir."""
        values = {}
        for field in self.spec.fields:
            values[field.name] = field.default
        return values

    async def on_run_click(self) -> None:
        """Formu doğrular, script'i ayrı thread'de çalıştırır ve sonucu çizer."""
        values, errors = self.form.submit()
        if len(errors) > 0:
            ui.notify(t("script_engine.form_invalid"), type="warning")
            return
        # Neden kilit: çalışma sürerken ikinci tıklama aynı script'i yeniden başlatmasın.
        self.run_button.disable()
        self.spinner.set_visibility(True)
        try:
            result = await run.io_bound(
                self.service.execute, self.script_id, values, self.service.current_username()
            )
        finally:
            self.run_button.enable()
            self.spinner.set_visibility(False)
        # io_bound, uygulama kapanırken ya da iptal edilince None döndürür.
        if result is None:
            return
        self.draw_result(result)
        if self.runs_table is not None:
            self.refresh_runs_table()

    async def refresh_live_result(self) -> None:
        """Canlı mod zamanlayıcısının her tetiklenişinde script'i çalıştırıp sonucu yeniden çizer."""
        # Neden: yalnızca sayfa açılışındaki ilk çalıştırma geçmişe yazılır; periyodik
        # yenilemeler yalnızca başarısız olursa kaydedilir (Log dolmasın).
        record_success = not self.live_first_run_done
        self.live_first_run_done = True
        self.spinner.set_visibility(True)
        try:
            result = await run.io_bound(
                self.service.execute,
                self.script_id,
                self.collect_default_values(),
                self.service.current_username(),
                record_success=record_success,
            )
        finally:
            self.spinner.set_visibility(False)
        if result is None:
            return
        self.draw_result(result)
        self.updated_label.set_text(t("script_engine.updated_at", time=format_time_now()))

    def draw_result(self, result) -> None:
        """RunResult'ı sonuç kartı olarak çizer (önceki sonucu siler)."""
        self.result_container.clear()
        with self.result_container:
            with page_card().classes("gap-4"):
                draw_run_header(result.success, result.duration_ms, "")
                if result.success:
                    show_result(result.result, result.output_text, result.error_text)
                else:
                    show_run_texts(result.output_text, result.error_text)

    # ---------- Geçmiş ----------

    def refresh_runs_table(self) -> None:
        """Geçmiş tablosunu servisten yeniden okur."""
        rows = []
        self.runs_by_id = {}
        for run_item in self.service.list_runs(self.script_id):
            self.runs_by_id[run_item["id"]] = run_item
            if run_item["success"]:
                status_text = t("script_engine.status_success")
            else:
                status_text = t("script_engine.status_failed")
            rows.append(
                {
                    "id": run_item["id"],
                    "started_at": format_time(run_item["started_at"]),
                    "username": run_item["username"],
                    "status": status_text,
                    "success": run_item["success"],
                    "duration_ms": run_item["duration_ms"],
                }
            )
        self.runs_table.rows = rows
        self.runs_table.update()

    def on_run_row_click(self, event) -> None:
        """Tıklanan geçmiş satırının sonucunu bir dialogda gösterir.

        Parametre: event - Quasar rowClick olayı; event.args = [olay, satır, sıra].
        """
        row = event.args[1]
        run_item = self.runs_by_id.get(row["id"])
        if run_item is None:
            return
        with ui.dialog() as self.run_dialog:
            with page_card().classes("min-w-[600px] max-w-[90vw] gap-4"):
                draw_run_header(run_item["success"], run_item["duration_ms"], format_time(run_item["started_at"]))
                if run_item["success"]:
                    show_result(run_item["result"], run_item["output_text"], run_item["error_text"])
                else:
                    show_run_texts(run_item["output_text"], run_item["error_text"])
                with ui.row().classes("w-full justify-end"):
                    ui.button(t("script_engine.close"), on_click=self.run_dialog.close).props("flat")
        self.run_dialog.open()


def format_time_now() -> str:
    """Şu anki saati "08:00:05" biçiminde döndürür."""
    return datetime.now().strftime("%H:%M:%S")


@ui.page("/script/{script_id}")
def script_page(script_id: str) -> None:
    """Script sayfası: giriş ve çalıştırma yetkisi kontrolü, çerçeve ve moda göre gövde."""
    kernel = get_kernel()
    if not check_page_access(kernel, None):
        return

    service = kernel.get_service("scripts")
    entry = service.get_entry(script_id)
    # Neden "bulunamadı": devre dışı ya da kaldırılmış script'in sayfası açılmamalı.
    if entry is None or not entry["is_enabled"]:
        draw_message_page(kernel, "search_off", t("script_engine.not_found"))
        return
    if not user_may_run(kernel, service, entry):
        draw_message_page(kernel, "lock", t("shell.forbidden"))
        return

    content = create_shell_frame(kernel, service.pick_title(entry))
    with content:
        ScriptPageView(kernel, service, entry).build()
