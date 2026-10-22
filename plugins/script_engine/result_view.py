"""result_view.py - script sonucunu türüne göre ekrana çizen fonksiyonlar.

Kim kullanır: script_page.py (çalıştırma sonucu ve geçmiş dialogu).
Nasıl bağlanır: show_result() o anki NiceGUI kapsamına (with bloğu) çizer.
Kurallar:
- Skaler değerlerden oluşan dict -> stat_card grid'i
- dict listesi -> ui.table
- str -> ui.code
- diğerleri -> salt okunur ui.json_editor
Script'in print çıktısı katlanabilir bir bölümde, hata metni kırmızı bir kartta gösterilir.
"""

import json

from nicegui import ui

from app.core.text import t
from app.core.theme import LABEL_CLASSES
from app.core.widgets import stat_card

# Kırmızı hata kartı: theme.py'deki kart yapısının kırmızı tonlu hali.
ERROR_CARD_CLASSES = (
    "w-full rounded-xl border border-red-200 dark:border-red-800 "
    "bg-red-50 dark:bg-red-950 p-4 gap-2"
)
SCALAR_TYPES = (str, int, float, bool)


def is_scalar(value) -> bool:
    """Değer tek bir kartta gösterilebilecek basit bir değer mi (metin, sayı, bool, None)?"""
    if value is None:
        return True
    return isinstance(value, SCALAR_TYPES)


def is_scalar_dict(value) -> bool:
    """Değer, bütün değerleri skaler olan boş olmayan bir dict mi?"""
    if not isinstance(value, dict) or len(value) == 0:
        return False
    for item in value.values():
        if not is_scalar(item):
            return False
    return True


def is_dict_list(value) -> bool:
    """Değer, bütün öğeleri dict olan boş olmayan bir liste mi?"""
    if not isinstance(value, list) or len(value) == 0:
        return False
    for item in value:
        if not isinstance(item, dict):
            return False
    return True


def display_value(value):
    """Skaler bir değeri ekranda gösterilecek hale getirir.

    Parametre: value - metin, sayı, bool ya da None.
    Dönüş: bool için aktif dilde "Evet"/"Hayır", None için "-", diğerleri aynen.
    """
    # Neden önce bool: Python'da True bir int'tir; sayı gibi gösterilmesin.
    if isinstance(value, bool):
        if value:
            return t("shell.yes")
        return t("shell.no")
    if value is None:
        return "-"
    return value


def cell_text(value):
    """Tablo hücresine konacak değeri hazırlar; iç içe yapılar JSON metnine çevrilir."""
    if is_scalar(value):
        return display_value(value)
    return json.dumps(value, default=str, ensure_ascii=False)


def show_stat_cards(result: dict) -> None:
    """Skaler dict'i her anahtar için bir istatistik kartı olarak çizer."""
    with ui.row().classes("w-full gap-4"):
        for key, value in result.items():
            stat_card(str(key), display_value(value))


def show_table(rows: list) -> None:
    """dict listesini sütunları anahtarlardan üretilen bir tablo olarak çizer."""
    # Sütunlar ilk görüldükleri sırayla toplanır; bazı satırlarda olmayan anahtarlar boş kalır.
    column_names = []
    for row in rows:
        for key in row.keys():
            if str(key) not in column_names:
                column_names.append(str(key))

    columns = []
    for name in column_names:
        columns.append({"name": name, "label": name, "field": name, "align": "left", "sortable": True})

    table_rows = []
    for index in range(len(rows)):
        table_row = {"_row_index": index}
        for key, value in rows[index].items():
            table_row[str(key)] = cell_text(value)
        table_rows.append(table_row)

    ui.table(columns=columns, rows=table_rows, row_key="_row_index").classes("w-full").props("flat")


def show_result(result, output_text: str = "", error_text: str = "") -> None:
    """Script sonucunu türüne göre çizer; çıktı ve hata metnini de altına ekler.

    Parametreler: result - run() dönüş değeri (JSON'dan çözülmüş);
    output_text - script'in print çıktısı; error_text - hata/uyarı metni.
    Dönüş: yok.
    """
    if is_scalar_dict(result):
        show_stat_cards(result)
    elif is_dict_list(result):
        show_table(result)
    elif isinstance(result, str):
        ui.code(result, language="text").classes("w-full")
    else:
        # Neden readOnly: sonuç yalnızca gösterilir, kullanıcı değiştiremez.
        editor = ui.json_editor({"content": {"json": result}, "readOnly": True})
        editor.classes("w-full")
    show_run_texts(output_text, error_text)


def show_run_texts(output_text: str, error_text: str) -> None:
    """Çıktıyı katlanabilir bölümde, hatayı kırmızı kartta çizer; boş olanlar çizilmez."""
    if output_text:
        with ui.expansion(t("script_engine.output"), icon="terminal").classes("w-full"):
            ui.code(output_text, language="text").classes("w-full")
    if error_text:
        with ui.column().classes(ERROR_CARD_CLASSES):
            with ui.row().classes("items-center gap-2"):
                ui.icon("error", size="20px").classes("text-red-500")
                ui.label(t("script_engine.error_title")).classes(
                    "font-semibold text-red-700 dark:text-red-200"
                )
            ui.label(error_text).classes(
                "whitespace-pre-wrap font-mono text-xs text-red-700 dark:text-red-200"
            )


def show_empty_result() -> None:
    """Henüz sonuç yokken küçük bir bilgi metni çizer."""
    ui.label(t("script_engine.no_result")).classes(LABEL_CLASSES)
