"""service.py - "scripts" servisi: script dosyaları, yayın kayıtları, yetki ve çalıştırma.

Kim kullanır: plugin.py (servisi ve nav provider'ı kaydeder), script_page.py,
wizard.py ve scripts_panel.py; diğer eklentiler kernel.get_service("scripts") ile.
Nasıl bağlanır:
- Script dosyaları config.toml'daki [scripts] folder klasöründe durur.
- Dosyalar parser.py ile (import edilmeden) okunur, runner.py ile ayrı bir
  süreçte çalıştırılır.
- Menüdeki yer ve ayarlar ScriptEntry tablosunda, çalışma geçmişi ScriptRun
  tablosunda tutulur. Her metot kendi DB oturumunu açar; bu yüzden execute()
  bir worker thread'den (run.io_bound) güvenle çağrılabilir.
- "menu" (bölüm/grup kontrolü) ve "forms" (argüman doğrulama) servisleri
  kernel.get_service ile kullanılır; bu eklentiler import edilmez.
- Değişiklikler "scripts.changed", çalıştırmalar "script.finished" olayıyla duyurulur.
- Okunan dosyalar (değişme zamanı ve boyutuyla) önbellekte tutulur; canlı moddaki
  sonuçlar izleyiciler arasında paylaşılır (run_live).
"""

import copy
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.core.db import get_session
from app.core.plugin import NavItem
from plugins.script_engine.models import ScriptEntry, ScriptRun
from plugins.script_engine.parser import (
    ALLOWED_MODES,
    ScriptSpec,
    make_script_id,
    parse_script_file,
)
from plugins.script_engine.runner import RunResult, run_script

# Mod -> menü ikonu.
MODE_ICONS = {
    "form": "play_arrow",
    "live": "monitor_heart",
    "scheduled": "schedule",
}

MISSING_FILE_ERROR = "Dosya bulunamadı"


@dataclass
class LiveResult:
    """Canlı moddaki bir çalıştırmanın paylaşılan sonucu.

    result: RunResult; finished_at: sonucun üretildiği saat (ekranda "Son güncelleme").
    """

    result: RunResult
    finished_at: datetime


def split_roles(roles_text: str) -> list[str]:
    """Virgülle ayrılmış rol metnini listeye çevirir; boş parçalar atlanır.

    Parametre: roles_text - örn. "operator,admin". Dönüş: ["operator", "admin"].
    """
    roles = []
    for part in (roles_text or "").split(","):
        name = part.strip()
        if name != "":
            roles.append(name)
    return roles


def entry_to_dict(entry: ScriptEntry) -> dict:
    """ScriptEntry kaydını sözlüğe çevirir; allowed_roles liste olarak döner."""
    return {
        "id": entry.id,
        "script_id": entry.script_id,
        "file_name": entry.file_name,
        "title_tr": entry.title_tr,
        "title_en": entry.title_en,
        "section_key": entry.section_key,
        "group_id": entry.group_id,
        "mode": entry.mode,
        "allowed_roles": split_roles(entry.allowed_roles),
        "timeout": entry.timeout,
        "refresh": entry.refresh,
        "schedule": entry.schedule,
        "is_enabled": entry.is_enabled,
        "created_at": entry.created_at,
    }


def read_result_json(result_json: str):
    """Kayıttaki sonuç JSON metnini Python değerine çevirir; okunamazsa None."""
    if not result_json:
        return None
    try:
        return json.loads(result_json)
    except ValueError:
        return None


def run_to_dict(run: ScriptRun) -> dict:
    """ScriptRun kaydını sözlüğe çevirir; "result" anahtarında çözülmüş sonuç da bulunur."""
    return {
        "id": run.id,
        "script_id": run.script_id,
        "username": run.username,
        "started_at": run.started_at,
        "success": run.success,
        "duration_ms": run.duration_ms,
        "result_json": run.result_json,
        "result": read_result_json(run.result_json),
        "output_text": run.output_text,
        "error_text": run.error_text,
    }


