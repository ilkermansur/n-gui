"""access.py - sayfa açılırken giriş ve yetki kontrolü.

Kim kullanır: her sayfa fonksiyonu, ilk satırında:
    `if not check_page_access(kernel, "<izin>"): return`
Nasıl bağlanır: kontrol "auth" servisi üzerinden yapılır. Servis yoksa
(auth eklentisi yüklenmemişse) her sayfa açıktır.
"""

from nicegui import ui

from app.core.layout import create_shell_frame
from app.core.text import t
from app.core.widgets import page_card


def check_page_access(kernel, permission: str | None) -> bool:
    """Kullanıcının bu sayfayı görüp göremeyeceğine karar verir.

    Parametreler: kernel - çekirdek; permission - gereken izin anahtarı,
    None ise giriş yapmış olmak yeterlidir.
    Dönüş: True ise sayfa çizilmeye devam eder. False ise sayfa durmalıdır:
    kullanıcı yoksa /login'e yönlendirilmiştir, izni yoksa "yetkiniz yok" kartı çizilmiştir.
    """
    auth = kernel.get_service("auth")
    if auth is None:
        return True

    user = auth.current_user()
    if user is None:
        ui.navigate.to("/login")
        return False

    if permission is None:
        return True
    if auth.has_permission(user, permission):
        return True

    # Neden çerçeve de çizilir: kullanıcı menüyü kullanıp başka sayfaya geçebilsin.
    content = create_shell_frame(kernel, t("shell.forbidden"))
    with content:
        with page_card().classes("items-center py-12"):
            ui.icon("lock", size="48px").classes("text-red-400")
            ui.label(t("shell.forbidden")).classes(
                "text-lg font-semibold text-slate-700 dark:text-slate-200"
            )
    return False
