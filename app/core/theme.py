"""theme.py - uygulamanın bütün görünüm değerleri (renk, font, kart/sidebar/header sınıfları).

Kim kullanır: layout.py, widgets.py, access.py ve kendi sayfasını çizen eklentiler.
Nasıl bağlanır: renkler ve Tailwind sınıfları burada sabit olarak durur; görünümü
değiştirmek bu tek dosyayı düzenlemek demektir. Her sayfa çizilmeden önce
apply_theme() çağrılır (create_shell_frame bunu kendisi yapar).
"""

import json

from nicegui import app, ui

from app.core import kernel as kernel_module

# --- Renkler ---
# TailAdmin'in birincil mavisi; Quasar'da "primary" rengi olarak da kullanılır.
PRIMARY_COLOR = "#3C50E0"
# İçerik alanının açık gri zemini.
BACKGROUND_COLOR = "#F1F5F9"
# Koyu temada zemin (Tailwind slate-900).
DARK_BACKGROUND_COLOR = "#0F172A"
# Durum renkleri (yeşil, sarı, kırmızı).
POSITIVE_COLOR = "#10B981"
WARNING_COLOR = "#F59E0B"
NEGATIVE_COLOR = "#EF4444"

# --- Yazı tipi ---
FONT_FAMILY = "'Inter', sans-serif"
FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"'
    ' rel="stylesheet">'
)

# --- Tailwind sınıf grupları ---
# Not: beyaz zemin için "bg-white" yerine "bg-[#ffffff]" yazılır. Neden: Quasar
# "bg-white" sınıfını !important ile tanımlar; o zaman koyu temadaki
# "dark:bg-slate-800" hiç uygulanamaz. Aynı nedenle Quasar'ın renk sınıfları
# (bg-white, text-white, bg-primary ...) "dark:" karşılığı olan yerlerde kullanılmaz.
# Beyaz, yuvarlak köşeli, hafif gölgeli ve ince kenarlıklı kart.
CARD_CLASSES = (
    "bg-[#ffffff] dark:bg-slate-800 rounded-xl shadow-sm "
    "border border-slate-200 dark:border-slate-700 p-6"
)
# Sol menü: beyaz zemin, sağda ince çizgi.
SIDEBAR_CLASSES = (
    "bg-[#ffffff] dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 "
    "px-4 py-6 gap-1"
)
# Üst çubuk: beyaz, altta ince çizgi, koyu gri yazı.
HEADER_CLASSES = (
    "bg-[#ffffff] dark:bg-slate-800 text-slate-700 dark:text-slate-200 "
    "border-b border-slate-200 dark:border-slate-700 px-6 py-3 items-center gap-4"
)
# İçerik kolonu: kenar boşluklu, ortalanmış, kartlar arasında boşluk.
CONTENT_CLASSES = "w-full max-w-screen-2xl mx-auto p-6 gap-6"

# Sayfa başlığı ve metin sınıfları.
PAGE_TITLE_CLASSES = "text-xl font-semibold text-slate-800 dark:text-white"
LABEL_CLASSES = "text-sm text-slate-500 dark:text-slate-400"
VALUE_CLASSES = "text-3xl font-semibold text-slate-800 dark:text-white"

# Menü satırları: normal ve aktif (seçili sayfa) hali.
NAV_ITEM_CLASSES = (
    "w-full flex items-center gap-3 px-3 py-2 rounded-lg no-underline "
    "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
)
# Neden "text-[...]" ve "text-primary" değil: Quasar'ın text-primary sınıfı !important
# olduğu için koyu temada daha açık bir maviye geçilemezdi.
NAV_ITEM_ACTIVE_CLASSES = (
    "w-full flex items-center gap-3 px-3 py-2 rounded-lg no-underline font-semibold "
    "bg-indigo-50 text-[" + PRIMARY_COLOR + "] dark:bg-slate-700 dark:text-indigo-300"
)
# Katlanabilir menü grubunun başlık satırı (Quasar q-item'a header-class olarak verilir).
NAV_GROUP_HEADER_CLASSES = "rounded-lg px-3 text-slate-600 dark:text-slate-300"

# Durum rozetleri (pill): renk adı -> Tailwind sınıfları.
BADGE_BASE_CLASSES = "px-2.5 py-0.5 rounded-full text-xs font-medium"
BADGE_COLOR_CLASSES = {
    "green": "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-200",
    "yellow": "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200",
    "red": "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200",
    "gray": "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
}


def page_language() -> str:
    """O anki kullanıcının arayüz dilini döndürür.

    Dönüş: i18n servisinin dili; kernel ya da i18n yoksa config varsayılanı, o da yoksa "tr".
    """
    # Neden doğrudan alan okunur: get_kernel() hazır değilken hata fırlatır.
    kernel = kernel_module.current_kernel
    if kernel is None:
        return "tr"
    i18n = kernel.get_service("i18n")
    if i18n is None:
        return kernel.config.default_language
    return i18n.get_language()


def html_lang_script(language: str) -> str:
    """<html> öğesinin lang özelliğini ayarlayan betiği döndürür.

    Parametre: language - dil kodu ("tr" ya da "en"). Dönüş: <script> etiketi metni.
    """
    return "<script>document.documentElement.lang = " + json.dumps(language) + ";</script>"


def apply_theme() -> None:
    """O anki sayfaya font, renk, zemin ve koyu tema ayarını uygular.

    Her sayfanın başında bir kez çağrılır. Parametre ve dönüş yok.
    """
    ui.add_head_html(FONT_LINK)
    # Neden lang: Quasar düğme ve sekme yazılarını CSS ile büyük harfe çevirir; lang="tr"
    # olmadan tarayıcı "i" harfini "I" yapar ("GİRİŞ" yerine "GIRIŞ" görünür).
    ui.add_head_html(html_lang_script(page_language()))
    ui.colors(
        primary=PRIMARY_COLOR,
        positive=POSITIVE_COLOR,
        warning=WARNING_COLOR,
        negative=NEGATIVE_COLOR,
    )
    # Neden CSS ile: body'nin zemin rengi koyu temada da değişmeli; Quasar koyu
    # temada body'ye "body--dark" sınıfını ekler.
    ui.add_css(
        "body { background-color: " + BACKGROUND_COLOR + "; font-family: " + FONT_FAMILY + "; }\n"
        "body.body--dark { background-color: " + DARK_BACKGROUND_COLOR + "; }"
    )

    # Neden storage'a bağlanır: kullanıcının açık/koyu tema seçimi oturumlar
    # arasında saklanır; header'daki düğme yalnızca bu değeri değiştirir.
    if "dark_mode" not in app.storage.user:
        app.storage.user["dark_mode"] = False
    ui.dark_mode().bind_value(app.storage.user, "dark_mode")
