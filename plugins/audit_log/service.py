"""service.py - "audit" servisi: işlem kaydı yazma, arama ve olay dinleyicileri.

Kim kullanır: plugin.py (kaydeder), log_page.py (arama) ve diğer eklentiler
kernel.get_service("audit") ile (write).
Nasıl bağlanır: olaylara subscribe_events() ile abone olur. Handler'lar worker
thread'den de çağrılabilir (scriptler run.io_bound ile çalışır); bu yüzden her
çağrı kendi oturumunu get_session() ile açar, hiçbir oturum paylaşılmaz.
"""

from sqlalchemy import or_, select

from app.core.db import get_session
from plugins.audit_log.models import AuditEntry

# details alanı bu uzunluktan fazlaysa kırpılır.
MAX_DETAILS_LENGTH = 4000


def entry_to_dict(entry: AuditEntry) -> dict:
    """AuditEntry kaydını sözlüğe çevirir. Parametre: entry. Dönüş: sözlük."""
    return {
        "id": entry.id,
        "created_at": entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "username": entry.username,
        "action": entry.action,
        "target": entry.target,
        "status": entry.status,
        "duration_ms": entry.duration_ms,
        "details": entry.details,
    }


class AuditService:
    """İşlem kayıtlarının tek sahibi."""

    def __init__(self, kernel) -> None:
        """Servisi kurar. Parametre: kernel - olay yoluna erişmek için."""
        self.kernel = kernel

    def write(
        self,
        username: str,
        action: str,
        target: str = "",
        status: str = "ok",
        duration_ms: int = 0,
        details: str = "",
    ) -> None:
        """Bir işlem kaydı yazar.

        Parametreler: username - işlemi yapan; action - işlem adı; target - hedef
        (script adı gibi); status - "ok" ya da "error"; duration_ms - süre;
        details - ek açıklama (4000 karakterde kırpılır). Dönüş: yok.
        """
        entry = AuditEntry(
            username=username,
            action=action,
            target=target,
            status=status,
            duration_ms=duration_ms,
            details=details[:MAX_DETAILS_LENGTH],
        )
        # Neden her seferinde yeni oturum: çağrı başka bir thread'den gelebilir.
        with get_session() as session:
            session.add(entry)
            session.commit()

    def search(self, status: str | None, text: str, limit: int = 500) -> list[dict]:
        """Kayıtları filtreleyip en yeni önce olacak şekilde döndürür.

        Parametreler: status - "ok"/"error" ya da None (hepsi); text - kullanıcı,
        işlem, hedef veya detayda aranan metin (boşsa süzme yok); limit - en fazla kayıt.
        Dönüş: sözlük listesi.
        """
        query = select(AuditEntry)
        if status:
            query = query.where(AuditEntry.status == status)
        if text:
            pattern = "%" + text + "%"
            query = query.where(
                or_(
                    AuditEntry.username.ilike(pattern),
                    AuditEntry.action.ilike(pattern),
                    AuditEntry.target.ilike(pattern),
                    AuditEntry.details.ilike(pattern),
                )
            )
        # Neden id de sıralanır: aynı saniyedeki kayıtlarda yeni olan önce gelsin.
        query = query.order_by(AuditEntry.created_at.desc(), AuditEntry.id.desc()).limit(limit)
        with get_session() as session:
            entries = session.scalars(query).all()
        result = []
        for entry in entries:
            result.append(entry_to_dict(entry))
        return result

    # ---------- Olay dinleyicileri ----------

    def subscribe_events(self) -> None:
        """Bu servisin dinlediği tüm olaylara abone olur. Dönüş: yok."""
        events = self.kernel.events
        events.subscribe("auth.login", self.on_auth_login)
        events.subscribe("auth.login_failed", self.on_auth_login_failed)
        events.subscribe("auth.logout", self.on_auth_logout)
        events.subscribe("script.finished", self.on_script_finished)
        events.subscribe("scripts.changed", self.on_scripts_changed)
        events.subscribe("settings.changed", self.on_settings_changed)

    def on_auth_login(self, data: dict) -> None:
        """Başarılı girişi kaydeder. Parametre: data - {"username"}."""
        self.write(data.get("username", ""), "auth.login")

    def on_auth_login_failed(self, data: dict) -> None:
        """Başarısız girişi error durumuyla kaydeder. Parametre: data - {"username"}."""
        self.write(data.get("username", ""), "auth.login_failed", status="error")

    def on_auth_logout(self, data: dict) -> None:
        """Çıkışı kaydeder. Parametre: data - {"username"}."""
        self.write(data.get("username", ""), "auth.logout")

    def on_script_finished(self, data: dict) -> None:
        """Biten script çalışmasını kaydeder.

        Parametre: data - {"username", "script_id", "success", "duration_ms", "error_text"}.
        """
        if data.get("success", False):
            status = "ok"
        else:
            status = "error"
        self.write(
            data.get("username", ""),
            "script.run",
            target=str(data.get("script_id", "")),
            status=status,
            duration_ms=data.get("duration_ms", 0) or 0,
            details=data.get("error_text", "") or "",
        )

    def on_scripts_changed(self, data: dict) -> None:
        """Script listesindeki değişikliği kaydeder.

        Parametre: data - {"script_id", isteğe bağlı "change", "username"}.
        """
        self.write(
            data.get("username", ""),
            "scripts.changed",
            target=str(data.get("script_id", "")),
            details=data.get("change", "") or "",
        )

    def on_settings_changed(self, data: dict) -> None:
        """Ayar değişikliğini kaydeder.

        Parametre: data - {"username", isteğe bağlı "setting", "details"}.
        """
        self.write(
            data.get("username", ""),
            "settings.changed",
            target=str(data.get("setting", "")),
            details=data.get("details", "") or "",
        )
