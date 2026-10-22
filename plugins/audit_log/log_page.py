"""log_page.py - /log sayfası: işlem kayıtlarını süzüp tabloda gösterir.

Kim kullanır: plugin.py (bu modülü import etmesi sayfayı kaydeder).
Nasıl bağlanır: "audit" servisinin search() sonucunu ui.table'da çizer.
Süzgeçler: durum, metin ve tarih aralığı. Tablo 50'şer satırlık sayfalara bölünür.
Durum hücresi rozet olarak görünür; sayfa "log.view" izni ister.
"""

from nicegui import ui

from app.core.access import check_page_access
from app.core.kernel import get_kernel
from app.core.layout import create_shell_frame
from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import page_card
from plugins.audit_log.service import SEARCH_LIMIT

# Durum seçicisindeki "hepsi" değeri.
STATUS_ALL = "all"
# Tablonun bir sayfasındaki satır sayısı.
ROWS_PER_PAGE = 50


class LogView:
    """Sayfadaki süzgeç kontrolleri ile tabloyu bir arada tutar."""

    def __init__(self, audit) -> None:
        """Parametre: audit - "audit" servisi."""
        self.audit = audit
        self.status_select = None
        self.search_input = None
        self.date_from_input = None
        self.date_to_input = None
        self.count_label = None
        self.table = None

    def build(self) -> None:
        """Süzgeç satırını ve tabloyu çizer. Dönüş: yok."""
        status_options = {
            STATUS_ALL: t("audit_log.status_all"),
            "ok": t("audit_log.status_ok"),
            "error": t("audit_log.status_error"),
        }
        with ui.row().classes("w-full items-end gap-4"):
            self.status_select = ui.select(
                status_options, value=STATUS_ALL, label=t("audit_log.col.status")
            ).classes("w-44")
            self.search_input = ui.input(label=t("audit_log.search")).classes("w-72")
            self.search_input.on("keydown.enter", self.refresh)
            # Neden type=date: tarayıcının kendi tarih seçicisi açılır, değer "YYYY-MM-DD" gelir.
            self.date_from_input = ui.input(label=t("audit_log.date_from")).props("type=date stack-label")
            self.date_to_input = ui.input(label=t("audit_log.date_to")).props("type=date stack-label")
            ui.button(t("audit_log.refresh"), icon="refresh", on_click=self.refresh)
        self.count_label = ui.label("").classes(LABEL_CLASSES)

        columns = [
            {"name": "created_at", "label": t("audit_log.col.time"), "field": "created_at", "align": "left"},
            {"name": "username", "label": t("audit_log.col.user"), "field": "username", "align": "left"},
            {"name": "action", "label": t("audit_log.col.action"), "field": "action", "align": "left"},
            {"name": "target", "label": t("audit_log.col.target"), "field": "target", "align": "left"},
            {"name": "status", "label": t("audit_log.col.status"), "field": "status", "align": "left"},
            {"name": "duration_ms", "label": t("audit_log.col.duration"), "field": "duration_ms", "align": "right"},
            {"name": "details", "label": t("audit_log.col.details"), "field": "details", "align": "left"},
        ]
        self.table = ui.table(
            columns=columns, rows=[], row_key="id", pagination={"rowsPerPage": ROWS_PER_PAGE}
        ).classes("w-full")
        # Neden slot: durum hücresi düz metin değil renkli rozet olmalı (Quasar badge).
        self.table.add_slot(
            "body-cell-status",
            '<q-td :props="props">'
            '<q-badge :color="props.value === \'ok\' ? \'positive\' : \'negative\'"'
            ' :label="props.value === \'ok\' ? \'OK\' : \'ERROR\'" />'
            "</q-td>",
        )
        self.refresh()

    def refresh(self) -> None:
        """Seçili süzgeçlere göre kayıtları yeniden okur ve tabloyu günceller. Dönüş: yok."""
        status = self.status_select.value
        if status == STATUS_ALL:
            status = None
        rows = self.audit.search(
            status,
            self.search_input.value or "",
            date_from=self.date_from_input.value or "",
            date_to=self.date_to_input.value or "",
        )
        self.table.rows = rows
        self.table.update()
        # Neden uyarı: arama sınırına ulaşıldıysa daha eski kayıtlar vardır; süzgeç daraltılmalı.
        if len(rows) >= SEARCH_LIMIT:
            self.count_label.set_text(t("audit_log.limit_reached", count=len(rows)))
        else:
            self.count_label.set_text(t("audit_log.count", count=len(rows)))


@ui.page("/log")
def log_page() -> None:
    """Log sayfası: izin kontrolü, çerçeve, süzgeçler ve tablo."""
    kernel = get_kernel()
    if not check_page_access(kernel, "log.view"):
        return

    content = create_shell_frame(kernel, t("audit_log.title"))
    with content:
        ui.label(t("audit_log.title")).classes(PAGE_TITLE_CLASSES)
        with page_card().classes("gap-4"):
            LogView(kernel.get_service("audit")).build()
