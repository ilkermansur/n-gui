"""main.py - uygulamanın giriş noktası.

Kim kullanır: komut satırı (`python -m app.main [--config config.toml] [--only a,b]`).
Nasıl bağlanır: ayarları okur, kernel'i kurar, veritabanını hazırlar,
eklentileri yükler, tabloları oluşturur, "/" sayfasını kaydeder ve NiceGUI'yi başlatır.
Eklentiler kendi sayfalarını setup() sırasında @ui.page ile kaydeder.
"""

import argparse
import logging
import sys

from nicegui import ui

from app.core.access import check_page_access
from app.core.config import find_insecure_settings, load_config
from app.core.db import create_all_tables, init_database
from app.core.kernel import Kernel, get_kernel, set_kernel
from app.core.layout import create_shell_frame, get_current_user
from app.core.loader import load_plugins
from app.core.navigation import build_navigation_tree, find_first_page_path
from app.core.text import t
from app.core.widgets import empty_state, page_card


def parse_arguments() -> argparse.Namespace:
    """Komut satırı parametrelerini okur.

    --config: ayar dosyası (varsayılan config.toml).
    --only: virgülle ayrılmış eklenti listesi; verilirse yalnızca bunlar yüklenir.
    Dönüş: argparse.Namespace (config: str, only: list[str] | None).
    """
    parser = argparse.ArgumentParser(description="N-GUI modüler kabuk")
    parser.add_argument("--config", default="config.toml", help="ayar dosyasının yolu")
    parser.add_argument(
        "--only",
        default=None,
        help="yalnızca bu eklentileri yükle (virgülle ayrılmış, örnek: auth,i18n)",
    )
    arguments = parser.parse_args()

    if arguments.only is not None:
        only_list = []
        for name in arguments.only.split(","):
            name = name.strip()
            if name:
                only_list.append(name)
        arguments.only = only_list
    return arguments


@ui.page("/")
def home_page() -> None:
    """Ana sayfa: kullanıcının menüsündeki ilk sayfaya gider; menü boşsa boş kabuğu gösterir."""
    kernel = get_kernel()
    if not check_page_access(kernel, None):
        return

    user = get_current_user(kernel)
    tree = build_navigation_tree(kernel.collect_nav_items(user))
    first_path = find_first_page_path(tree)
    # Neden "/" hariç: ilk öğe ana sayfanın kendisiyse sonsuz yönlendirme olur.
    if first_path is not None and first_path != "/":
        ui.navigate.to(first_path)
        return

    content = create_shell_frame(kernel, kernel.config.app_title)
    with content:
        empty_state(t("shell.empty"))


def not_found_page() -> None:
    """Bulunamayan adresler için kabuk içinde "sayfa bulunamadı" kartı çizer.

    Kim çağırır: NiceGUI, eşleşen bir sayfa olmadığında (ui.run(root=...) ile bağlanır).
    Örnek: kapalı bir eklentinin sayfası (/log) ya da yanlış yazılmış bir adres.
    """
    kernel = get_kernel()
    if not check_page_access(kernel, None):
        return

    content = create_shell_frame(kernel, t("shell.not_found"))
    with content:
        with page_card().classes("items-center py-12"):
            ui.icon("search_off", size="48px").classes("text-slate-300 dark:text-slate-600")
            ui.label(t("shell.not_found")).classes(
                "text-lg font-semibold text-slate-700 dark:text-slate-200"
            )
            ui.button(t("shell.go_home"), icon="home", on_click=on_go_home_click).props("flat")


def on_go_home_click() -> None:
    """"Ana sayfaya dön" düğmesi: "/" adresine gider. Parametre ve dönüş yok."""
    ui.navigate.to("/")


def find_security_problems(kernel) -> list[str]:
    """Canlı ortamda kabul edilmeyecek güvenlik sorunlarını listeler.

    Parametre: kernel - ayarlar ve (varsa) "auth" servisi için.
    Dönüş: Türkçe sorun açıklamaları; boşsa sorun yok. Veritabanı hazır olduktan sonra
    çağrılmalıdır (admin parolası veritabanından kontrol edilir).
    """
    problems = find_insecure_settings(kernel.config)
    auth = kernel.get_service("auth")
    if auth is not None and auth.has_default_admin_password():
        problems.append(
            'admin kullanıcısı varsayılan "admin" parolasını kullanıyor; giriş yapıp '
            'kullanıcı menüsünden "Şifremi değiştir" ile değiştirin'
        )
    return problems


def enforce_security(kernel) -> None:
    """Güvenlik sorunlarını loglar; canlı ortamda ([app] environment = "production") varsa uygulamayı durdurur.

    Parametre: kernel. Dönüş: yok. Neden durdurulur: varsayılan gizli anahtar ve parola ile
    yayına çıkan bir uygulama, kodu bilen herkese açık demektir.
    """
    problems = find_security_problems(kernel)
    for problem in problems:
        logging.warning("Güvenlik: %s", problem)
    if problems and kernel.config.environment == "production":
        logging.critical("Canlı ortamda güvenlik sorunları var; uygulama açılmıyor.")
        sys.exit(1)


def main() -> None:
    """Uygulamayı sırasıyla kurar ve web sunucusunu başlatır. Dönüş: yok."""
    logging.basicConfig(level=logging.INFO)
    arguments = parse_arguments()

    config = load_config(arguments.config)
    kernel = Kernel(config)
    set_kernel(kernel)

    init_database(config.database_url)
    load_plugins(kernel, "plugins", "plugins", arguments.only)
    # Neden bu sırayla: eklentiler modellerini setup'ta import eder; tablolar ancak
    # hepsi yüklendikten sonra oluşturulabilir. "database.ready" olayını dinleyen
    # eklentiler (örn. seed verisi) tablolar hazır olunca çalışır.
    kernel.events.publish("plugins.loaded", {})
    create_all_tables()
    kernel.events.publish("database.ready", {})

    for plugin_id, status in kernel.plugin_status.items():
        logging.info("Eklenti %s: %s", plugin_id, status)
    enforce_security(kernel)

    # Neden root: NiceGUI eşleşmeyen her adreste root fonksiyonunu çağırır; böylece
    # İngilizce varsayılan 404 sayfası yerine kabuk içinde çevrilmiş bir sayfa görünür.
    ui.run(
        root=not_found_page,
        title=config.app_title,
        port=config.port,
        storage_secret=config.storage_secret,
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
