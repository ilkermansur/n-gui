"""models.py - script_engine eklentisinin veritabanı tabloları (script kaydı ve çalışma geçmişi).

Kim kullanır: service.py (okuma/yazma) ve plugin.py (import ederek tabloları Base'e kaydeder).
Nasıl bağlanır: iki sınıf da app.core.db.Base'den türer; main'deki create_all_tables()
bu modül import edilmiş olduğu için tabloları oluşturur.
ScriptEntry, bir script'in menüdeki yerini ve ayarlarını tutar (sihirbaz yazar).
ScriptRun, her çalıştırmanın sonucunu tutar; script kaldırılsa da silinmez.
"""

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ScriptEntry(Base):
    """Yayınlanmış bir script'in menüdeki yeri ve çalışma ayarları."""

    __tablename__ = "script_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Dosya adından üretilen kimlik (make_script_id); adres /script/<script_id> olur.
    script_id: Mapped[str] = mapped_column(String(200), unique=True)
    file_name: Mapped[str] = mapped_column(String(300))
    title_tr: Mapped[str] = mapped_column(String(300), default="")
    title_en: Mapped[str] = mapped_column(String(300), default="")
    section_key: Mapped[str] = mapped_column(String(100))
    # Boşsa script doğrudan bölümün altında görünür.
    group_id: Mapped[int | None] = mapped_column(nullable=True, default=None)
    # "form", "live" ya da "scheduled".
    mode: Mapped[str] = mapped_column(String(20), default="form")
    # Virgülle ayrılmış rol adları; boşsa herkes çalıştırabilir.
    allowed_roles: Mapped[str] = mapped_column(String(500), default="")
    timeout: Mapped[int] = mapped_column(default=60)
    refresh: Mapped[int] = mapped_column(default=30)
    schedule: Mapped[str] = mapped_column(String(100), default="")
    is_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class ScriptRun(Base):
    """Bir script'in tek bir çalıştırılmasının kaydı."""

    __tablename__ = "script_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    script_id: Mapped[str] = mapped_column(String(200))
    username: Mapped[str] = mapped_column(String(200), default="")
    started_at: Mapped[datetime] = mapped_column(default=datetime.now)
    success: Mapped[bool] = mapped_column(default=False)
    duration_ms: Mapped[int] = mapped_column(default=0)
    # run() sonucunun JSON metni; hata varsa "null".
    result_json: Mapped[str] = mapped_column(Text, default="")
    output_text: Mapped[str] = mapped_column(Text, default="")
    error_text: Mapped[str] = mapped_column(Text, default="")
