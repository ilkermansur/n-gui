"""login_page.py - /login sayfası (ortalanmış, TailAdmin tarzı giriş kartı).

Kim kullanır: plugin.py (bu modülü import etmesi sayfayı kaydeder).
Nasıl bağlanır: kabuk çerçevesi (menü/header) çizmez; kendi başına tam sayfadır,
bu yüzden apply_theme() çağrısını kendisi yapar. Giriş doğrulamasını "auth"
servisine yaptırır ve sonucu auth.login / auth.login_failed olaylarıyla duyurur.
"""

from nicegui import ui

from app.core.kernel import get_kernel
from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES, apply_theme
from app.core.widgets import page_card


class LoginForm:
    """Giriş formunun alanlarını ve buton davranışını bir arada tutar."""

    def __init__(self) -> None:
        """Alanlar henüz çizilmedi; build() çağrılınca oluşur. Dönüş: yok."""
        self.username_input = None
        self.password_input = None

    def build(self) -> None:
        """Başlığı, iki alanı ve giriş butonunu o anki kapsama çizer."""
        ui.icon("lock", size="40px").classes("text-indigo-500 self-center")
        ui.label(t("auth.login.title")).classes(PAGE_TITLE_CLASSES + " self-center")
        ui.label(t("auth.login.subtitle")).classes(LABEL_CLASSES + " self-center text-center")

        self.username_input = ui.input(t("auth.login.username")).props("outlined dense")
        self.username_input.classes("w-full")
        self.password_input = ui.input(
            t("auth.login.password"), password=True, password_toggle_button=True
        ).props("outlined dense")
        self.password_input.classes("w-full")
        # Neden Enter'a da bağlı: kullanıcı fareye uzanmadan giriş yapabilsin.
        self.password_input.on("keydown.enter", self.on_login_click)
        self.username_input.on("keydown.enter", self.on_login_click)

        ui.button(t("auth.login.button"), on_click=self.on_login_click).classes("w-full")

    def on_login_click(self) -> None:
        """Bilgileri doğrular; başarılıysa oturumu açıp "/" sayfasına gider.

        Hatalı girişte bildirim gösterir ve auth.login_failed olayını yayınlar.
        Parametre ve dönüş yok.
        """
        kernel = get_kernel()
        auth = kernel.get_service("auth")
        username = self.username_input.value or ""
        password = self.password_input.value or ""

        user = auth.authenticate(username, password)
        if user is None:
            kernel.events.publish("auth.login_failed", {"username": username.lower().strip()})
            ui.notify(t("auth.login.failed"), type="negative")
            return

        auth.login_user(user)
        kernel.events.publish("auth.login", {"username": user["username"]})
        ui.navigate.to("/")


# Neden modül seviyesinde: bu dosya plugin.py setup'ında import edilir; @ui.page
# import anında sayfayı kaydeder, iç içe fonksiyona gerek kalmaz.
@ui.page("/login")
def login_page() -> None:
    """Giriş sayfası: zaten girişliyse ana sayfaya yönlendirir."""
    apply_theme()
    kernel = get_kernel()
    auth = kernel.get_service("auth")
    if auth.current_user() is not None:
        ui.navigate.to("/")
        return

    # Zemin rengini apply_theme() verir; burada Quasar renk sınıfı kullanılmaz.
    with ui.column().classes("w-full min-h-screen items-center justify-center p-4"):
        with page_card().classes("max-w-md gap-4"):
            LoginForm().build()
