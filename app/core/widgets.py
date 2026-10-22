"""widgets.py - sayfalarda tekrar eden küçük görsel parçalar (kart, istatistik, rozet, boş durum).

Kim kullanır: çekirdek sayfalar (layout, access, main) ve tüm eklentiler.
Nasıl bağlanır: her fonksiyon o anki NiceGUI kapsamına (with bloğu) bir öğe çizer.
Stil değerleri theme.py'den gelir; böylece her sayfa aynı görünür.
"""

from nicegui import ui

from app.core.theme import (
    BADGE_BASE_CLASSES,
    BADGE_COLOR_CLASSES,
    CARD_CLASSES,
    LABEL_CLASSES,
    VALUE_CLASSES,
)


def page_card() -> ui.card:
    """İçerik için beyaz, yuvarlak köşeli tam genişlik bir kart döndürür.

    Kullanım: `with page_card(): ...`. Dönüş: ui.card.
    """
    # Neden "flat": Quasar'ın kendi gölgesi yerine theme.py'deki hafif gölge kullanılır.
    return ui.card().props("flat").classes(CARD_CLASSES + " w-full")


# İstatistik kartında gösterilecek en uzun değer; uzun metin kesilir, tamamı ipucunda görünür.
STAT_VALUE_MAX_LENGTH = 40


def shorten_stat_value(text: str) -> str:
    """Uzun değeri STAT_VALUE_MAX_LENGTH karaktere kısaltır ve sonuna "…" ekler.

    Parametre: text - gösterilecek metin. Dönüş: kısa metin (kısaysa aynısı).
    """
    if len(text) <= STAT_VALUE_MAX_LENGTH:
        return text
    return text[:STAT_VALUE_MAX_LENGTH] + "…"


def stat_card(title: str, value, hint: str = "") -> None:
    """Dashboard için istatistik kartı çizer: küçük etiket, büyük sayı, isteğe bağlı rozet.

    Parametreler: title - etiket; value - gösterilecek değer (str'ye çevrilir);
    hint - sayının altında küçük bir rozet metni (örnek "+%12"), boşsa çizilmez.
    Dönüş: yok.
    """
    with ui.card().props("flat").classes(CARD_CLASSES + " min-w-[220px] flex-1 gap-2"):
        ui.label(title).classes(LABEL_CLASSES)
        value_text = str(value)
        # Neden break-all: boşluksuz uzun değerler (yol, URL) kartın dışına taşmasın.
        value_label = ui.label(shorten_stat_value(value_text)).classes(VALUE_CLASSES + " break-all")
        if len(value_text) > STAT_VALUE_MAX_LENGTH:
            value_label.tooltip(value_text)
        if hint:
            status_badge(hint, "green")


def status_badge(text: str, color: str) -> None:
    """Renkli, yuvarlak (pill) bir durum rozeti çizer.

    Parametreler: text - rozet yazısı; color - "green", "yellow", "red" veya "gray".
    Bilinmeyen renk gri kabul edilir. Dönüş: yok.
    """
    color_classes = BADGE_COLOR_CLASSES.get(color, BADGE_COLOR_CLASSES["gray"])
    ui.label(text).classes(BADGE_BASE_CLASSES + " " + color_classes)


def empty_state(text: str) -> None:
    """Gösterilecek bir şey olmadığında ortalanmış ikon ve mesaj içeren bir kart çizer.

    Parametre: text - gösterilecek mesaj. Dönüş: yok.
    """
    with page_card().classes("items-center py-12"):
        ui.icon("inbox", size="48px").classes("text-slate-300 dark:text-slate-600")
        ui.label(text).classes(LABEL_CLASSES)
