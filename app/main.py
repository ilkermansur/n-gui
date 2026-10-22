"""main.py - uygulamanın giriş noktası.

Kim kullanır: komut satırı (`python -m app.main [--config config.toml] [--only a,b]`).
Nasıl bağlanır: ayarları okur, kernel'i kurar, veritabanını hazırlar,
eklentileri yükler, tabloları oluşturur, "/" sayfasını kaydeder ve NiceGUI'yi başlatır.
Eklentiler kendi sayfalarını setup() sırasında @ui.page ile kaydeder.
"""

import argparse
import logging

from nicegui import ui

from app.core.access import check_page_access
from app.core.config import load_config
from app.core.db import create_all_tables, init_database
from app.core.kernel import Kernel, get_kernel, set_kernel
from app.core.layout import create_shell_frame, get_current_user
from app.core.loader import load_plugins
from app.core.navigation import build_navigation_tree, find_first_page_path
from app.core.text import t
from app.core.widgets import empty_state


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

    ui.run(
        title=config.app_title,
        port=config.port,
        storage_secret=config.storage_secret,
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
