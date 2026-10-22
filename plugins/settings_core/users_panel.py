"""users_panel.py - Ayarlar > Kullanıcılar paneli: tablo, ekle/düzenle, şifre sıfırla, aktif/pasif.

Kim kullanır: plugin.py paneli SettingsPanel olarak kaydeder; /settings sayfası
build_users_panel() fonksiyonunu yetki kontrolünden sonra çağırır.
Nasıl bağlanır: bütün işi "auth" servisine yaptırır. Panel bir sınıftır
(UsersEditor); her değişiklikten sonra kendini baştan çizer. Servisin
fırlattığı ValueError (örn. kısa parola) ui.notify ile gösterilir.
"""

from nicegui import ui

from app.core.kernel import get_kernel
from app.core.layout import refresh_navigation
from app.core.text import t
from app.core.theme import LABEL_CLASSES, PAGE_TITLE_CLASSES
from app.core.widgets import page_card
from plugins.settings_core.changes import publish_settings_changed


class UsersEditor:
    """Kullanıcı tablosunu ve dialogları yöneten panel."""

    def __init__(self) -> None:
        """Servisi alır, alanları boş bırakır. Dönüş: yok."""
        self.auth = get_kernel().get_service("auth")
        self.container = None
        self.table = None
        self.selected_user_id: int | None = None
        # Dialog alanları: dialog açılınca doldurulur.
        self.dialog = None
        self.username_input = None
        self.full_name_input = None
        self.password_input = None
        self.roles_select = None
        self.active_switch = None

    # ---------- Çizim ----------

    def build(self) -> None:
        """Kapsayıcıyı oluşturur ve ilk kez çizer."""
        self.container = ui.column().classes("w-full gap-4")
        self.render()

    def render(self) -> None:
        """Kapsayıcıyı temizleyip kullanıcı tablosunu yeniden çizer."""
        self.container.clear()
        columns = [
            {"name": "username", "label": t("settings.users.col.username"), "field": "username", "align": "left"},
            {"name": "full_name", "label": t("settings.users.col.full_name"), "field": "full_name", "align": "left"},
            {"name": "roles", "label": t("settings.users.col.roles"), "field": "roles", "align": "left"},
            {"name": "active", "label": t("settings.users.col.active"), "field": "active"},
        ]
        rows = []
        for user in self.auth.list_users():
            rows.append(
                {
                    "id": user["id"],
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "roles": ", ".join(user["roles"]),
                    "active": "✓" if user["is_active"] else "—",
                }
            )

        with self.container:
            with page_card():
                ui.label(t("settings.users.title")).classes(PAGE_TITLE_CLASSES)
                with ui.row().classes("gap-2"):
                    ui.button(t("settings.add"), icon="add", on_click=self.open_add_dialog)
                    ui.button(t("settings.edit"), icon="edit", on_click=self.open_edit_dialog).props("flat")
                    ui.button(t("settings.users.reset_password"), icon="key",
                              on_click=self.open_password_dialog).props("flat")
                    ui.button(t("settings.users.toggle_active"), icon="toggle_on",
                              on_click=self.on_toggle_active_click).props("flat")
                self.table = ui.table(columns=columns, rows=rows, row_key="id", selection="single",
                                      on_select=self.on_selection_changed)
                self.table.classes("w-full")
                # Neden seçili satır korunur: yeniden çizimden sonra aynı kullanıcı seçili kalsın.
                if self.selected_user_id is not None:
                    for row in rows:
                        if row["id"] == self.selected_user_id:
                            self.table.selected = [row]

    # ---------- Seçim ve yardımcılar ----------

    def on_selection_changed(self, event) -> None:
        """Tablo seçimi değişince seçili kullanıcı kimliğini saklar.

        Parametre: event - NiceGUI olayı (kullanılmaz; seçim table.selected'dan okunur).
        """
        if self.table.selected:
            self.selected_user_id = self.table.selected[0]["id"]
        else:
            self.selected_user_id = None

    def find_selected_user(self) -> dict | None:
        """Seçili kullanıcının sözlüğünü döndürür; seçim yoksa uyarı verip None döner."""
        if self.selected_user_id is None:
            ui.notify(t("settings.users.select_user"), type="warning")
            return None
        for user in self.auth.list_users():
            if user["id"] == self.selected_user_id:
                return user
        ui.notify(t("settings.users.select_user"), type="warning")
        return None

    def role_names(self) -> list[str]:
        """Sistemdeki tüm rol adlarını döndürür (rol seçicisi için)."""
        names = []
        for role in self.auth.list_roles():
            names.append(role["name"])
        return names

    # ---------- Ekle / düzenle ----------

    def open_add_dialog(self) -> None:
        """Yeni kullanıcı dialogunu açar."""
        with ui.dialog() as self.dialog:
            with page_card().classes("min-w-[360px] gap-2"):
                ui.label(t("settings.users.add_title")).classes(PAGE_TITLE_CLASSES)
                self.username_input = ui.input(t("settings.users.col.username")).props("outlined dense")
                self.full_name_input = ui.input(t("settings.users.col.full_name")).props("outlined dense")
                self.password_input = ui.input(t("settings.users.password"), password=True,
                                               password_toggle_button=True).props("outlined dense")
                self.roles_select = ui.select(self.role_names(), value=[], multiple=True,
                                              label=t("settings.users.col.roles")).props("outlined dense use-chips")
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("settings.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("settings.save"), on_click=self.on_save_new_user_click)
        self.dialog.open()

    def on_save_new_user_click(self) -> None:
        """Dialogdaki yeni kullanıcıyı oluşturur; hatayı bildirimle gösterir."""
        username = (self.username_input.value or "").strip()
        try:
            self.auth.create_user(
                username,
                (self.full_name_input.value or "").strip(),
                self.password_input.value or "",
                list(self.roles_select.value or []),
            )
        except ValueError as error:
            ui.notify(t("settings.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        publish_settings_changed("users", "kullanıcı eklendi: " + username.lower())
        ui.notify(t("settings.saved"), type="positive")
        self.render()

    def open_edit_dialog(self) -> None:
        """Seçili kullanıcının adını, aktiflik durumunu ve rollerini düzenleme dialogunu açar."""
        user = self.find_selected_user()
        if user is None:
            return
        with ui.dialog() as self.dialog:
            with page_card().classes("min-w-[360px] gap-2"):
                ui.label(t("settings.users.edit_title") + ": " + user["username"]).classes(PAGE_TITLE_CLASSES)
                self.full_name_input = ui.input(t("settings.users.col.full_name"),
                                                value=user["full_name"]).props("outlined dense")
                self.roles_select = ui.select(self.role_names(), value=user["roles"], multiple=True,
                                              label=t("settings.users.col.roles")).props("outlined dense use-chips")
                self.active_switch = ui.switch(t("settings.users.col.active"), value=user["is_active"])
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("settings.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("settings.save"), on_click=self.on_save_edit_click)
        self.dialog.open()

    def on_save_edit_click(self) -> None:
        """Düzenleme dialogundaki bilgileri kaydeder; kendi hesabını pasif yapmayı engeller."""
        current = self.auth.current_user()
        if current is not None and current["id"] == self.selected_user_id and not self.active_switch.value:
            # Neden engellenir: kendini pasif yapan yönetici sistemin dışında kalır.
            ui.notify(t("settings.users.cannot_deactivate_self"), type="warning")
            return
        try:
            self.auth.update_user(
                self.selected_user_id,
                (self.full_name_input.value or "").strip(),
                bool(self.active_switch.value),
                list(self.roles_select.value or []),
            )
        except ValueError as error:
            ui.notify(t("settings.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        publish_settings_changed("users", "kullanıcı güncellendi (id " + str(self.selected_user_id) + ")")
        ui.notify(t("settings.saved"), type="positive")
        # Neden: kendi rollerinizi değiştirdiyseniz sol menü buna göre değişir. Önce menü
        # yenilenir; render() tıklanan düğmeyi silince NiceGUI bağlamı bulunamaz.
        refresh_navigation()
        self.render()

    # ---------- Şifre sıfırla ----------

    def open_password_dialog(self) -> None:
        """Seçili kullanıcı için yeni şifre dialogunu açar."""
        user = self.find_selected_user()
        if user is None:
            return
        with ui.dialog() as self.dialog:
            with page_card().classes("min-w-[360px] gap-2"):
                ui.label(t("settings.users.reset_password") + ": " + user["username"]).classes(PAGE_TITLE_CLASSES)
                ui.label(t("settings.users.password_hint", min=get_kernel().config.min_password_length)).classes(LABEL_CLASSES)
                self.password_input = ui.input(t("settings.users.password"), password=True,
                                               password_toggle_button=True).props("outlined dense")
                with ui.row().classes("justify-end w-full"):
                    ui.button(t("settings.cancel"), on_click=self.dialog.close).props("flat")
                    ui.button(t("settings.save"), on_click=self.on_save_password_click)
        self.dialog.open()

    def on_save_password_click(self) -> None:
        """Yeni şifreyi kaydeder; kural hatasını bildirimle gösterir. Şifre olaya yazılmaz."""
        try:
            self.auth.change_password(self.selected_user_id, self.password_input.value or "")
        except ValueError as error:
            ui.notify(t("settings.error", message=str(error)), type="negative")
            return
        self.dialog.close()
        publish_settings_changed("users", "şifre sıfırlandı (id " + str(self.selected_user_id) + ")")
        ui.notify(t("settings.saved"), type="positive")

    # ---------- Aktif / pasif ----------

    def on_toggle_active_click(self) -> None:
        """Seçili kullanıcının aktiflik durumunu tersine çevirir; kendini pasif yapamaz."""
        user = self.find_selected_user()
        if user is None:
            return
        current = self.auth.current_user()
        if current is not None and current["id"] == user["id"] and user["is_active"]:
            ui.notify(t("settings.users.cannot_deactivate_self"), type="warning")
            return
        try:
            self.auth.update_user(user["id"], user["full_name"], not user["is_active"], user["roles"])
        except ValueError as error:
            ui.notify(t("settings.error", message=str(error)), type="negative")
            return
        publish_settings_changed("users", "aktiflik değişti (id " + str(user["id"]) + ")")
        self.render()


def build_users_panel() -> None:
    """"Kullanıcılar" ayar panelini o anki NiceGUI kapsamına çizer. Parametre ve dönüş yok."""
    UsersEditor().build()