class ScriptService:
    """Script dosyaları, yayın kayıtları ve çalıştırmanın tek sahibi."""

    def __init__(self, kernel) -> None:
        """Servisi kurar ve scripts klasörünü (yoksa) oluşturur.

        Parametre: kernel - config.scripts_folder, olaylar ve diğer servisler için.
        Göreli klasör yolu, uygulamanın çalıştığı klasöre göre çözülür.
        """
        self.kernel = kernel
        self.scripts_folder = os.path.abspath(kernel.config.scripts_folder)
        os.makedirs(self.scripts_folder, exist_ok=True)
        # Dosya yolu -> (değişme zamanı, boyut, ScriptSpec). Neden: Scriptler paneli ve
        # zamanlayıcı her seferinde bütün klasörü okur; değişmeyen dosyayı yeniden ayrıştırmayalım.
        self.parse_cache: dict[str, tuple] = {}
        # Canlı mod: script_id -> {"live": LiveResult, "at": saat}. Kilitler aynı script'in
        # iki izleyici için aynı anda iki kez çalışmasını engeller.
        self.live_cache: dict[str, dict] = {}
        self.live_locks: dict[str, threading.Lock] = {}
        self.live_locks_guard = threading.Lock()
        # Neden değiştirilebilir saat: testler zamanı elle ilerletebilsin.
        self.clock = time.monotonic

    def parse_file(self, path: str) -> ScriptSpec:
        """Dosyayı ayrıştırır; değişmemişse önbellekteki sonucun kopyasını döndürür.

        Parametre: path - .py dosyasının yolu. Dönüş: ScriptSpec (çağıran değiştirebilir,
        önbellek etkilenmez). Dosya okunamazsa önbellek atlanır.
        """
        try:
            stat = os.stat(path)
        except OSError:
            return parse_script_file(path)
        cached = self.parse_cache.get(path)
        if cached is not None and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
            return copy.deepcopy(cached[2])
        spec = parse_script_file(path)
        self.parse_cache[path] = (stat.st_mtime_ns, stat.st_size, spec)
        return copy.deepcopy(spec)

    # ---------- Dosyalar ----------

    def list_script_files(self) -> list[str]:
        """Klasördeki .py dosyalarının adlarını alfabetik döndürür."""
        names = []
        for name in sorted(os.listdir(self.scripts_folder)):
            path = os.path.join(self.scripts_folder, name)
            if name.lower().endswith(".py") and os.path.isfile(path):
                names.append(name)
        return names

    def find_script_file(self, script_id: str) -> str | None:
        """Kimliği verilen script'in dosya yolunu bulur; yoksa None.

        Önce kayıttaki dosya adına bakılır; kayıt yoksa ya da dosya taşınmışsa
        klasördeki adlardan kimliği aynı olan aranır (elle bırakılan dosyalar için).
        """
        entry = self.get_entry(script_id)
        if entry is not None:
            path = os.path.join(self.scripts_folder, entry["file_name"])
            if os.path.isfile(path):
                return path
        for name in self.list_script_files():
            if make_script_id(name) == script_id:
                return os.path.join(self.scripts_folder, name)
        return None

    def save_uploaded_file(self, file_name: str, content: bytes, overwrite: bool) -> str:
        """Yüklenen dosyayı scripts klasörüne kaydeder.

        Parametreler: file_name - tarayıcının bildirdiği ad; content - dosya içeriği;
        overwrite - aynı kimlikte dosya varsa üzerine yazılsın mı.
        Dönüş: kaydedilen dosyanın yolu. Ad "<script_id>.py" olarak normalleştirilir.
        Uzantı .py değilse ya da dosya varken overwrite=False ise ValueError.
        """
        # Neden basename: "../x.py" gibi adlarla klasör dışına yazılmasın.
        base_name = os.path.basename(file_name.replace("\\", "/"))
        if not base_name.lower().endswith(".py"):
            raise ValueError("Yalnızca .py dosyası yüklenebilir")
        script_id = make_script_id(base_name)

        # Neden kimliğe göre aranır: "Ping Testi.py" ile "ping_testi.py" aynı
        # script'tir; ikisi yan yana durursa menü kaydı hangisine ait belli olmaz.
        existing_path = self.find_script_file(script_id)
        if existing_path is not None and not overwrite:
            raise ValueError("Bu script zaten var: " + script_id)
        if existing_path is not None:
            target_path = existing_path
        else:
            target_path = os.path.join(self.scripts_folder, script_id + ".py")

        with open(target_path, "wb") as script_file:
            script_file.write(content)
        return target_path

    def parse(self, script_id: str) -> ScriptSpec:
        """Script dosyasını bulup taze olarak okur.

        Dönüş: ScriptSpec; dosya yoksa error alanı "Dosya bulunamadı" olur.
        """
        path = self.find_script_file(script_id)
        if path is None:
            spec = ScriptSpec(script_id=script_id, file_path="")
            spec.error = MISSING_FILE_ERROR
            return spec
        return self.parse_file(path)

    # ---------- Tarama ----------

    def is_orphan(self, entry: dict, sections: list[dict]) -> bool:
        """Kaydın bölümü ya da grubu artık yok mu?

        Parametreler: entry - kayıt sözlüğü; sections - menu.list_sections() sonucu.
        Dönüş: sahipsizse True. "menu" servisi yoksa hiçbir kayıt sahipsiz sayılmaz.
        """
        menu = self.kernel.get_service("menu")
        if menu is None:
            return False
        section_found = False
        for section in sections:
            if section["key"] == entry["section_key"]:
                section_found = True
        if not section_found:
            return True
        if entry["group_id"] is None:
            return False
        for group in menu.list_groups(entry["section_key"]):
            if group["id"] == entry["group_id"]:
                return False
        return True

    def scan_folder(self) -> list[dict]:
        """Klasördeki her script'i kaydı ve durumuyla listeler (script_id'ye göre sıralı).

        Dönüş: {"spec": ScriptSpec, "entry": dict | None, "is_orphan": bool} listesi.
        Dosyası silinmiş kayıtlar da "Dosya bulunamadı" hatasıyla listede yer alır;
        böylece admin onları panelden kaldırabilir.
        """
        sections = []
        menu = self.kernel.get_service("menu")
        if menu is not None:
            sections = menu.list_sections()

        entries_by_id = {}
        for entry in self.list_entries():
            entries_by_id[entry["script_id"]] = entry

        items_by_id = {}
        for name in self.list_script_files():
            spec = self.parse_file(os.path.join(self.scripts_folder, name))
            items_by_id[spec.script_id] = {"spec": spec, "entry": None, "is_orphan": False}

        for script_id, entry in entries_by_id.items():
            if script_id not in items_by_id:
                spec = ScriptSpec(
                    script_id=script_id,
                    file_path=os.path.join(self.scripts_folder, entry["file_name"]),
                    title_tr=entry["title_tr"],
                    title_en=entry["title_en"],
                    error=MISSING_FILE_ERROR,
                )
                items_by_id[script_id] = {"spec": spec, "entry": None, "is_orphan": False}
            items_by_id[script_id]["entry"] = entry
            items_by_id[script_id]["is_orphan"] = self.is_orphan(entry, sections)

        result = []
        for script_id in sorted(items_by_id):
            result.append(items_by_id[script_id])
        return result

    # ---------- Kayıtlar ----------

    def list_entries(self) -> list[dict]:
        """Bütün yayın kayıtlarını script_id sırasıyla döndürür."""
        with get_session() as session:
            query = select(ScriptEntry).order_by(ScriptEntry.script_id)
            entries = []
            for entry in session.scalars(query):
                entries.append(entry_to_dict(entry))
            return entries

    def get_entry(self, script_id: str) -> dict | None:
        """Kimliği verilen script'in kaydını döndürür; yoksa None."""
        with get_session() as session:
            entry = session.scalar(select(ScriptEntry).where(ScriptEntry.script_id == script_id))
            if entry is None:
                return None
            return entry_to_dict(entry)

    def check_placement(self, section_key: str, group_id) -> None:
        """Bölümün ve (varsa) grubun var olduğunu denetler; yoksa ValueError.

        "menu" servisi yoksa denetim yapılmaz.
        """
        menu = self.kernel.get_service("menu")
        if menu is None:
            return
        section_found = False
        for section in menu.list_sections():
            if section["key"] == section_key:
                section_found = True
        if not section_found:
            raise ValueError("Bölüm bulunamadı: " + str(section_key))
        if group_id is None:
            return
        for group in menu.list_groups(section_key):
            if group["id"] == group_id:
                return
        raise ValueError("Grup bu bölümde bulunamadı: " + str(group_id))

    def publish(
        self,
        script_id: str,
        title_tr: str,
        title_en: str,
        section_key: str,
        group_id,
        mode: str,
        allowed_roles: list[str],
        timeout: int,
        refresh: int,
        schedule: str,
        username: str = "",
    ) -> None:
        """Script'i menüde yayınlar: kayıt yoksa ekler, varsa günceller.

        Parametreler: script_id; başlıklar; section_key ve group_id (None olabilir)
        menüdeki yer; mode ("form", "live", "scheduled"); allowed_roles - boşsa herkes;
        timeout/refresh saniye; schedule cron metni; username - olay kaydı için.
        Dosya yoksa, parse hatası varsa, mod geçersizse ya da bölüm/grup yoksa ValueError.
        """
        path = self.find_script_file(script_id)
        if path is None:
            raise ValueError(MISSING_FILE_ERROR + ": " + script_id)
        spec = self.parse_file(path)
        if spec.error != "":
            raise ValueError(spec.error)
        if mode not in ALLOWED_MODES:
            raise ValueError("Geçersiz mod: " + str(mode))
        if int(timeout) < 1:
            raise ValueError("Zaman aşımı en az 1 saniye olmalı")
        if int(refresh) < 1:
            raise ValueError("Yenileme aralığı en az 1 saniye olmalı")
        self.check_placement(section_key, group_id)

        with get_session() as session:
            entry = session.scalar(select(ScriptEntry).where(ScriptEntry.script_id == script_id))
            if entry is None:
                entry = ScriptEntry(script_id=script_id, is_enabled=True)
                session.add(entry)
            entry.file_name = os.path.basename(path)
            entry.title_tr = title_tr or spec.title_tr
            entry.title_en = title_en or title_tr or spec.title_en
            entry.section_key = section_key
            entry.group_id = group_id
            entry.mode = mode
            entry.allowed_roles = ",".join(allowed_roles)
            entry.timeout = int(timeout)
            entry.refresh = int(refresh)
            entry.schedule = schedule or ""
            session.commit()
        self.publish_changed(script_id, "published", username)

    def set_enabled(self, script_id: str, enabled: bool, username: str = "") -> None:
        """Script'i etkinleştirir ya da devre dışı bırakır. Kayıt yoksa ValueError."""
        with get_session() as session:
            entry = session.scalar(select(ScriptEntry).where(ScriptEntry.script_id == script_id))
            if entry is None:
                raise ValueError("Script kaydı bulunamadı: " + script_id)
            entry.is_enabled = enabled
            session.commit()
        if enabled:
            self.publish_changed(script_id, "enabled", username)
        else:
            self.publish_changed(script_id, "disabled", username)

    def remove(self, script_id: str, username: str = "") -> None:
        """Script'in kaydını ve dosyasını siler; çalışma geçmişi (ScriptRun) kalır.

        Ne kayıt ne dosya varsa ValueError.
        """
        path = self.find_script_file(script_id)
        removed_something = False
        with get_session() as session:
            entry = session.scalar(select(ScriptEntry).where(ScriptEntry.script_id == script_id))
            if entry is not None:
                session.delete(entry)
                session.commit()
                removed_something = True
        if path is not None:
            os.remove(path)
            removed_something = True
        if not removed_something:
            raise ValueError("Script bulunamadı: " + script_id)
        self.publish_changed(script_id, "removed", username)

    def publish_changed(self, script_id: str, change: str, username: str) -> None:
        """"scripts.changed" olayını yayınlar (audit_log bunu kaydeder)."""
        self.kernel.events.publish(
            "scripts.changed",
            {"script_id": script_id, "change": change, "username": username},
        )

    # ---------- Yetki ----------

    def can_user_run(self, user: dict | None, entry: dict) -> bool:
        """Kullanıcı bu script'i çalıştırabilir mi?

        Kurallar: admin rolü (ya da "*" izni) her zaman; allowed_roles boşsa
        giriş yapmış herkes; aksi halde kullanıcının rolleriyle kesişim olmalı.
        user None ise False.
        """
        if user is None:
            return False
        user_roles = user.get("roles", [])
        if "admin" in user_roles:
            return True
        # Neden "*": admin rolüyle aynı yetkiye sahip özel roller de çalıştırabilsin.
        if "*" in user.get("permissions", []):
            return True
        allowed_roles = entry.get("allowed_roles", [])
        if len(allowed_roles) == 0:
            return True
        for role in user_roles:
            if role in allowed_roles:
                return True
        return False

    def current_username(self) -> str:
        """Giriş yapmış kullanıcının adını döndürür; "auth" servisi ya da kullanıcı yoksa boş metin.

        İstek bağlamında (sayfa/handler) çağrılmalıdır; sayfalar ve sihirbaz bunu kullanır.
        """
        auth = self.kernel.get_service("auth")
        if auth is None:
            return ""
        user = auth.current_user()
        if user is None:
            return ""
        return user["username"]

    def current_user_can_manage(self) -> bool:
        """Giriş yapmış kullanıcının "scripts.manage" izni var mı?

        "auth" servisi yoksa True (yetki sistemi yok). İstek bağlamında çağrılmalıdır;
        panel ve sihirbaz handler'ları, panel açıkken izin geri alınmış olabileceği için
        işlemden önce bunu tekrar kontrol eder.
        """
        auth = self.kernel.get_service("auth")
        if auth is None:
            return True
        return auth.has_permission(auth.current_user(), "scripts.manage")

    # ---------- Menü ----------

    def build_nav_items(self, user: dict | None) -> list[NavItem]:
        """Etkin ve kullanıcının çalıştırabildiği script'ler için menü öğeleri üretir.

        Parametre: user - giriş yapmış kullanıcı ya da None. "auth" servisi yoksa
        yetki süzmesi yapılmaz; varsa ve kullanıcı yoksa liste boştur.
        Bölümü/grubu silinmiş kayıtların ebeveyni olmadığı için menü ağacı onları atar.
        """
        auth = self.kernel.get_service("auth")
        if auth is not None and user is None:
            return []
        items = []
        for entry in self.list_entries():
            if not entry["is_enabled"]:
                continue
            if auth is not None and not self.can_user_run(user, entry):
                continue
            if entry["group_id"] is not None:
                parent_key = "group:" + str(entry["group_id"])
            else:
                parent_key = "section:" + entry["section_key"]
            items.append(
                NavItem(
                    key="script:" + entry["script_id"],
                    label=self.pick_title(entry),
                    icon=MODE_ICONS.get(entry["mode"], "play_arrow"),
                    path="/script/" + entry["script_id"],
                    parent_key=parent_key,
                    order=100,
                )
            )
        return items

    def pick_title(self, entry: dict) -> str:
        """Kaydın başlığını aktif dile göre seçer; i18n yoksa Türkçe başlık."""
        i18n = self.kernel.get_service("i18n")
        if i18n is None:
            return entry["title_tr"] or entry["script_id"]
        return i18n.pick(entry["title_tr"], entry["title_en"]) or entry["script_id"]

    # ---------- Çalıştırma ----------

    def execute(
        self, script_id: str, arguments: dict, username: str, record_success: bool = True
    ) -> RunResult:
        """Script'i çalıştırır, sonucu ScriptRun olarak yazar ve "script.finished" yayınlar.

        Parametreler: script_id; arguments - formdan gelen değerler; username - çalıştıran;
        record_success - False ise BAŞARILI çalışma geçmişe yazılmaz ve olay yayınlanmaz
        (canlı moddaki periyodik yenilemeler Log'u doldurmasın diye); başarısız
        çalışma her durumda kaydedilir.
        Dönüş: RunResult (hata fırlatmaz). Dosya her çağrıda taze okunur, böylece
        diskteki değişiklikler hemen etkili olur. Argümanlar "forms" servisiyle
        doğrulanır; hata varsa script hiç çalıştırılmaz ama başarısız kayıt yazılır.
        Bu metot UI çağırmaz; worker thread'den güvenle çağrılabilir.
        """
        started_at = datetime.now()
        result = self.prepare_and_run(script_id, arguments)
        if result.success and not record_success:
            return result
        self.record_run(script_id, username, started_at, result)
        self.kernel.events.publish(
            "script.finished",
            {
                "username": username,
                "script_id": script_id,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error_text": result.error_text,
            },
        )
        return result

    def prepare_and_run(self, script_id: str, arguments: dict) -> RunResult:
        """Kaydı ve dosyayı denetler, argümanları doğrular ve script'i çalıştırır.

        Dönüş: RunResult; çalıştırma öncesi bir sorun varsa başarısız RunResult.
        """
        entry = self.get_entry(script_id)
        if entry is None:
            return RunResult(False, None, "", "Script yayınlanmamış: " + script_id, 0)
        if not entry["is_enabled"]:
            return RunResult(False, None, "", "Script devre dışı: " + script_id, 0)
        spec = self.parse(script_id)
        if spec.error != "":
            return RunResult(False, None, "", spec.error, 0)

        values = arguments
        forms = self.kernel.get_service("forms")
        if forms is not None:
            values, errors = forms.convert_and_validate(spec.fields, arguments)
            if len(errors) > 0:
                self.discard_uploaded_files(spec, arguments)
                return RunResult(False, None, "", "\n".join(errors), 0)
        config = self.kernel.config
        try:
            return run_script(
                spec.file_path,
                values,
                entry["timeout"],
                python_executable=config.scripts_python,
                env_passthrough=config.scripts_env_passthrough,
            )
        finally:
            self.discard_uploaded_files(spec, values)

    def discard_uploaded_files(self, spec: ScriptSpec, values: dict) -> None:
        """Dosya alanlarına yüklenen dosyaları çalıştırmadan sonra sildirir.

        Parametreler: spec - alan tarifleri; values - alan adı -> değer (dosya yolu).
        Neden: yüklenen dosyalar yalnızca o çalıştırma içindir; data/uploads büyümesin.
        Silme işi dosyaları kaydeden "forms" servisine aittir; yalnızca kendi klasöründekileri siler.
        """
        forms = self.kernel.get_service("forms")
        if forms is None or not hasattr(forms, "discard_uploaded_file"):
            return
        for field in spec.fields:
            if field.field_type != "file":
                continue
            path = values.get(field.name)
            if path:
                forms.discard_uploaded_file(path)

    def default_arguments(self, spec: ScriptSpec) -> dict:
        """Canlı mod ve zamanlayıcı için alanların varsayılan değerlerinden argüman üretir."""
        values = {}
        for field in spec.fields:
            values[field.name] = field.default
        return values

    def get_live_lock(self, script_id: str) -> threading.Lock:
        """Script'e özel kilidi döndürür (yoksa oluşturur)."""
        with self.live_locks_guard:
            if script_id not in self.live_locks:
                self.live_locks[script_id] = threading.Lock()
            return self.live_locks[script_id]

    def run_live(self, script_id: str, username: str) -> LiveResult:
        """Canlı mod sonucunu döndürür; taze sonuç varsa script yeniden çalıştırılmaz.

        Parametreler: script_id; username - çalıştıran (sonuç yeniden üretilirse kaydedilir).
        Dönüş: LiveResult. Kurallar:
        - Sonuç, kaydın yenileme aralığından (refresh) daha yeniyse aynısı döner. Böylece
          panoyu 20 kişi açsa da script aralık başına bir kez çalışır.
        - Aynı script aynı anda tek kez çalışır; bekleyen izleyiciler çıkan sonucu paylaşır.
        - Başarılı sonuç yalnızca pano bir süredir izlenmiyorsa (önceki sonuç iki aralıktan
          eskiyse) geçmişe ve Log'a yazılır; başarısız sonuç her zaman yazılır.
        Worker thread'den çağrılmalıdır (run.io_bound); UI çağırmaz.
        """
        entry = self.get_entry(script_id)
        refresh_seconds = 30
        if entry is not None:
            refresh_seconds = entry["refresh"]
        # Neden 1 saniye pay: izleyicilerin zamanlayıcıları aynı anda tetiklenmez; sonuç
        # tam aralık kadar bekletilirse geç kalan izleyici eski veriyi bir aralık daha görürdü.
        max_age = max(refresh_seconds - 1, 1)
        with self.get_live_lock(script_id):
            now = self.clock()
            cached = self.live_cache.get(script_id)
            if cached is not None and now - cached["at"] < max_age:
                return cached["live"]
            record_success = cached is None or now - cached["at"] > refresh_seconds * 2
            spec = self.parse(script_id)
            result = self.execute(
                script_id, self.default_arguments(spec), username, record_success=record_success
            )
            live = LiveResult(result=result, finished_at=datetime.now())
            self.live_cache[script_id] = {"live": live, "at": self.clock()}
            return live

    # ---------- Yetki uyarıları ----------

    def find_roles_without_section_access(self, section_key: str, role_names: list[str]) -> list[str]:
        """Script'i çalıştırabilecek ama bölümü göremeyen (menüde bulamayacak) rolleri bulur.

        Parametreler: section_key - script'in bölümü; role_names - script'in rol listesi
        (boşsa bütün roller çalıştırabilir sayılır). Dönüş: rol adları (alfabetik).
        "auth" servisi yoksa boş liste. "*" izinli roller her bölümü görür.
        """
        auth = self.kernel.get_service("auth")
        if auth is None:
            return []
        permission = "section." + section_key + ".view"
        missing = []
        for role in auth.list_roles():
            if len(role_names) > 0 and role["name"] not in role_names:
                continue
            if "*" in role["permissions"] or permission in role["permissions"]:
                continue
            missing.append(role["name"])
        return sorted(missing)

    def record_run(self, script_id: str, username: str, started_at: datetime, result: RunResult) -> None:
        """Çalıştırma sonucunu ScriptRun tablosuna yazar (kendi DB oturumuyla)."""
        # Neden default=str: tarih gibi JSON'a uymayan değerler de kaydedilebilsin.
        result_json = json.dumps(result.result, default=str, ensure_ascii=False)
        with get_session() as session:
            session.add(
                ScriptRun(
                    script_id=script_id,
                    username=username,
                    started_at=started_at,
                    success=result.success,
                    duration_ms=result.duration_ms,
                    result_json=result_json,
                    output_text=result.output_text,
                    error_text=result.error_text,
                )
            )
            session.commit()

    def list_runs(self, script_id: str, limit: int = 50) -> list[dict]:
        """Script'in çalışma geçmişini en yeni önce döndürür (en fazla limit kayıt)."""
        with get_session() as session:
            query = (
                select(ScriptRun)
                .where(ScriptRun.script_id == script_id)
                .order_by(ScriptRun.id.desc())
                .limit(limit)
            )
            runs = []
            for run in session.scalars(query):
                runs.append(run_to_dict(run))
            return runs

    def purge_runs_older_than(self, days: int) -> int:
        """Verilen günden eski çalışma kayıtlarını siler.

        Parametre: days - saklama süresi (gün); 0 ya da negatifse hiçbir şey silinmez.
        Dönüş: silinen kayıt sayısı. Kim çağırır: plugin.py (açılışta ve günde bir).
        """
        if days <= 0:
            return 0
        limit_time = datetime.now() - timedelta(days=days)
        with get_session() as session:
            result = session.execute(delete(ScriptRun).where(ScriptRun.started_at < limit_time))
            session.commit()
            return result.rowcount or 0

    def last_run(self, script_id: str) -> dict | None:
        """Script'in son çalıştırmasını döndürür; hiç çalışmadıysa None."""
        runs = self.list_runs(script_id, 1)
        if len(runs) == 0:
            return None
        return runs[0]
