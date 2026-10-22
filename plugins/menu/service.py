"""service.py - "menu" servisi: bölüm ve grup yönetimi, hazır kayıtlar, menü öğeleri.

Kim kullanır: plugin.py (kaydeder), section_page.py ve settings_panel.py,
ayrıca diğer eklentiler kernel.get_service("menu") ile.
Nasıl bağlanır: veritabanına get_session() ile erişir. "auth" ve "i18n"
servislerini kernel.get_service ile (varsa) kullanır; bu eklentileri import etmez.
Bölüm ve grup her yerde düz sözlük olarak döner.
"""

import re

from sqlalchemy import select

from app.core.db import get_session
from app.core.plugin import NavItem
from plugins.menu.models import MenuGroup, Section

# Bölüm anahtarında yalnızca küçük harf, rakam ve alt çizgi olabilir.
KEY_PATTERN = re.compile(r"^[a-z0-9_]+$")

# Hazır bölümler: (key, name_tr, name_en, icon, order, is_system, path)
DEFAULT_SECTIONS = [
    ("dashboard", "Dashboard", "Dashboard", "dashboard", 10, False, ""),
    ("operation", "Operasyon", "Operation", "build", 20, False, ""),
    ("report", "Rapor", "Report", "assessment", 30, False, ""),
    ("log", "Log", "Log", "receipt_long", 40, True, "/log"),
    ("settings", "Ayarlar", "Settings", "settings", 50, True, "/settings"),
]

# Sistem bölümü anahtarı -> sayfasını sunan eklentinin id'si.
# Neden: bölümler veritabanında durur, eklenti kapalıyken de kaydı kalır. Sahibi eklenti
# yüklenmemişse bölümün sayfası yoktur (404), bu yüzden menüden gizlenir.
# Yeni bir sistem bölümü eklenirse buraya da eklenmelidir.
SYSTEM_SECTION_OWNERS = {"log": "audit_log", "settings": "settings_core"}


def section_to_dict(section: Section) -> dict:
    """Section kaydını sözlüğe çevirir. Parametre: section. Dönüş: sözlük."""
    # Neden: path boşsa bölümün gerçek adresi /section/<key>'dir.
    path = section.path or "/section/" + section.key
    return {
        "id": section.id,
        "key": section.key,
        "name_tr": section.name_tr,
        "name_en": section.name_en,
        "icon": section.icon,
        "order": section.order,
        "is_system": section.is_system,
        "is_visible": section.is_visible,
        "path": path,
    }


def group_to_dict(group: MenuGroup) -> dict:
    """MenuGroup kaydını sözlüğe çevirir. Parametre: group. Dönüş: sözlük."""
    return {
        "id": group.id,
        "section_key": group.section_key,
        "name_tr": group.name_tr,
        "name_en": group.name_en,
        "order": group.order,
    }


