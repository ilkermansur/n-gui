"""layout.py - her sayfanın ortak çerçevesi: üst çubuk (header), sol menü (sidebar) ve içerik kolonu.

Kim kullanır: çekirdek sayfalar ("/" sayfası, access.py) ve eklenti sayfaları.
Nasıl bağlanır: bir sayfa önce check_page_access ile yetkiyi kontrol eder,
sonra create_shell_frame(kernel, başlık) çağırır ve dönen kolonun içine
(`with content:`) kendi kartlarını çizer. Menü öğeleri kernel'in nav
provider'larından, kullanıcı bilgisi "auth" servisinden, dil "i18n" servisinden gelir.
Bu servisler yoksa (örneğin --only none) çerçeve yine çizilir.
"""

from nicegui import app, events, ui

from app.core.kernel import get_kernel
from app.core.navigation import NavNode, build_navigation_tree, flatten_navigation_tree
from app.core.text import t
from app.core.theme import (
    CONTENT_CLASSES,
    HEADER_CLASSES,
    NAV_ITEM_ACTIVE_CLASSES,
    NAV_GROUP_CLASS,
    NAV_GROUP_HEADER_CLASSES,
    NAV_ITEM_CLASSES,
    PAGE_TITLE_CLASSES,
    SIDEBAR_CLASSES,
    apply_theme,
)


def get_current_user(kernel) -> dict | None:
    """Giriş yapmış kullanıcıyı "auth" servisinden alır.

    Parametre: kernel - çekirdek. Dönüş: kullanıcı sözlüğü; servis ya da kullanıcı yoksa None.
    """
    auth = kernel.get_service("auth")
    if auth is None:
        return None
    return auth.current_user()


# app.storage.client içinde, açık sayfanın menüsünü yeniden çizen fonksiyonun anahtarı.
NAVIGATION_REDRAW_KEY = "redraw_navigation"


def create_shell_frame(kernel, page_title: str) -> ui.column:
    """Temayı uygular, header ve sidebar'ı çizer, içerik kolonunu döndürür.

    Parametreler: kernel - çekirdek; page_title - header'da görünen sayfa başlığı.
    Dönüş: sayfa içeriğinin çizileceği ui.column (kullanım: `with content:`).
    """
    apply_theme()

    user = get_current_user(kernel)
    # Neden request yolu: "/script/{id}" gibi parametreli sayfalarda page.path
    # şablonu verir; menüdeki gerçek yol ile karşılaştırmak için istenen adres gerekir.
    current_path = ui.context.client.request.url.path

    # Neden önce drawer: header'daki menü düğmesi drawer'ı açıp kapatabilsin.
    drawer, nav_column = draw_sidebar(kernel)
    search = draw_header(kernel, page_title, user, drawer)

    def redraw_navigation() -> None:
        """Menü ağacını ve arama seçeneklerini kullanıcının güncel yetkileriyle yeniden çizer."""
        tree = build_navigation_tree(kernel.collect_nav_items(get_current_user(kernel)))
        nav_column.clear()
        with nav_column:
            for node in tree:
                render_nav_node(node, current_path)
        search.set_options(build_search_options(tree))

    redraw_navigation()
    # Neden client deposu: menüyü değiştiren paneller (script, bölüm, rol) aynı sayfada
    # refresh_navigation() çağırınca sidebar sayfa yenilenmeden güncellenir.
    app.storage.client[NAVIGATION_REDRAW_KEY] = redraw_navigation

    return ui.column().classes(CONTENT_CLASSES)


def refresh_navigation() -> None:
    """Açık sayfanın sol menüsünü ve aramasını yeniden çizer.

    Kim çağırır: menüyü etkileyen bir değişiklikten sonra ayar panelleri (script yayınlama,
    kaldırma, bölüm ve grup düzenleme, rol izinleri). Sayfa create_shell_frame ile
    çizilmemişse hiçbir şey yapmaz. Diğer kullanıcılar değişikliği bir sonraki sayfada görür.
    Dikkat: tıklanan düğmeyi silen bir yeniden çizimden (panel.render()) ÖNCE çağrılmalıdır;
    silinmiş düğmenin bağlamından açık sayfa bulunamaz.
    """
    redraw = app.storage.client.get(NAVIGATION_REDRAW_KEY)
    if redraw is not None:
        redraw()


