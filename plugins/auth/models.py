"""models.py - auth eklentisinin veritabanı tabloları (kullanıcı, rol, kullanıcı-rol bağı).

Kim kullanır: service.py (okuma/yazma) ve plugin.py (import ederek tabloları Base'e kaydeder).
Nasıl bağlanır: üç sınıf da app.core.db.Base'den türer; main'deki create_all_tables()
bu modül import edilmiş olduğu için tabloları oluşturur.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    """Sisteme giriş yapabilen bir kullanıcı."""

    __tablename__ = "auth_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)
    language: Mapped[str] = mapped_column(String(10), default="tr")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class Role(Base):
    """İzin grubu. İzinler virgülle ayrılmış tek bir metin olarak saklanır."""

    __tablename__ = "auth_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    # Neden düz metin: ayrı bir izin tablosu bu proje için gereksiz karmaşıklık olurdu.
    permissions_text: Mapped[str] = mapped_column(default="")


class UserRole(Base):
    """Hangi kullanıcının hangi role sahip olduğunu tutan bağ tablosu."""

    __tablename__ = "auth_user_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    role_id: Mapped[int] = mapped_column(ForeignKey("auth_roles.id"))
