"""service.py - "auth" servisi: giriş, yetki, oturum, kullanıcı ve rol yönetimi.

Kim kullanır: plugin.py (kaydeder), çekirdek (access.py, layout.py) ve diğer
eklentiler kernel.get_service("auth") ile.
Nasıl bağlanır: veritabanına get_session() ile erişir, oturum bilgisini
NiceGUI'nin app.storage.user["user_id"] alanında tutar, giriş/çıkış olaylarını
kernel.events ile yayınlar. Kullanıcı bilgisi her yerde şu anahtarlı sözlüktür:
id, username, full_name, roles (list[str]), permissions (list[str]).
"""

import logging
import time

from nicegui import app
from sqlalchemy import select

from app.core.db import get_session
from plugins.auth.models import Role, User, UserRole
from plugins.auth.passwords import hash_password, verify_password

logger = logging.getLogger(__name__)

# Seed rolleri ve izinleri (rol adı -> izin listesi).
DEFAULT_ROLES = {
    "admin": ["*"],
    "operator": [
        "section.dashboard.view",
        "section.operation.view",
        "section.report.view",
        "section.log.view",
        "log.view",
    ],
    "viewer": ["section.dashboard.view", "section.report.view"],
}


def normalize_username(username: str) -> str:
    """Kullanıcı adını küçük harfe çevirip baş/son boşluğu atar."""
    return username.lower().strip()


def split_permissions(permissions_text: str) -> list[str]:
    """Virgülle ayrılmış izin metnini listeye çevirir (boş parçalar atılır)."""
    permissions = []
    for part in permissions_text.split(","):
        part = part.strip()
        if part:
            permissions.append(part)
    return permissions


# Varsayılan admin parolası; canlı ortamda bu parolayla açılmaya izin verilmez.
DEFAULT_ADMIN_PASSWORD = "admin"
# Hatalı giriş sayacının en çok tutacağı kullanıcı adı sayısı (bellek sınırı).
MAX_TRACKED_LOGINS = 1000


def check_password_rules(password: str, min_length: int = 8) -> None:
    """Parolanın uzunluk kurallarını denetler; kural bozuksa ValueError fırlatır.

    Parametreler: password - düz parola; min_length - en az karakter sayısı
    (config.toml [auth] min_password_length).
    Neden 72 bayt: bcrypt 72 bayttan fazlasını sessizce keser; bunu kullanıcıdan saklamayız.
    """
    if len(password) < min_length:
        raise ValueError("Parola en az " + str(min_length) + " karakter olmalı")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Parola en fazla 72 bayt olabilir")