class MenuService:
    """Bölüm ve grupların tek sahibi."""

    def __init__(self, kernel) -> None:
        """Servisi kurar. Parametre: kernel - izin kaydı ve diğer servisler için."""
        self.kernel = kernel

    # ---------- Yardımcılar ----------

    def register_section_permission(self, key: str) -> None:
        """Bölümün görüntüleme iznini kernel'e kaydeder. Parametre: key."""
        self.kernel.register_permission("section." + key + ".view", "menu.permission.section_view")

    def register_all_section_permissions(self) -> None:
        """Veritabanındaki her bölümün izinlerini kaydeder (kernel kaydı bellekte tutulur)."""
        for section in self.list_sections():
            self.register_section_permission(section["key"])

    def pick_label(self, name_tr: str, name_en: str) -> str:
        """Etiketi aktif dile göre seçer; i18n servisi yoksa Türkçe adı döndürür."""
        i18n = self.kernel.get_service("i18n")
        if i18n is None:
            return name_tr
        return i18n.pick(name_tr, name_en)

    # ---------- Bölümler ----------

    def list_sections(self) -> list[dict]:
        """Bütün bölümleri sıra numarasına göre döndürür (gizliler dahil)."""
        with get_session() as session:
            query = select(Section).order_by(Section.order, Section.id)
            sections = []
            for section in session.scalars(query):
                sections.append(section_to_dict(section))
            return sections

    def create_section(self, key: str, name_tr: str, name_en: str, icon: str) -> None:
        """Yeni bölüm ekler ve görüntüleme iznini kaydeder.

        Parametreler: key - yalnızca [a-z0-9_]; adlar ve ikon.
        Geçersiz ya da var olan anahtarda ValueError fırlatır.
        """
        if not KEY_PATTERN.fullmatch(key):
            raise ValueError("Bölüm anahtarı yalnızca küçük harf, rakam ve _ içerebilir.")
        with get_session() as session:
            existing = session.scalar(select(Section).where(Section.key == key))
            if existing is not None:
                raise ValueError("Bu anahtarla bir bölüm zaten var: " + key)
            # Neden son sıra + 10: yeni bölüm menünün sonuna eklenir.
            highest = 0
            for section in session.scalars(select(Section)):
                if section.order > highest:
                    highest = section.order
            session.add(
                Section(
                    key=key,
                    name_tr=name_tr,
                    name_en=name_en or name_tr,
                    icon=icon or "folder",
                    order=highest + 10,
                )
            )
            session.commit()
        self.register_section_permission(key)

    def update_section(
        self, key: str, name_tr: str, name_en: str, icon: str, order: int, is_visible: bool
    ) -> None:
        """Bölümün adını, ikonunu, sırasını ve görünürlüğünü günceller. Yoksa ValueError."""
        with get_session() as session:
            section = session.scalar(select(Section).where(Section.key == key))
            if section is None:
                raise ValueError("Bölüm bulunamadı: " + key)
            section.name_tr = name_tr
            section.name_en = name_en or name_tr
            section.icon = icon or "folder"
            section.order = order
            section.is_visible = is_visible
            session.commit()

    def delete_section(self, key: str) -> None:
        """Bölümü ve gruplarını siler. Sistem bölümü ya da bulunmayan bölüm için ValueError."""
        with get_session() as session:
            section = session.scalar(select(Section).where(Section.key == key))
            if section is None:
                raise ValueError("Bölüm bulunamadı: " + key)
            if section.is_system:
                raise ValueError("Sistem bölümü silinemez: " + key)
            groups = session.scalars(select(MenuGroup).where(MenuGroup.section_key == key))
            for group in groups.all():
                session.delete(group)
            session.delete(section)
            session.commit()

    # ---------- Gruplar ----------

    def list_groups(self, section_key: str | None = None) -> list[dict]:
        """Grupları döndürür; section_key verilirse yalnızca o bölümün grupları."""
        with get_session() as session:
            query = select(MenuGroup).order_by(MenuGroup.order, MenuGroup.id)
            if section_key is not None:
                query = query.where(MenuGroup.section_key == section_key)
            groups = []
            for group in session.scalars(query):
                groups.append(group_to_dict(group))
            return groups

    def create_group(self, section_key: str, name_tr: str, name_en: str) -> int:
        """Bölümün altına grup ekler. Dönüş: yeni grubun id'si. Bölüm yoksa ValueError."""
        with get_session() as session:
            section = session.scalar(select(Section).where(Section.key == section_key))
            if section is None:
                raise ValueError("Bölüm bulunamadı: " + section_key)
            highest = 0
            query = select(MenuGroup).where(MenuGroup.section_key == section_key)
            for group in session.scalars(query):
                if group.order > highest:
                    highest = group.order
            group = MenuGroup(
                section_key=section_key,
                name_tr=name_tr,
                name_en=name_en or name_tr,
                order=highest + 10,
            )
            session.add(group)
            session.commit()
            return group.id

    def delete_group(self, group_id: int) -> None:
        """Grubu siler. Bulunamazsa ValueError."""
        with get_session() as session:
            group = session.get(MenuGroup, group_id)
            if group is None:
                raise ValueError("Grup bulunamadı: " + str(group_id))
            session.delete(group)
            session.commit()

    # ---------- Hazır kayıtlar ----------

    def seed_defaults(self) -> None:
        """Hazır beş bölümü yalnızca bölüm tablosu boşsa ekler (tekrar çağrılabilir).

        Neden: admin hazır bir bölümü sildiyse yeniden başlatmada geri gelmemeli.
        """
        with get_session() as session:
            if session.scalar(select(Section).limit(1)) is not None:
                return
            for key, name_tr, name_en, icon, order, is_system, path in DEFAULT_SECTIONS:
                existing = session.scalar(select(Section).where(Section.key == key))
                if existing is not None:
                    continue
                session.add(
                    Section(
                        key=key,
                        name_tr=name_tr,
                        name_en=name_en,
                        icon=icon,
                        order=order,
                        is_system=is_system,
                        path=path,
                    )
                )
            session.commit()

    # ---------- Menü öğeleri ----------

    def build_menu_nav_items(self, user: dict | None) -> list[NavItem]:
        """Yan menü için bölüm ve grup öğelerini üretir (nav provider).

        Parametre: user - giriş yapmış kullanıcı ya da None.
        Gizli bölümler, sahibi eklentisi yüklenmemiş sistem bölümleri ve kullanıcının izni olmayan bölümler (ve grupları) atlanır.
        "auth" servisi yoksa izin süzmesi yapılmaz; varsa ve kullanıcı yoksa liste boştur.
        """
        auth = self.kernel.get_service("auth")
        if auth is not None and user is None:
            return []

        items: list[NavItem] = []
        visible_keys: list[str] = []
        for section in self.list_sections():
            if not section["is_visible"]:
                continue
            # Neden: sahibi eklenti yüklü değilse sayfa da yoktur; bölümü gösterme.
            owner = SYSTEM_SECTION_OWNERS.get(section["key"])
            if owner is not None and self.kernel.plugin_status.get(owner) != "loaded":
                continue
            if auth is not None:
                if not auth.has_permission(user, "section." + section["key"] + ".view"):
                    continue
            visible_keys.append(section["key"])
            items.append(
                NavItem(
                    key="section:" + section["key"],
                    label=self.pick_label(section["name_tr"], section["name_en"]),
                    icon=section["icon"],
                    path=section["path"],
                    parent_key=None,
                    order=section["order"],
                )
            )

        for group in self.list_groups():
            # Neden: bölümü görünmeyen kullanıcıya grubu da gösterilmez.
            if group["section_key"] not in visible_keys:
                continue
            items.append(
                NavItem(
                    key="group:" + str(group["id"]),
                    label=self.pick_label(group["name_tr"], group["name_en"]),
                    icon="folder",
                    path="",
                    parent_key="section:" + group["section_key"],
                    order=group["order"],
                )
            )
        return items