def build_search_options(tree: list[NavNode]) -> dict:
    """Aramada önerilecek sayfaları "adres -> etiket" sözlüğü olarak döndürür.

    Parametre: tree - menü ağacı. Neden ağaçtan: sahipsiz öğeler menüde olmadığı gibi
    aramada da çıkmamalı.
    """
    options = {}
    for item in flatten_navigation_tree(tree):
        if item.path:
            options[item.path] = item.label
    return options


def draw_sidebar(kernel) -> tuple[ui.left_drawer, ui.column]:
    """Sol menüyü çizer: üstte logo/uygulama adı, altında menü ağacı için boş bir kolon.

    Parametre: kernel - çekirdek (uygulama adı için).
    Dönüş: (ui.left_drawer, menü kolonu). Menü ağacını create_shell_frame bu kolona çizer.
    """
    # Neden value=None: geniş ekranda açık, dar ekranda kapalı başlar (Quasar "show-if-above").
    # Neden top_corner=True: sidebar ekranın tam boyunu kaplar, header onun sağında kalır.
    with ui.left_drawer(value=None, top_corner=True).classes(SIDEBAR_CLASSES) as drawer:
        with ui.row().classes("items-center gap-2 px-3 pb-6"):
            ui.icon("dashboard", size="28px").classes("text-primary")
            ui.label(kernel.config.app_title).classes(
                "text-xl font-bold text-slate-800 dark:text-white"
            )
        nav_column = ui.column().classes("w-full gap-1")
    return drawer, nav_column


def render_nav_node(node: NavNode, current_path: str) -> None:
    """Bir menü düğümünü çizer; çocukları varsa kendini tekrar çağırır.

    Parametreler: node - çizilecek düğüm; current_path - açık sayfanın adresi.
    Çocuğu olan düğüm katlanabilir bir ui.expansion, olmayan düğüm bir bağlantı satırı olur.
    Dönüş: yok.
    """
    item = node.item

    if len(node.children) > 0:
        # Neden: aktif sayfa bu grubun altındaysa grup açık başlar.
        is_open = node_contains_path(node, current_path)
        expansion = ui.expansion(item.label, icon=item.icon, value=is_open)
        expansion.classes("w-full text-sm " + NAV_GROUP_CLASS)
        expansion.props('dense header-class="' + NAV_GROUP_HEADER_CLASSES + '"')
        with expansion:
            with ui.column().classes("w-full gap-1 pl-4"):
                for child in node.children:
                    render_nav_node(child, current_path)
        return

    if item.path == current_path:
        row_classes = NAV_ITEM_ACTIVE_CLASSES
    else:
        row_classes = NAV_ITEM_CLASSES

    icon_name = item.icon
    if not icon_name:
        icon_name = "chevron_right"

    with ui.link(target=item.path).classes(row_classes):
        ui.icon(icon_name, size="20px")
        ui.label(item.label).classes("text-sm")


def node_contains_path(node: NavNode, path: str) -> bool:
    """Düğümün kendisi ya da altındaki bir düğüm verilen adrese mi gidiyor?

    Parametreler: node - aranacak düğüm; path - aranan adres.
    Dönüş: bulunursa True.
    """
    if node.item.path == path:
        return True
    for child in node.children:
        if node_contains_path(child, path):
            return True
    return False


def draw_header(kernel, page_title: str, user: dict | None, drawer) -> ui.select:
    """Üst çubuğu çizer: menü düğmesi, başlık, arama, dil, tema ve kullanıcı menüsü.

    Parametreler: kernel - çekirdek; page_title - sayfa başlığı; user - kullanıcı ya da None;
    drawer - açıp kapatılacak sidebar.
    Dönüş: arama kutusu (seçeneklerini create_shell_frame menüyle birlikte doldurur).
    """
    # Neden düğmelerde color=None: Quasar renk sınıfları koyu temada değişmez;
    # renksiz düğmeler header'ın yazı rengini (açık/koyu) devralır.
    with ui.header().classes(HEADER_CLASSES):
        ui.button(icon="menu", color=None, on_click=drawer.toggle).props("flat round dense")
        ui.label(page_title).classes(PAGE_TITLE_CLASSES + " truncate min-w-0")

        ui.space()

        # Arama: seçenekler "adres -> etiket" sözlüğüdür; seçim yapılınca o adrese gidilir.
        search = ui.select({}, label=t("shell.search"), with_input=True, on_change=on_search_select)
        search.props("outlined dense clearable options-dense")
        # Neden gt-xs: telefonda (600px altı) gizlenir, üst çubuk tek satıra sığar; sayfalara
        # menüden gidilir. Tailwind "hidden md:block" olmaz: Quasar'ın .hidden sınıfı !important'tır.
        search.classes("w-64 gt-xs")

        # Dil düğmesi: şu anki dili gösterir, tıklanınca diğer dile geçer.
        language_button = ui.button(
            current_language(kernel).upper(), color=None, on_click=on_language_click
        )
        language_button.props("flat dense")
        language_button.tooltip(t("shell.language"))

        # Tema düğmesi: ikon ve ipucu, saklanan dark_mode değerine bağlıdır (ay / güneş).
        theme_button = ui.button(color=None, on_click=on_dark_mode_click)
        theme_button.props("flat round dense")
        theme_button.bind_icon_from(app.storage.user, "dark_mode", backward=dark_mode_icon)
        with theme_button:
            theme_tooltip = ui.tooltip()
        theme_tooltip.bind_text_from(app.storage.user, "dark_mode", backward=dark_mode_tooltip)

        if user is not None:
            draw_user_menu(user)
    return search


