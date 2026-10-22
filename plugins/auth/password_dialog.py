"""password_dialog.py - kullanıcının kendi parolasını değiştirdiği dialog.

Kim kullanır: plugin.py, open_change_password_dialog fonksiyonunu kullanıcı menüsüne
("Şifremi değiştir") UserMenuItem olarak ekler.
Nasıl bağlanır: işi "auth" servisinin change_own_password metoduna yaptırır; mevcut parola
doğru değilse ya da yeni parola kurala uymuyorsa servis ValueError fırlatır ve hata
bildirimle gösterilir. Başarılı değişiklik "auth.password_changed" olayıyla duyurulur
(audit_log kaydeder); olayda parola bulunmaz.
"""

from nicegui import ui

from app.core.kernel import get_kernel
from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import page_card


class ChangePasswordDialog:
    """Mevcut parola, yeni parola ve tekrarı alanlarını ve Kaydet davranışını tutar."""

    def __init__(self) -> None:
        """Servisi alır; alanlar open() ile oluşur. Dönüş: yok."""
        self.kernel = get_kernel()
        self.auth = self.kernel.get_service("auth")
        self.dialog = None
        self.current_input = None
        self.new_input = None
        self.repeat_input = None

    def open(self) -> None:
        """Dialogu çizip açar."""
        with ui.dialog() as self.dialog:
            with page_card().classes("min-w-[360px] gap-2"):
                ui.label(t("auth.password.title")).classes(PAGE_TITLE_CLASSES)
                hint = t("auth.password.hint", min=self.kernel.config.min_password_length)
                ui.label(hint).classes(LABEL_CLASSES)
                self.current_input = self.create_password_input(t("auth.password.current"))
                self.new_input = self.create_password_input(t("auth.password.new"))
                self.repeat_input = self.create_password_input(t("auth.password.repeat"))
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("auth.password.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("auth.password.save"), on_click=self.on_save_click)
        self.dialog.open()

    def create_password_input(self, label: str) -> ui.input:
        """Göster/gizle düğmeli, tam genişlik bir parola kutusu döndürür. Parametre: label."""
        widget = ui.input(label, password=True, password_toggle_button=True)
        return widget.props("outlined dense").classes("w-full")

    def on_save_click(self) -> None:
        """Yeni parolaları karşılaştırır, servise kaydettirir ve sonucu bildirir."""
        user = self.auth.current_user()
        if user is None:
            self.dialog.close()
            return
        new_password = self.new_input.value or ""
        if new_password != (self.repeat_input.value or ""):
            ui.notify(t("auth.password.mismatch"), type="warning")
            return
        try:
            self.auth.change_own_password(user["id"], self.current_input.value or "", new_password)
        except ValueError as error:
            ui.notify(t("auth.password.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        self.kernel.events.publish("auth.password_changed", {"username": user["username"]})
        ui.notify(t("auth.password.changed"), type="positive")


def open_change_password_dialog() -> None:
    """Kullanıcı menüsündeki "Şifremi değiştir" satırının handler'ı. Parametre ve dönüş yok."""
    ChangePasswordDialog().open()
