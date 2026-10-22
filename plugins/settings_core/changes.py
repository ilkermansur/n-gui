"""changes.py - ayar panellerinin ortak yardımcısı: "settings.changed" olayını yayınlar.

Kim kullanır: users_panel.py, roles_panel.py, database_panel.py.
Nasıl bağlanır: olayı kernel.events ile yayınlar; audit_log eklentisi bu olayı
dinleyip işlem kaydı yazar. Olayda asla parola bulunmaz.
"""

from app.core.kernel import get_kernel


def publish_settings_changed(setting: str, details: str) -> None:
    """Bir ayar değiştiğini duyurur.

    Parametreler: setting - değişen ayarın adı ("users", "roles", "database");
    details - kısa açıklama (parola ya da gizli bilgi içermemeli).
    Dönüş: yok.
    """
    kernel = get_kernel()
    auth = kernel.get_service("auth")
    username = ""
    if auth is not None:
        user = auth.current_user()
        if user is not None:
            username = user["username"]
    kernel.events.publish(
        "settings.changed",
        {"username": username, "setting": setting, "details": details},
    )
