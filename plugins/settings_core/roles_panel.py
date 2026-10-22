"""roles_panel.py - Ayarlar > Roller paneli: rol seç, izinleri onay kutularıyla düzenle, kaydet.

Kim kullanır: plugin.py paneli SettingsPanel olarak kaydeder; /settings sayfası
build_roles_panel() fonksiyonunu yetki kontrolünden sonra çağırır.
Nasıl bağlanır: roller "auth" servisinden, seçilebilir izinler
kernel.list_permissions() sonucundan gelir.
"""

from nicegui import ui

from app.core.kernel import get_kernel
from app.core.layout import refresh_navigation
from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import page_card
from plugins.settings_core.changes import publish_settings_changed


class RolesEditor:
    """Rol seçicisini ve izin onay kutularını yöneten panel."""

    def __init__(self) -> None:
        """Servisi ve izin listesini alır. Dönüş: yok."""
        self.kernel = get_kernel()
        self.auth = self.kernel.get_service("auth")
        self.container = None
        self.selected_role: str | None = None
        # İzin anahtarı -> onay kutusu (seçili rol çizilince doldurulur).
        self.checkboxes: dict = {}
        self.dialog = None
        self.name_input = None

    def build(self) -> None:
        """Kapsayıcıyı oluşturur ve ilk kez çizer."""
        self.container = ui.column().classes("w-full gap-4")
        self.render()

    def find_role(self, name: str | None) -> dict | None:
        """Adı verilen rolün sözlüğünü döndürür; yoksa None."""
        for role in self.auth.list_roles():
            if role["name"] == name:
                return role
        return None

    def render(self) -> None:
        """Rol seçicisini ve seçili rolün izin kutularını yeniden çizer."""
        self.container.clear()
        self.checkboxes = {}
        role_names = []
        for role in self.auth.list_roles():
            role_names.append(role["name"])
        if self.selected_role not in role_names:
            self.selected_role = None
        selected = self.find_role(self.selected_role)

        with self.container:
            with page_card():
                ui.label(t("settings.roles.title")).classes(PAGE_TITLE_CLASSES)
                with ui.row().classes("items-center gap-2"):
                    role_select = ui.select(role_names, value=self.selected_role,
                                            label=t("settings.roles.select")).classes("w-64")
                    role_select.on_value_change(self.on_role_changed)
                    ui.button(t("settings.roles.add"), icon="add", on_click=self.open_add_dialog).props("flat")
                if selected is None:
                    ui.label(t("settings.roles.select_hint")).classes(LABEL_CLASSES)
                    return
                self.draw_permissions(selected)

    def draw_permissions(self, role: dict) -> None:
        """Seçili rol için izin onay kutularını ve Kaydet düğmesini çizer.

        Parametre: role - {"name", "permissions"} sözlüğü.
        """
        if "*" in role["permissions"]:
            # Neden uyarı: "*" her izni kapsar; kutular bunu göstermez.
            ui.label(t("settings.roles.wildcard_note")).classes(LABEL_CLASSES)
        ui.label(t("settings.roles.permissions")).classes(LABEL_CLASSES)
        permissions = self.kernel.list_permissions()
        for key in sorted(permissions.keys()):
            label = key + " — " + t(permissions[key])
            self.checkboxes[key] = ui.checkbox(label, value=key in role["permissions"])
        with ui.row().classes("gap-2"):
            ui.button(t("settings.save"), icon="save", on_click=self.on_save_click)
            # Neden admin'de yok: admin rolü silinemez; düğmeyi göstermek yanıltıcı olurdu.
            if role["name"] != "admin":
                ui.button(t("settings.roles.delete"), icon="delete",
                          on_click=self.open_delete_dialog).props("flat color=negative")

    def on_role_changed(self, event) -> None:
        """Rol seçicisi değişince seçili rolü saklar ve paneli yeniden çizer.

        Parametre: event - değer değişim olayı (event.value yeni rol adı).
        """
        self.selected_role = event.value
        self.render()

    def on_save_click(self) -> None:
        """İşaretli izinleri seçili role yazar; kayıtlı olmayan izinler korunur."""
        role = self.find_role(self.selected_role)
        if role is None:
            return
        new_permissions = []
        # Neden korunur: "*" ya da yüklü olmayan eklentinin izni kutularda yoktur, silinmemeli.
        for permission in role["permissions"]:
            if permission not in self.checkboxes:
                new_permissions.append(permission)
        for key in sorted(self.checkboxes.keys()):
            if self.checkboxes[key].value:
                new_permissions.append(key)
        try:
            self.auth.set_role_permissions(self.selected_role, new_permissions)
        except ValueError as error:
            ui.notify(t("settings.error", message=str(error)), type="negative")
            return
        publish_settings_changed("roles", "rol izinleri güncellendi: " + self.selected_role)
        ui.notify(t("settings.saved"), type="positive")
        # Neden: kendi rolünüzün izinleri değiştiyse sol menü buna göre değişir.
        refresh_navigation()

    def open_add_dialog(self) -> None:
        """Yeni rol adı için dialog açar."""
        with ui.dialog() as self.dialog:
            with page_card().classes("min-w-[320px] gap-2"):
                ui.label(t("settings.roles.add")).classes(PAGE_TITLE_CLASSES)
                self.name_input = ui.input(t("settings.roles.name")).props("outlined dense")
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("settings.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("settings.save"), on_click=self.on_save_new_role_click)
        self.dialog.open()

    def on_save_new_role_click(self) -> None:
        """Yeni rolü oluşturup seçer; hatayı bildirimle gösterir."""
        name = (self.name_input.value or "").strip()
        try:
            self.auth.create_role(name)
        except ValueError as error:
            ui.notify(t("settings.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        self.selected_role = name
        publish_settings_changed("roles", "rol eklendi: " + name)
        ui.notify(t("settings.saved"), type="positive")
        self.render()

    def open_delete_dialog(self) -> None:
        """Seçili rolü silmek için onay dialogu açar."""
        with ui.dialog() as self.dialog:
            with page_card().classes("gap-2"):
                ui.label(t("settings.roles.confirm_delete", name=self.selected_role))
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("settings.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("settings.roles.delete"), on_click=self.on_confirm_delete).props("color=negative")
        self.dialog.open()

    def on_confirm_delete(self) -> None:
        """Onaydan sonra rolü siler; kullanıcıya atanmışsa servis hatasını bildirimle gösterir."""
        name = self.selected_role
        try:
            self.auth.delete_role(name)
        except ValueError as error:
            self.dialog.close()
            ui.notify(t("settings.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        self.selected_role = None
        publish_settings_changed("roles", "rol silindi: " + name)
        ui.notify(t("settings.roles.deleted"), type="positive")
        self.render()


def build_roles_panel() -> None:
    """"Roller" ayar panelini o anki NiceGUI kapsamına çizer. Parametre ve dönüş yok."""
    RolesEditor().build()