class AuthService:
    """Kullanıcı, rol ve oturum işlerinin tek sahibi."""

    def __init__(self, kernel) -> None:
        """Servisi kurar. Parametre: kernel - olay yayını ve ayarlar için. Dönüş: yok."""
        self.kernel = kernel
        # Hatalı giriş sayacı: kullanıcı adı -> {"count", "last_failure", "locked_until"}.
        # Neden bellekte: kilit kısa sürelidir; yeniden başlatınca sıfırlanması sorun değildir.
        self.failed_logins: dict[str, dict] = {}
        # Neden değiştirilebilir saat: testler zamanı elle ilerletebilsin.
        self.clock = time.monotonic

    def check_password(self, password: str) -> None:
        """Parolayı config'teki en kısa uzunluk kuralıyla denetler; bozuksa ValueError."""
        check_password_rules(password, self.kernel.config.min_password_length)
    # ---------- Yardımcılar ----------

    def build_user_dict(self, session, user: User) -> dict:
        """Bir User kaydını rolleri ve birleşik izinleriyle sözlüğe çevirir.

        Parametreler: session - açık DB oturumu; user - User kaydı.
        Dönüş: id, username, full_name, roles, permissions anahtarlı sözlük.
        """
        query = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
            .order_by(Role.name)
        )
        role_names: list[str] = []
        permissions: list[str] = []
        for role in session.scalars(query):
            role_names.append(role.name)
            for permission in split_permissions(role.permissions_text):
                # Neden kontrol: birden çok rolde aynı izin varsa tek kez yazılsın.
                if permission not in permissions:
                    permissions.append(permission)
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "roles": role_names,
            "permissions": permissions,
        }

    def set_user_roles(self, session, user_id: int, role_names: list[str]) -> None:
        """Kullanıcının rollerini verilen listeyle değiştirir (commit etmez).

        Parametreler: session; user_id; role_names. Bilinmeyen rol adı ValueError verir.
        """
        roles = []
        seen_names = []
        for role_name in role_names:
            # Neden atlanır: aynı rol iki kez eklenirse tekrarlı bağ oluşur.
            if role_name in seen_names:
                continue
            seen_names.append(role_name)
            role = session.scalar(select(Role).where(Role.name == role_name))
            if role is None:
                raise ValueError(f"Rol bulunamadı: {role_name}")
            roles.append(role)

        old_links = session.scalars(select(UserRole).where(UserRole.user_id == user_id))
        for link in old_links.all():
            session.delete(link)
        for role in roles:
            session.add(UserRole(user_id=user_id, role_id=role.id))

    # ---------- Giriş ----------

    def authenticate(self, username: str, password: str) -> dict | None:
        """Kullanıcı adı ve parolayı doğrular.

        Parametreler: username (büyük/küçük harf fark etmez); password.
        Dönüş: kullanıcı sözlüğü; yanlış bilgi, pasif kullanıcı ya da kilitli hesapta None.
        Hatalı denemeler sayılır; [auth] max_login_attempts kez üst üste hata olursa
        kullanıcı adı lockout_minutes dakika kilitlenir. Başarılı giriş sayacı sıfırlar.
        """
        username = normalize_username(username)
        if self.is_locked_out(username):
            return None
        with get_session() as session:
            user = session.scalar(select(User).where(User.username == username))
            # Neden var olmayan ad da sayılır: aksi halde kilitlenme davranışı hangi
            # kullanıcı adlarının var olduğunu ele verirdi.
            if user is None or not user.is_active or not verify_password(password, user.password_hash):
                self.record_failed_login(username)
                return None
            self.failed_logins.pop(username, None)
            return self.build_user_dict(session, user)

    # ---------- Giriş kilidi ----------

    def is_locked_out(self, username: str) -> bool:
        """Kullanıcı adı çok fazla hatalı deneme yüzünden şu an kilitli mi?

        Parametre: username (büyük/küçük harf fark etmez). Dönüş: kilitliyse True.
        """
        record = self.failed_logins.get(normalize_username(username))
        if record is None:
            return False
        return record["locked_until"] > self.clock()

    def record_failed_login(self, username: str) -> None:
        """Hatalı bir denemeyi sayar; sınır aşılınca kullanıcı adını kilitler.

        Parametre: username - normalleştirilmiş ad. Dönüş: yok.
        """
        max_attempts = self.kernel.config.max_login_attempts
        if max_attempts <= 0:
            return
        now = self.clock()
        window_seconds = self.kernel.config.lockout_minutes * 60
        record = self.failed_logins.get(username)
        # Neden sıfırlanır: uzun süre önceki hatalar yeni bir kilide sayılmamalı.
        if record is None or now - record["last_failure"] > window_seconds:
            record = {"count": 0, "last_failure": now, "locked_until": 0.0}
        record["count"] += 1
        record["last_failure"] = now
        if record["count"] >= max_attempts:
            record["locked_until"] = now + window_seconds
            record["count"] = 0
            logger.warning("Çok fazla hatalı giriş, kullanıcı adı kilitlendi: %s", username)
        self.failed_logins[username] = record
        self.forget_old_failures(now, window_seconds)

    def forget_old_failures(self, now: float, window_seconds: float) -> None:
        """Sayaç çok büyüdüyse süresi geçmiş kayıtları atar (rastgele adlarla bellek dolmasın)."""
        if len(self.failed_logins) <= MAX_TRACKED_LOGINS:
            return
        for name in list(self.failed_logins):
            record = self.failed_logins[name]
            if record["locked_until"] <= now and now - record["last_failure"] > window_seconds:
                del self.failed_logins[name]

    def get_user_by_id(self, user_id: int) -> dict | None:
        """Kullanıcıyı id ile okur. Dönüş: sözlük; yoksa ya da pasifse None."""
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None or not user.is_active:
                return None
            return self.build_user_dict(session, user)

    # ---------- Yetki ----------

    def has_permission(self, user: dict | None, permission: str) -> bool:
        """Kullanıcının izni olup olmadığını söyler.

        Parametreler: user - kullanıcı sözlüğü ya da None; permission - izin anahtarı.
        Dönüş: "*" izni her şeyi kapsar; kullanıcı None ise False.
        """
        if user is None:
            return False
        if "*" in user["permissions"]:
            return True
        return permission in user["permissions"]

    # ---------- Oturum ----------

    def login_user(self, user: dict) -> None:
        """Kullanıcıyı bu tarayıcı oturumuna giriş yapmış olarak yazar.

        Parametre: user - kullanıcı sözlüğü. Dönüş: yok. İstek bağlamı gerektirir.
        """
        app.storage.user["user_id"] = user["id"]

    def logout_current_user(self) -> None:
        """Oturumdaki kullanıcıyı çıkarır ve auth.logout olayını yayınlar."""
        user = self.current_user()
        app.storage.user.pop("user_id", None)
        if user is not None:
            self.kernel.events.publish("auth.logout", {"username": user["username"]})

    def current_user(self) -> dict | None:
        """Oturumdaki kullanıcıyı her çağrıda DB'den okur.

        Dönüş: kullanıcı sözlüğü; giriş yoksa, kullanıcı silinmiş/pasifse ya da
        istek bağlamı dışındaysa None.
        """
        # Neden RuntimeError yakalanır: app.storage.user yalnızca bir web isteği
        # içinde vardır; arka plan kodundan çağrılınca hata yerine None dönmeli.
        try:
            user_id = app.storage.user.get("user_id")
        except RuntimeError:
            return None
        if user_id is None:
            return None
        return self.get_user_by_id(user_id)

    # ---------- Kullanıcı yönetimi ----------

    def list_users(self) -> list[dict]:
        """Tüm kullanıcıları (pasifler dahil) listeler.

        Dönüş: sözlük listesi; her sözlükte ayrıca is_active bulunur.
        """
        users = []
        with get_session() as session:
            for user in session.scalars(select(User).order_by(User.username)):
                user_dict = self.build_user_dict(session, user)
                user_dict["is_active"] = user.is_active
                users.append(user_dict)
        return users

    def create_user(
        self,
        username: str,
        full_name: str,
        password: str,
        role_names: list[str],
        enforce_password_rules: bool = True,
    ) -> dict:
        """Yeni kullanıcı oluşturur.

        Parametreler: username, full_name, password (düz), role_names;
        enforce_password_rules - False ise uzunluk kuralı atlanır (yalnızca ilk admin için).
        Dönüş: kullanıcı sözlüğü. Kullanıcı adı doluysa/boşsa ya da parola kuralı bozuksa ValueError.
        """
        username = normalize_username(username)
        if not username:
            raise ValueError("Kullanıcı adı boş olamaz")
        if enforce_password_rules:
            self.check_password(password)
        with get_session() as session:
            existing = session.scalar(select(User).where(User.username == username))
            if existing is not None:
                raise ValueError(f"Bu kullanıcı adı zaten var: {username}")
            user = User(
                username=username,
                full_name=full_name,
                password_hash=hash_password(password),
            )
            session.add(user)
            # Neden flush: rol bağlarını yazmadan önce user.id'nin oluşması gerekir.
            session.flush()
            self.set_user_roles(session, user.id, role_names)
            session.commit()
            return self.build_user_dict(session, user)

    def update_user(
        self, user_id: int, full_name: str, is_active: bool, role_names: list[str]
    ) -> None:
        """Kullanıcının adını, aktiflik durumunu ve rollerini günceller.

        Parametreler: user_id, full_name, is_active, role_names. Dönüş: yok.
        Kullanıcı yoksa ValueError.
        """
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError(f"Kullanıcı bulunamadı: {user_id}")
            user.full_name = full_name
            user.is_active = is_active
            self.set_user_roles(session, user_id, role_names)
            session.commit()

    def change_password(self, user_id: int, new_password: str) -> None:
        """Kullanıcının parolasını değiştirir. Kullanıcı yoksa ya da parola kuralı bozuksa ValueError."""
        self.check_password(new_password)
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError(f"Kullanıcı bulunamadı: {user_id}")
            user.password_hash = hash_password(new_password)
            session.commit()

    def change_own_password(self, user_id: int, current_password: str, new_password: str) -> None:
        """Kullanıcının kendi parolasını değiştirir; mevcut parolayı bilmesi gerekir.

        Parametreler: user_id; current_password - şu anki parola; new_password - yeni parola.
        Mevcut parola yanlışsa, kullanıcı yoksa ya da yeni parola kurala uymuyorsa ValueError.
        """
        with get_session() as session:
            user = session.get(User, user_id)
            if user is None or not verify_password(current_password, user.password_hash):
                raise ValueError("Mevcut parola hatalı")
        self.change_password(user_id, new_password)

    def has_default_admin_password(self) -> bool:
        """admin kullanıcısı hâlâ varsayılan "admin" parolasını mı kullanıyor?

        Kim kullanır: main.py, canlı ortamda bu durumda uygulamayı açmaz.
        """
        with get_session() as session:
            admin = session.scalar(select(User).where(User.username == "admin"))
            if admin is None:
                return False
            return verify_password(DEFAULT_ADMIN_PASSWORD, admin.password_hash)

    # ---------- Rol yönetimi ----------

    def list_roles(self) -> list[dict]:
        """Rolleri listeler. Dönüş: {"name": ..., "permissions": [...]} sözlükleri."""
        roles = []
        with get_session() as session:
            for role in session.scalars(select(Role).order_by(Role.name)):
                roles.append(
                    {
                        "name": role.name,
                        "permissions": split_permissions(role.permissions_text),
                    }
                )
        return roles

    def create_role(self, name: str) -> None:
        """Boş izinli yeni rol oluşturur. Ad doluysa ya da boşsa ValueError."""
        name = name.strip()
        if not name:
            raise ValueError("Rol adı boş olamaz")
        with get_session() as session:
            if session.scalar(select(Role).where(Role.name == name)) is not None:
                raise ValueError(f"Bu rol zaten var: {name}")
            session.add(Role(name=name, permissions_text=""))
            session.commit()

    def set_role_permissions(self, role_name: str, permissions: list[str]) -> None:
        """Rolün izin listesini değiştirir. Rol yoksa ValueError."""
        with get_session() as session:
            role = session.scalar(select(Role).where(Role.name == role_name))
            if role is None:
                raise ValueError(f"Rol bulunamadı: {role_name}")
            role.permissions_text = ",".join(permissions)
            session.commit()

    def delete_role(self, name: str) -> None:
        """Rolü siler. admin rolü ve en az bir kullanıcıya atanmış rol silinemez (ValueError)."""
        if name == "admin":
            raise ValueError("admin rolü silinemez")
        with get_session() as session:
            role = session.scalar(select(Role).where(Role.name == name))
            if role is None:
                raise ValueError(f"Rol bulunamadı: {name}")
            link = session.scalar(select(UserRole).where(UserRole.role_id == role.id))
            if link is not None:
                raise ValueError(f"Bu rol kullanıcılara atanmış, önce rolü kullanıcılardan kaldırın: {name}")
            session.delete(role)
            session.commit()

    # ---------- Seed ----------

    def seed_defaults(self, initial_admin_password: str) -> None:
        """Hazır rolleri ve admin kullanıcısını oluşturur.

        Parametre: initial_admin_password - admin'in ilk parolası. Dönüş: yok.
        Neden tekrar güvenli: zaten var olan rol ve admin kullanıcısına dokunulmaz.
        """
        with get_session() as session:
            for role_name, permissions in DEFAULT_ROLES.items():
                role = session.scalar(select(Role).where(Role.name == role_name))
                if role is None:
                    session.add(Role(name=role_name, permissions_text=",".join(permissions)))
            session.commit()

        with get_session() as session:
            admin = session.scalar(select(User).where(User.username == "admin"))
        if admin is None:
            # Neden kural atlanır: geliştirme ortamında varsayılan "admin" parolası kısa olsa da
            # ilk giriş yapılabilsin. Canlı ortamda main.py varsayılan parolayla açılmayı reddeder.
            self.create_user(
                "admin", "Yönetici", initial_admin_password, ["admin"], enforce_password_rules=False
            )
            logger.info("Varsayılan admin kullanıcısı oluşturuldu")
