"""models.py - audit_log eklentisinin veritabanı tablosu (işlem kaydı).

Kim kullanır: service.py (okuma/yazma) ve plugin.py (import ederek tabloyu Base'e kaydeder).
Nasıl bağlanır: AuditEntry app.core.db.Base'den türer; main'deki create_all_tables()
bu modül import edilmiş olduğu için tabloyu oluşturur.
"""

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditEntry(Base):
    """Tek bir işlem kaydı (giriş, script çalıştırma, ayar değişikliği ...)."""

    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    username: Mapped[str] = mapped_column(String(200), default="")
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(300), default="")
    # "ok" ya da "error".
    status: Mapped[str] = mapped_column(String(20), default="ok")
    duration_ms: Mapped[int] = mapped_column(default=0)
    details: Mapped[str] = mapped_column(Text, default="")