def draw_user_menu(user: dict) -> None:
    """Sağ üstteki kullanıcı avatarını ve açılır menüsünü (Çıkış) çizer.

    Parametre: user - "auth" servisinden gelen kullanıcı sözlüğü. Dönüş: yok.
    """
    display_name = user.get("full_name") or user.get("username") or ""
    initial = display_name[:1].upper()

    with ui.button(color=None).props("flat no-caps dense"):
        # Neden içine label: ui.avatar'ın ilk parametresi ikon adıdır; baş harf metin olarak eklenir.
        with ui.avatar(color="primary", text_color="white", size="32px"):
            ui.label(initial).classes("text-sm font-semibold")
        # Neden gt-xs: telefonda yalnızca avatar kalır, üst çubuk taşmaz.
        ui.label(display_name).classes("ml-2 text-sm font-medium gt-xs")
        with ui.menu():
            ui.menu_item(t("shell.logout"), on_click=on_logout_click)


def current_language(kernel) -> str:
    """Şu anki arayüz dilini döndürür.

    Parametre: kernel - çekirdek. Dönüş: "tr" ya da "en"; i18n servisi yoksa config varsayılanı.
    """
    i18n = kernel.get_service("i18n")
    if i18n is None:
        return kernel.config.default_language
    return i18n.get_language()


def dark_mode_icon(dark_mode_enabled) -> str:
    """Tema düğmesinin ikonunu seçer.

    Parametre: dark_mode_enabled - saklanan dark_mode değeri.
    Dönüş: koyu tema açıksa "light_mode" (güneş), değilse "dark_mode" (ay).
    """
    if dark_mode_enabled:
        return "light_mode"
    return "dark_mode"


def dark_mode_tooltip(dark_mode_enabled) -> str:
    """Tema düğmesinin ipucunu seçer: düğmeye basınca geçilecek temayı söyler.

    Parametre: dark_mode_enabled - saklanan dark_mode değeri.
    Dönüş: koyu tema açıksa "Açık tema", değilse "Koyu tema" (aktif dilde).
    """
    if dark_mode_enabled:
        return t("shell.light_mode")
    return t("shell.dark_mode")


def on_search_select(event: events.ValueChangeEventArguments) -> None:
    """Aramada bir öğe seçilince o sayfaya gider.

    Parametre: event - seçilen değer (sayfa adresi) event.value içindedir. Dönüş: yok.
    """
    # Neden kontrol: "temizle" düğmesi de on_change tetikler ve değer None olur.
    if event.value:
        ui.navigate.to(event.value)


def on_language_click() -> None:
    """TR ve EN arasında geçiş yapar ve sayfayı yeniden yükler. Dönüş: yok."""
    kernel = get_kernel()
    i18n = kernel.get_service("i18n")
    if i18n is None:
        return
    if i18n.get_language() == "tr":
        i18n.set_language("en")
    else:
        i18n.set_language("tr")
    # Neden yenilenir: tüm metinler t() ile çizim anında çevrildiği için sayfa baştan çizilmeli.
    ui.navigate.reload()


def on_dark_mode_click() -> None:
    """Açık/koyu temayı değiştirir. Dönüş: yok.

    ui.dark_mode bu değere bağlı olduğu için tema hemen değişir.
    """
    app.storage.user["dark_mode"] = not app.storage.user.get("dark_mode", False)


def on_logout_click() -> None:
    """Kullanıcının oturumunu kapatır ve giriş sayfasına gider. Dönüş: yok."""
    auth = get_kernel().get_service("auth")
    if auth is not None:
        auth.logout_current_user()
    ui.navigate.to("/login")
