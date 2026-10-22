"""models.py - menu eklentisinin veritabanı tabloları (bölüm ve grup).

Kim kullanır: service.py (okuma/yazma) ve plugin.py (import ederek tabloları Base'e kaydeder).
Nasıl bağlanır: iki sınıf da app.core.db.Base'den türer; main'deki create_all_tables()
bu modül import edilmiş olduğu için tabloları oluşturur.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Section(Base):
    """Yan menüdeki üst seviye bölüm (Dashboard, Operasyon, ...)."""

    __tablename__ = "menu_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    name_tr: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str] = mapped_column(String(100), default="folder")
    order: Mapped[int] = mapped_column(default=100)
    # Neden is_system: log ve settings bölümlerinin içeriği eklentilerden gelir, silinemez.
    is_system: Mapped[bool] = mapped_column(default=False)
    is_visible: Mapped[bool] = mapped_column(default=True)
    # Boşsa bölümün adresi /section/<key> olur.
    path: Mapped[str] = mapped_column(String(200), default="")


class MenuGroup(Base):
    """Bir bölümün altındaki katlanabilir grup."""

    __tablename__ = "menu_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_key: Mapped[str] = mapped_column(String(100))
    name_tr: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(default=100)
