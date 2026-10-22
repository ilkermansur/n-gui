# Modüler NiceGUI Kabuk — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Amaç:** Admin bir `.py` script'i yüklediğinde formu kendiliğinden oluşan ve script'i seçilen menü konumunda yayınlayan bir NiceGUI web kabuğu kurmak. Kabukta RBAC, TR/EN dil desteği, log ve ayar ekranları bulunur.

**Mimari:** Projenin merkezinde küçük bir çekirdek (`app/core`) var. Çekirdek bir kayıt defteri (Kernel), bir event bus, DB oturumu, tema ve kabuk çerçevesi sağlar. Her yetenek `plugins/<ad>/` altında bağımsız bir eklentidir. Eklentiler birbirini import etmez; birbirleriyle `kernel.get_service()` ve event'ler üzerinden konuşur. Menü veritabanından üretilir. Script'ler ayrı bir process'te çalışır.

**Teknoloji:** Python 3.12, nicegui 3.18, SQLAlchemy 2.1, PyYAML, bcrypt, APScheduler 3.11, tomli-w, pytest.

**Spec:** `docs/superpowers/specs/2026-10-22-modular-shell-design.md`

## Genel Kısıtlar
- **Kod stili** (spec'teki "Kod yazım kuralları" bölümü, her task için geçerli):
  - lambda, closure, kendi decorator'ımız, metaclass, `functools.partial`, karmaşık comprehension ve ileri seviye typing kullanılmaz.
  - Buton handler'ları adı olan fonksiyonlardır.
  - Her dosyanın başında Türkçe bir açıklama bloğu, her fonksiyonda Türkçe bir docstring bulunur; bariz olmayan adımlara "neden" yorumu eklenir.
  - Uzun ama düz kod, kısa ama zekice koda tercih edilir.
- **Veri tutucular:** pydantic yerine `dataclasses.dataclass` kullanılır (spec'teki "pydantic ScriptSpec" yerine; daha sade).
- **Eklenti sınırı:** eklentiler `plugins.X` paketlerini import etmez; yalnızca `app.core.*` modüllerini import eder.
- **Paylaşılan veri tipleri** (FieldSpec, NavItem) `app/core` içinde durur.
- **Yetki kontrolü** her sayfanın ilk satırında açıkça yapılır: `if not check_page_access(kernel, "<perm>"): return`.
- **Renk ve font:** ana renk `#3C50E0`, zemin `#F1F5F9`, font Inter. Hepsi `app/core/theme.py` içindedir.
- **Varsayılan dil:** `tr`. Bir anahtarın çevirisi bulunamazsa önce `en`, o da yoksa anahtarın kendisi döner.
- **Hazır kayıtlar (seed):**
  - Roller: `admin`, `operator`, `viewer`. `admin` rolü `*` iznine sahiptir.
  - Bölümler: `dashboard`, `operation`, `report`, `log`, `settings`. `log` ve `settings` sistem bölümüdür.
- **Script görünüm modları:** `form`, `live`, `scheduled`.
- **Script alan tipleri:** `str`, `text`, `int`, `float`, `bool`, `choice`, `multichoice`, `date`, `datetime`, `file`, `password`.
- **Testler:** `pytest`, `pyproject.toml` içinde `pythonpath = ["."]`. Test DB'si `sqlite:///:memory:`.
- **Commit mesajları** şu satırla biter: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## İnceleme Odağı
1. **JSON'a çevrilemeyen sonuç:** Script `datetime`, `set` ya da kendi nesnesini döndürür, veya çok fazla `print` yapar. Beklenen: sonuç `str`'ye çevrilerek gösterilir, çıktı kırpılır, uygulama hata vermez. (Task 11 testi)
2. **Takılan script:** Beklenen: `timeout` süresi dolunca process öldürülür, kullanıcı "zaman aşımı" mesajı görür, log'a `error` olarak düşer. (Task 11 testi)
3. **Bozuk script yükleme:** Syntax hatası, `run()` fonksiyonu yok, bozuk YAML ya da `.py` olmayan dosya. Beklenen: uygulama çökmez, script listede hata mesajıyla görünür ve yayınlanamaz. (Task 10 testleri)
4. **İçinde script olan bölüm veya grup silinir.** Beklenen: menü çizimi çökmez, sahipsiz öğeler menüde görünmez, Settings → Scriptler'de "atanmamış" olarak listelenir. (Task 3 `build_navigation_tree` testi)
5. **Oturum açıkken pasif yapılan kullanıcı.** Beklenen: bir sonraki sayfa açılışında login'e yönlendirilir. (Task 5 testi: `get_user_by_id` pasif kullanıcı için `None` döner.)

---

### Task 1: Proje iskeleti, config ve event bus

**Dosyalar:**
- Oluştur: `pyproject.toml`, `config.toml`, `README.md`, `app/__init__.py`, `app/core/__init__.py`, `plugins/__init__.py`, `app/core/config.py`, `app/core/events.py`
- Test: `tests/test_config.py`, `tests/test_events.py`

**Arayüzler:**
- Üretir:
  - `AppConfig` dataclass: `app_title: str = "N-GUI"`, `database_url: str = "sqlite:///data/app.db"`, `storage_secret: str = "degistir-beni"`, `scripts_folder: str = "scripts"`, `disabled_plugins: list[str]` (boş liste), `default_language: str = "tr"`, `port: int = 8080`, `initial_admin_password: str = "admin"`
  - `load_config(path: str) -> AppConfig`
  - `save_config_value(path: str, section: str, key: str, value) -> None`
  - `EventBus.subscribe(event_name: str, handler) -> None`
  - `EventBus.publish(event_name: str, data: dict) -> None`

- [ ] **Adım 1:** Testleri yaz:
  - `test_missing_file_returns_defaults`: olmayan bir yol verilince `load_config` sonucu `AppConfig()` ile eşittir.
  - `test_reads_values`: `[app] title="X"`, `[database] url="sqlite:///x.db"`, `[plugins] disabled=["scheduler"]` içeren geçici bir dosyadan okunan değerler doğrudur.
  - `test_save_config_value_roundtrip`: `save_config_value` ile yazılan `database.url` değeri tekrar okununca aynıdır.
  - `test_publish_calls_handlers_in_order`: handler'lar abone olma sırasıyla çağrılır.
  - `test_failing_handler_does_not_stop_others`: ilk handler `raise` etse bile ikinci handler çağrılır ve `publish` hata fırlatmaz.
- [ ] **Adım 2:** `pytest tests/test_config.py tests/test_events.py -v` → import hatasıyla FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - `pyproject.toml`: proje adı `n-gui`; bağımlılıklar `nicegui>=3.18`, `sqlalchemy>=2.1`, `pyyaml`, `bcrypt`, `apscheduler>=3.11,<4`, `tomli-w`, `pytest`; `[tool.pytest.ini_options] pythonpath=["."]`, `testpaths=["tests"]`.
  - `config.toml` dosyasında `[app] [database] [plugins] [scripts] [auth]` bölümleri bulunur; her satırın üstünde Türkçe açıklama yer alır.
  - `config.py`: `tomllib` ile okur; okuma tek tek `dict.get` çağrılarıyla, düz bir şekilde yapılır. `save_config_value` dosyayı okur, ilgili değeri değiştirir ve `tomli_w` ile geri yazar.
  - `events.py`: handler'lar `dict[str, list]` içinde tutulur. `publish` her handler'ı ayrı bir try/except içinde çağırır; hata olursa `logging` ile yazar.
- [ ] **Adım 4:** `python -m venv .venv && .venv/bin/pip install -e .` çalıştır, ardından testler → PASS.
- [ ] **Adım 5:** `README.md` içine kurulum ve çalıştırma adımlarını yaz, sonra commit: `feat(core): config ve event bus`.

### Task 2: Kernel, eklenti sözleşmesi, loader ve `t()`

**Dosyalar:**
- Oluştur: `app/core/plugin.py`, `app/core/kernel.py`, `app/core/loader.py`, `app/core/text.py`, `app/core/field_spec.py`
- Test: `tests/test_loader.py`, `tests/fixture_plugins/__init__.py`, `tests/fixture_plugins/{alpha,needs_alpha,broken_setup,needs_missing}/plugin.py`

**Arayüzler:**
- Tüketir: `AppConfig`, `EventBus` (Task 1)
- Üretir:
  - `class Plugin`: sınıf alanları `plugin_id: str`, `name: str`, `version: str = "1.0"`, `requires: list[str]`; metot `setup(self, kernel) -> None`
  - `@dataclass NavItem`: `key: str`, `label: str` (zaten çevrilmiş metin), `icon: str`, `path: str`, `parent_key: str | None = None`, `order: int = 100`
  - `@dataclass SettingsPanel`: `key: str`, `label_key: str`, `icon: str`, `permission: str`, `build_function` (çağrılabilir; parametre almaz, UI çizer)
  - `class Kernel(config: AppConfig)`:
    - Alanlar: `config`, `events: EventBus`, `plugin_status: dict[str, str]`, `loaded_plugin_folders: list[str]`
    - Servisler: `register_service(name: str, service) -> None`, `get_service(name: str)` (yoksa `None` döner)
    - İzinler: `register_permission(key: str, description: str) -> None`, `list_permissions() -> dict[str, str]`
    - Menü: `add_nav_provider(function) -> None` (function `(user: dict | None) -> list[NavItem]` şeklindedir), `collect_nav_items(user) -> list[NavItem]` (her provider'ı try/except ile çağırır)
    - Ayarlar: `register_settings_panel(panel: SettingsPanel) -> None`, `list_settings_panels() -> list[SettingsPanel]`
  - `set_kernel(kernel) -> None`, `get_kernel() -> Kernel` (modül seviyesinde tek örnek)
  - `discover_plugins(folder: str) -> list[str]`: içinde `plugin.py` olan alt klasör adları, alfabetik sırada
  - `load_plugins(kernel, folder: str, package: str, only: list[str] | None = None) -> None`
  - `t(key: str, **values) -> str`: `"i18n"` servisi yoksa `key` döner
  - `@dataclass FieldSpec`: `name`, `field_type="str"`, `label_tr=""`, `label_en=""`, `required=False`, `default=None`, `options: list` (boş liste), `min_value=None`, `max_value=None`, `help_text=""`

- [ ] **Adım 1:** Fixture eklentilerini oluştur:
  - `alpha`: servis kaydeder.
  - `needs_alpha`: `requires=["alpha"]`.
  - `broken_setup`: `setup` içinde `raise`.
  - `needs_missing`: `requires=["yok"]`.

  Ardından testleri yaz:
  - `test_discovers_folders`
  - `test_loads_in_dependency_order`: `needs_alpha` alfabetik olarak sonra gelmese bile `alpha`'dan sonra yüklenir.
  - `test_broken_plugin_marked_failed_and_others_load`: `plugin_status["broken_setup"]` değeri `"failed:"` ile başlar, `alpha` ise `"loaded"` olur.
  - `test_missing_dependency_not_loaded`: durum `"missing dependency: yok"` olur.
  - `test_disabled_plugin_skipped`: `config.disabled_plugins=["alpha"]` iken `alpha` → `"disabled"`, `needs_alpha` → `"missing dependency: alpha"`.
  - `test_only_parameter`: `only=["alpha"]` iken diğerleri `"not selected"` olur.
  - `test_nav_provider_error_is_isolated`: hata fırlatan provider olsa bile diğer provider'ın öğeleri döner.
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - Loader iki aşamalıdır:
    1. Her eklenti modülünü `importlib.import_module(f"{package}.{id}.plugin")` ile alıp `Plugin()` örneği oluşturur; hata olursa durumu `failed: <mesaj>` yapar.
    2. Bağımlılık sırasını basit bir `while` döngüsüyle çözer: her turda, gereksinimleri yüklenmiş olan eklentiyi `setup` eder. İlerleme kalmayınca kalan eklentileri `missing dependency: <id>` olarak işaretler.
  - `setup` çağrısı try/except içindedir. Başarılı olan eklentinin klasör yolu `loaded_plugin_folders` listesine eklenir.
- [ ] **Adım 4:** Testler → PASS.
- [ ] **Adım 5:** Commit: `feat(core): kernel, eklenti sözleşmesi ve loader`.

### Task 3: DB, tema, widget'lar, kabuk çerçevesi ve `main.py`

**Dosyalar:**
- Oluştur: `app/core/db.py`, `app/core/theme.py`, `app/core/widgets.py`, `app/core/navigation.py`, `app/core/layout.py`, `app/core/access.py`, `app/main.py`
- Test: `tests/test_navigation.py`, `tests/test_db.py`

**Arayüzler:**
- Tüketir: Task 2'deki `Kernel`, `NavItem`, `get_kernel`, `t`, `load_plugins`
- Üretir:
  - Veritabanı:
    - `class Base(DeclarativeBase)`: bütün modeller bu sınıftan türer.
    - `init_database(database_url: str) -> None`: `:memory:` için `StaticPool` kullanır, SQLite dosyasının klasörünü oluşturur.
    - `get_session() -> Session`: `with get_session() as session:` şeklinde kullanılır.
    - `create_all_tables() -> None`
  - Menü ağacı:
    - `@dataclass NavNode`: `item: NavItem`, `children: list[NavNode]`
    - `build_navigation_tree(items: list[NavItem]) -> list[NavNode]`: `order` değerine, sonra `label`'a göre sıralar. Ebeveyni olmayan (sahipsiz) öğeleri atar. Döngüye karşı korumalıdır.
  - Görünüm:
    - `apply_theme() -> None`
    - Widget'lar: `page_card() -> ui.card`, `stat_card(title: str, value, hint: str = "") -> None`, `status_badge(text: str, color: str) -> None` (color: `"green"`, `"yellow"`, `"red"`, `"gray"`), `empty_state(text: str) -> None`
    - `create_shell_frame(kernel, page_title: str) -> ui.column`: header ve sidebar'ı çizer, içerik kolonunu döndürür.
  - Erişim: `check_page_access(kernel, permission: str | None) -> bool`
    - `"auth"` servisi yoksa `True` döner.
    - Kullanıcı yoksa `/login` sayfasına yönlendirir ve `False` döner.
    - Kullanıcının izni yoksa "Yetkiniz yok" kartı çizer ve `False` döner.

- [ ] **Adım 1:** Testleri yaz:
  - `test_tree_nests_children`: `section:a` altında `group:1`, onun altında `script:x` olacak şekilde iç içe yerleşir.
  - `test_orphan_items_dropped`: `parent_key="section:silinmis"` olan öğe sonuçta yer almaz.
  - `test_sorted_by_order_then_label`
  - `test_self_parent_does_not_loop`: kendisini ebeveyn gösteren öğe sonsuz döngüye sokmaz.
  - `test_memory_db_tables_created`: test modeli eklenir, `create_all_tables` çağrılır, bir satır yazılıp okunur.
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - **`navigation.py`:** önce `key → NavNode` sözlüğü kurulur, sonra her düğüm ebeveyninin `children` listesine eklenir.
  - **`theme.py`:**
    - Sabitler: `PRIMARY_COLOR="#3C50E0"`, `BACKGROUND_COLOR="#F1F5F9"`, `CARD_CLASSES="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"`, `SIDEBAR_CLASSES`, `HEADER_CLASSES`.
    - `apply_theme` şunları yapar: Inter fontunu `ui.add_head_html` ile ekler, `ui.colors(primary=PRIMARY_COLOR)` çağırır, body'ye arka plan rengini ve fontu verir.
  - **`layout.py`:**
    - Header: sayfa başlığı; arama alanı (`ui.select`; seçenekler nav öğelerinin `label → path` eşlemesidir, seçim yapılınca o sayfaya gider); TR/EN düğmesi (`i18n` servisinin `set_language` metodunu çağırır ve sayfayı yeniler); koyu tema düğmesi (`app.storage.user["dark_mode"]` değerini değiştirir); kullanıcı menüsü ("Çıkış" seçeneği `auth.logout_current_user()` çağırıp `/login` sayfasına gider).
    - Sidebar: `ui.left_drawer` içinde ağaç, kendini çağıran bir `render_nav_node(node)` fonksiyonuyla çizilir. Çocuğu olan düğüm `ui.expansion` olur, olmayan düğüm `ui.link` stilinde bir satır olur. Aktif sayfa, `ui.context.client.page.path` ile karşılaştırılarak vurgulanır.
    - Kullanıcı bilgisi `kernel.get_service("auth")` üzerinden alınır; servis yoksa `None` kabul edilir.
  - **`main.py`:**
    - `parse_arguments()` → `--config` (varsayılan `config.toml`), `--only` (virgülle ayrılmış liste).
    - `main()` sırası: config yükle → `Kernel` → `set_kernel` → `init_database` → `load_plugins(kernel, "plugins", "plugins", only)` → `publish("plugins.loaded")` → `create_all_tables()` → `publish("database.ready")` → `/` sayfasını kaydet → `ui.run(title, port, storage_secret, reload=False)`.
    - `/` sayfası, kullanıcının nav ağacındaki ilk sayfaya gider; ağaç boşsa `empty_state` gösterir.
- [ ] **Adım 4:** Testler → PASS. `python -m app.main --only none` ile uygulama açılır ve boş kabuk görünür (bunu tarayıcıda gözle kontrol et).
- [ ] **Adım 5:** Commit: `feat(core): db, tema, kabuk çerçevesi ve main`.

### Task 4: `i18n` eklentisi

**Dosyalar:**
- Oluştur: `plugins/i18n/{__init__.py, plugin.py, translator.py, README.md}`, `app/core/locales/{tr.json,en.json}` (kabuk metinleri: `shell.logout`, `shell.search`, `shell.forbidden`, `shell.empty`…)
- Test: `tests/test_translator.py`

**Arayüzler:**
- Tüketir: `kernel.loaded_plugin_folders`, `"plugins.loaded"` event'i
- Üretir: `"i18n"` servisi (`class Translator(default_language: str)`):
  - `add_translations(language: str, entries: dict) -> None`
  - `load_folder(folder: str) -> None`: `<folder>/tr.json`, `en.json`
  - `translate(key: str, language: str, **values) -> str`
  - `t(key, **values) -> str`: dili oturumdan okur; istek bağlamı dışında varsayılan dili kullanır
  - `get_language() -> str`
  - `set_language(language: str) -> None`
  - `pick(text_tr: str, text_en: str) -> str`: aktif dile göre birini seçer; seçilen boşsa diğerini döndürür

- [ ] **Adım 1:** Testleri yaz:
  - `test_translate_existing`
  - `test_fallback_to_english`: TR'de olmayan anahtar için EN metni döner.
  - `test_fallback_to_key`
  - `test_format_values`: `"Merhaba {name}"` + `name="Ali"` → `"Merhaba Ali"`.
  - `test_missing_placeholder_value_returns_raw_text`: format hatasında ham metin döner, hata fırlatılmaz.
  - `test_load_folder_merges`: iki klasör yüklenince anahtarlar birleşir.
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - `Translator` sınıfını yaz.
  - Plugin `setup` şunları yapar: servisi kaydeder; `"plugins.loaded"` event'ine abone olur. Bu event geldiğinde `app/core/locales` ve her `loaded_plugin_folders/locales` klasörünü yükler.
  - Dil `app.storage.user["language"]` içinde tutulur. Bu değere erişim `RuntimeError` verirse varsayılan dil kullanılır.
- [ ] **Adım 4:** Testler → PASS.
- [ ] **Adım 5:** Commit: `feat(i18n): çeviri eklentisi`.

### Task 5: `auth` eklentisi (kullanıcı, rol, oturum, login)

**Dosyalar:**
- Oluştur: `plugins/auth/{__init__.py, plugin.py, models.py, passwords.py, service.py, login_page.py, locales/*.json, README.md}`
- Test: `tests/test_auth_service.py`

**Arayüzler:**
- Tüketir: `Base`, `get_session`, `"database.ready"` event'i, `kernel.config.initial_admin_password`
- Üretir:
  - Modeller:
    - `User`: `id`, `username` (unique), `full_name`, `password_hash`, `is_active`, `language`, `created_at`
    - `Role`: `id`, `name` (unique), `permissions_text` (izinler virgülle ayrılmış)
    - `UserRole`: `user_id`, `role_id`
  - Şifre fonksiyonları: `hash_password(plain: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`
  - `"auth"` servisi (`class AuthService`). Kullanıcı sözlüğü şu anahtarlara sahiptir: `id`, `username`, `full_name`, `roles: list[str]`, `permissions: list[str]`.
    - Giriş: `authenticate(username, password) -> dict | None`, `get_user_by_id(user_id) -> dict | None` (pasif kullanıcı için `None`)
    - Yetki: `has_permission(user: dict | None, permission: str) -> bool` (`*` izni her şeyi kapsar)
    - Oturum: `login_user(user: dict) -> None`, `logout_current_user() -> None`, `current_user() -> dict | None` (oturumdaki `user_id` ile her istekte DB'den okur)
    - Kullanıcı yönetimi: `list_users() -> list[dict]`, `create_user(username, full_name, password, role_names: list[str]) -> dict`, `update_user(user_id, full_name, is_active, role_names) -> None`, `change_password(user_id, new_password) -> None`
    - Rol yönetimi: `list_roles() -> list[dict]`, `create_role(name) -> None`, `set_role_permissions(role_name, permissions: list[str]) -> None`
    - Seed: `seed_defaults(initial_admin_password: str) -> None`
  - İzinler: `settings.users.manage`, `settings.roles.manage`
  - Event'ler: `auth.login`, `auth.login_failed`, `auth.logout` (data: `{"username": ...}`)

- [ ] **Adım 1:** Testleri yaz (bellek içi DB):
  - `test_seed_creates_roles_and_admin`: `admin`, `operator`, `viewer` rolleri oluşur; `admin` kullanıcısı `admin` rolüne sahiptir; seed iki kez çalışınca kopya kayıt oluşmaz.
  - `test_authenticate_ok_and_wrong_password`
  - `test_inactive_user_cannot_login_and_lookup_returns_none`
  - `test_has_permission_wildcard_and_specific`
  - `test_user_permissions_union_of_roles`: kullanıcının izinleri, rollerindeki izinlerin birleşimidir.
  - `test_duplicate_username_raises_valueerror`
  - `test_username_is_case_insensitive_on_login`: `Admin` ile giriş yapılabilir.
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - Servis kodu ve bcrypt kullanımını yaz. Kullanıcı adları kaydedilirken `lower().strip()` uygulanır.
  - `login_page.py`: `/login` sayfası. TailAdmin tarzında, ortalanmış bir kart; kullanıcı adı ve şifre alanları; `on_login_click` adlı bir handler. Başarılı girişte `/` sayfasına gider, hatalı girişte bildirim gösterir ve event yayınlar.
  - Plugin `setup` şunları yapar: modelleri import eder; servisi ve izinleri kaydeder; `"database.ready"` gelince `seed_defaults` çağırır.
  - Admin şifresi varsayılan değerse (`"admin"`) loglara uyarı yazılır.
- [ ] **Adım 4:** Testler → PASS. `python -m app.main --only i18n,auth` → login çalışır, çıkış yapınca tekrar login sayfasına dönülür.
- [ ] **Adım 5:** Commit: `feat(auth): kullanıcı, rol ve login`.

### Task 6: `menu` eklentisi (bölüm ve gruplar veride)

**Dosyalar:**
- Oluştur: `plugins/menu/{__init__.py, plugin.py, models.py, service.py, section_page.py, settings_panel.py, locales/*.json, README.md}`
- Test: `tests/test_menu_service.py`

**Arayüzler:**
- Tüketir: `"auth"` servisi (`has_permission`), `"i18n"` servisi (`pick`), `NavItem`, `SettingsPanel`, `widgets`
- Üretir:
  - Modeller:
    - `Section`: `id`, `key` (unique), `name_tr`, `name_en`, `icon`, `order`, `is_system`, `is_visible`, `path` (boşsa `/section/<key>`)
    - `MenuGroup`: `id`, `section_key`, `name_tr`, `name_en`, `order`
  - `"menu"` servisi (`class MenuService`):
    - Bölümler: `list_sections() -> list[dict]`, `create_section(key, name_tr, name_en, icon) -> None` (`key` yalnızca `[a-z0-9_]` olabilir, aksi halde `ValueError`), `update_section(key, name_tr, name_en, icon, order, is_visible) -> None`, `delete_section(key) -> None` (sistem bölümü için `ValueError`; bölümün grupları da silinir)
    - Gruplar: `list_groups(section_key: str | None = None) -> list[dict]`, `create_group(section_key, name_tr, name_en) -> int`, `delete_group(group_id) -> None`
    - Seed: `seed_defaults() -> None`
  - Nav öğesi anahtarları: bölümler `section:<key>`, gruplar `group:<id>` (ebeveyni `section:<section_key>`).
  - İzinler: her bölüm için `section.<key>.view` (bölüm oluşturulduğunda kaydedilir), `settings.menu.manage`
  - Sistem bölümlerinin yolları: `log` → `/log`, `settings` → `/settings`.

- [ ] **Adım 1:** Testleri yaz:
  - `test_seed_creates_five_sections_once`
  - `test_create_section_rejects_bad_key`: `"Ürün B"` → `ValueError`.
  - `test_delete_system_section_rejected`
  - `test_delete_section_removes_its_groups`
  - `test_nav_items_respect_visibility_and_permission`: gizli bölüm ve izinsiz bölüm nav öğesi üretmez.
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - Servisi ve nav provider'ı (`build_menu_nav_items(user)`) yaz.
  - `/section/{key}` sayfası: o bölümün altındaki nav öğelerini (`collect_nav_items` sonucundan) kartlar halinde listeler; öğe yoksa `empty_state` gösterir.
  - Ayar paneli "Menü": bölümler tablosu ve şu aksiyonlar: ekle (dialog), düzenle (dialog), gizle/göster, sil (onay dialog'u). Seçilen bölümün grupları ekle ve sil aksiyonlarıyla listelenir.
- [ ] **Adım 4:** Testler → PASS.
- [ ] **Adım 5:** Commit: `feat(menu): veri tabanlı menü ve menü editörü`.

### Task 7: `audit_log` eklentisi

**Dosyalar:**
- Oluştur: `plugins/audit_log/{__init__.py, plugin.py, models.py, service.py, log_page.py, locales/*.json, README.md}`
- Test: `tests/test_audit_service.py`

**Arayüzler:**
- Tüketir: event'ler `auth.login`, `auth.login_failed`, `auth.logout`, `script.finished`, `scripts.changed`, `settings.changed`
- Üretir:
  - Model: `AuditEntry` (`id`, `created_at`, `username`, `action`, `target`, `status` (`"ok"` / `"error"`), `duration_ms`, `details`)
  - `"audit"` servisi:
    - `write(username: str, action: str, target: str = "", status: str = "ok", duration_ms: int = 0, details: str = "") -> None`: `details` 4000 karakterde kırpılır.
    - `search(status: str | None, text: str, limit: int = 500) -> list[dict]`: en yeni kayıt önce gelir.
  - İzin: `log.view`

- [ ] **Adım 1:** Testleri yaz:
  - `test_event_is_written`: `script.finished` event'i (`{"username","script_id","success","duration_ms","error_text"}`) bir satır oluşturur; `success=False` ise `status` `"error"` olur.
  - `test_search_filters_status_and_text`
  - `test_long_details_truncated`
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - Her event için ayrı, adı olan bir handler fonksiyonu yaz.
  - `/log` sayfası: durum seçimi, arama kutusu, "Yenile" butonu ve `ui.table`. Durum hücresi renkli bir rozet olarak gösterilir.
- [ ] **Adım 4:** Testler → PASS.
- [ ] **Adım 5:** Commit: `feat(audit_log): işlem kayıtları ve Log sayfası`.

### Task 8: `settings_core` eklentisi

**Dosyalar:**
- Oluştur: `plugins/settings_core/{__init__.py, plugin.py, settings_page.py, users_panel.py, roles_panel.py, system_panel.py, database_panel.py, system_info.py, locales/*.json, README.md}`
- Test: `tests/test_system_info.py`

**Arayüzler:**
- Tüketir: `kernel.list_settings_panels()`, `kernel.list_permissions()`, `kernel.plugin_status`, `"auth"` servisi, `save_config_value`
- Üretir:
  - `/settings` sayfası: kullanıcının izinli olduğu panelleri sekmeler (`ui.tabs`) halinde gösterir.
  - Sistem bilgisi fonksiyonları:
    - `collect_system_info() -> dict`: anahtarlar `python_version`, `platform`, `nicegui_version`, `database_url_masked`
    - `list_installed_packages() -> list[dict]`: her öğe `{"name", "version"}` şeklindedir; `importlib.metadata` ile okunur
    - `mask_database_url(url: str) -> str`: şifreyi `***` ile değiştirir
  - İzinler: `settings.view`, `settings.system.view`, `settings.database.manage`

- [ ] **Adım 1:** Testleri yaz:
  - `test_mask_database_url`: `postgresql://u:secret@h/db` → `postgresql://u:***@h/db`; `sqlite:///x.db` değişmez.
  - `test_collect_system_info_keys`
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - Panelleri yaz; her panel kendi `SettingsPanel` kaydını yapar:
    - **Kullanıcılar:** tablo, ekle/düzenle dialog'u, şifre sıfırla, aktif/pasif.
    - **Roller:** rol seçilir, ardından `list_permissions()` sonucundaki izinler checkbox listesi olarak gösterilir, "Kaydet".
    - **Sistem:** bilgi kartları, eklenti durumları (rozetli), paket listesi.
    - **Veritabanı:** maskelenmiş URL gösterilir. "Bağlantıyı test et" (`create_engine(url).connect()` try/except içinde) ve "Kaydet" butonları vardır. Kaydet, `config.toml` dosyasını günceller ve "yeniden başlatın" uyarısı gösterir.
  - Paneller değişiklikte `settings.changed` event'i yayınlar.
- [ ] **Adım 4:** Testler → PASS. Tarayıcıda: admin bir operator kullanıcısı açar; operator ile girişte Settings menüde görünmez.
- [ ] **Adım 5:** Commit: `feat(settings_core): kullanıcı, rol, sistem ve DB ayarları`.

### Task 9: `forms` eklentisi

**Dosyalar:**
- Oluştur: `plugins/forms/{__init__.py, plugin.py, validation.py, builder.py, locales/*.json, README.md}`
- Test: `tests/test_form_validation.py`

**Arayüzler:**
- Tüketir: `FieldSpec`, `"i18n"` servisi (`pick`)
- Üretir:
  - `convert_and_validate(fields: list[FieldSpec], raw_values: dict) -> tuple[dict, list[str]]`
    - Tiplere çevirir: `int`, `float`, `bool`; `date` ve `datetime` ISO metin olarak kalır; `multichoice` liste olur.
    - Hata mesajları Türkçe/İngilizce çeviri anahtarıyla üretilir: `forms.required`, `forms.not_number`, `forms.too_small`, `forms.too_large`, `forms.not_in_options`.
  - `"forms"` servisi:
    - `build_form(fields: list[FieldSpec]) -> FormHandle`: çağrıldığı yerdeki NiceGUI bağlamına iki sütunlu bir grid çizer.
    - `class FormHandle`: `get_raw_values() -> dict`, `submit() -> tuple[dict, list[str]]` (hataları alanların altında gösterir)
  - Tip → widget eşlemesi:

    | Tip | Widget |
    |---|---|
    | `str` | `ui.input` |
    | `text` | `ui.textarea` |
    | `password` | `ui.input(password=True)` |
    | `int`, `float` | `ui.number` |
    | `bool` | `ui.switch` |
    | `choice` | `ui.select` |
    | `multichoice` | `ui.select(multiple=True)` |
    | `date` | `ui.input` + `props("type=date")` |
    | `datetime` | `props("type=datetime-local")` |
    | `file` | `ui.upload`; dosya `data/uploads/<uuid>_<ad>` olarak kaydedilir, değer bu yoldur |

    Hepsi `outlined` stilindedir.

- [ ] **Adım 1:** Testleri yaz:
  - `test_required_missing`
  - `test_int_conversion_and_bounds`: `"5"` → `5`; `min=10` ise hata.
  - `test_bool_conversion`
  - `test_choice_not_in_options`
  - `test_optional_empty_uses_default`
  - `test_unknown_type_treated_as_str`
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - `validation.py` UI'dan bağımsızdır; her tip için ayrı, adı olan bir çevirici fonksiyon içerir.
  - `builder.py` her tip için ayrı bir `create_<tip>_widget(field)` fonksiyonu içerir. Seçim `if/elif` zinciriyle yapılır.
- [ ] **Adım 4:** Testler → PASS.
- [ ] **Adım 5:** Commit: `feat(forms): alan şemasından form üretimi`.

### Task 10: Script motoru — docstring/imza parser

**Dosyalar:**
- Oluştur: `plugins/script_engine/{__init__.py, parser.py}`
- Test: `tests/test_script_parser.py`, `tests/sample_scripts/{full_metadata.py, signature_only.py, syntax_error.py, no_run.py, bad_yaml.py}`

**Arayüzler:**
- Tüketir: `FieldSpec`
- Üretir:
  - `@dataclass ScriptSpec`: `script_id`, `file_path`, `description`, `title_tr`, `title_en`, `suggested_section`, `suggested_group`, `mode="form"`, `roles: list[str]`, `timeout=60`, `refresh=30`, `schedule=""`, `fields: list[FieldSpec]`, `error: str = ""`
  - `parse_script_file(path: str) -> ScriptSpec`
    - Asla hata fırlatmaz; sorunları `error` alanına yazar.
    - Script'i import etmez; `ast` ile okur.
  - `make_script_id(file_name: str) -> str`: küçük harfe çevirir, Türkçe karakterleri ASCII'ye çevirir, `[a-z0-9_]` dışındakileri `_` yapar.

- [ ] **Adım 1:** Örnek script dosyalarını ve testleri yaz:
  - `test_full_metadata`: spec'teki örnek docstring'in alanları (title tr/en, mode, roles, timeout, inputs → `FieldSpec` listesi, `choice` seçenekleri, `min`/`max`) doğru okunur.
  - `test_signature_only`: `def run(host: str, port: int = 22, verbose: bool = False)` → 3 alan; `host` zorunlu, `port` varsayılanı `22` ve tipi `int`, `verbose` tipi `bool`. Başlık dosya adından üretilir.
  - `test_yaml_overrides_signature_label_and_type`
  - `test_syntax_error_sets_error`
  - `test_missing_run_sets_error`
  - `test_bad_yaml_sets_error`
  - `test_invalid_mode_sets_error`: `mode: foo`
  - `test_make_script_id`: `"Servis Yönet-1.py"` → `"servis_yonet_1"`
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - `ast.get_docstring` ile docstring alınır. Satırları `---` olan iki işaretin arasındaki bölüm `yaml.safe_load` ile okunur.
  - `run` adlı `FunctionDef` bulunur. Annotation adı eşlemesi: `str`, `int`, `float`, `bool`, `list` (→ `multichoice`), `date`, `datetime`; diğerleri `str` kabul edilir. Varsayılan değerler `ast.literal_eval` ile okunur.
  - YAML'daki `inputs` her alanı ada göre zenginleştirir. İmzada olmayan bir girdi varsa `error` alanına yazılır.
- [ ] **Adım 4:** Testler → PASS.
- [ ] **Adım 5:** Commit: `feat(script_engine): docstring ve imza parser`.

### Task 11: Script motoru — subprocess runner

**Dosyalar:**
- Oluştur: `plugins/script_engine/runner.py`, `plugins/script_engine/runner_shim.py`
- Test: `tests/test_script_runner.py` (geçici dizinde örnek script'ler)

**Arayüzler:**
- Üretir:
  - `@dataclass RunResult`: `success: bool`, `result` (JSON'a uygun değer), `output_text: str`, `error_text: str`, `duration_ms: int`, `timed_out: bool = False`
  - `run_script(file_path: str, arguments: dict, timeout_seconds: int) -> RunResult`
    - Komut: `[sys.executable, "-I", <runner_shim yolu>, file_path, <args json dosyası>]`
    - `capture_output=True`, `text=True`, `timeout=...`
  - `RESULT_MARKER = "__NGUI_RESULT__"`. Shim, sonucu `json.dumps(result, default=str, ensure_ascii=False)` ile marker satırına yazar. Hata olursa traceback'i stderr'e yazar ve 1 koduyla çıkar.
  - `output_text` 20000 karakterde kırpılır.

- [ ] **Adım 1:** Testleri yaz:
  - `test_returns_dict`
  - `test_print_output_captured_and_separated_from_result`
  - `test_exception_gives_error_text_with_message`
  - `test_timeout`: `time.sleep(5)` ve `timeout=1` → `timed_out=True`, `success=False`.
  - `test_non_json_result_stringified`: `datetime` ve `set` döndüren script hata vermez.
  - `test_huge_output_truncated`
  - `test_arguments_passed`: Türkçe karakterli metin argüman olarak doğru iletilir.
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz:
  - Shim, script'i `importlib.util.spec_from_file_location` ile yükler ve `run(**arguments)` çağırır.
  - Runner, stdout'taki son marker satırını sonuç olarak ayırır; geri kalan stdout `output_text` olur.
  - `subprocess.TimeoutExpired` yakalanır.
- [ ] **Adım 4:** Testler → PASS.
- [ ] **Adım 5:** Commit: `feat(script_engine): izole subprocess runner`.

### Task 12: Script motoru — servis, sayfalar, yükleme sihirbazı ve örnek script'ler

**Dosyalar:**
- Oluştur: `plugins/script_engine/{plugin.py, models.py, service.py, script_page.py, result_view.py, wizard.py, scripts_panel.py, locales/*.json, README.md}`, `scripts/{sistem_durumu.py (live), ping_testi.py (form), gunluk_ozet.py (scheduled)}`
- Test: `tests/test_script_service.py`

**Arayüzler:**
- Tüketir:
  - Task 10: `parse_script_file`, `make_script_id`
  - Task 11: `run_script`
  - Servisler: `"menu"` (`list_sections`, `list_groups`, `create_group`), `"forms"` (`build_form`), `"auth"` (`current_user`, `has_permission`, `list_roles`)
- Üretir:
  - Modeller:
    - `ScriptEntry`: `id`, `script_id` (unique), `file_name`, `title_tr`, `title_en`, `section_key`, `group_id` (boş olabilir), `mode`, `allowed_roles` (virgülle ayrılmış), `timeout`, `refresh`, `schedule`, `is_enabled`, `created_at`
    - `ScriptRun`: `id`, `script_id`, `username`, `started_at`, `success`, `duration_ms`, `result_json`, `output_text`, `error_text`
  - `"scripts"` servisi (`class ScriptService(scripts_folder: str)`):
    - Dosyalar ve listeleme:
      - `scan_folder() -> list[dict]`: klasördeki her `.py` dosyası için bir sözlük döner. Anahtarlar: `spec: ScriptSpec`, `entry: dict | None`, `is_orphan: bool`. Bölümü veya grubu artık var olmayan kayıt `is_orphan=True` olur.
      - `save_uploaded_file(file_name: str, content: bytes, overwrite: bool) -> str`: kaydedilen yolu döner. Uzantı `.py` değilse veya dosya varken `overwrite=False` ise `ValueError` fırlatır.
    - Yayınlama:
      - `publish(script_id, title_tr, title_en, section_key, group_id, mode, allowed_roles: list[str], timeout, refresh, schedule) -> None`: kayıt yoksa ekler, varsa günceller. Parse hatası varsa `ValueError` fırlatır.
      - `set_enabled(script_id, enabled: bool) -> None`
      - `remove(script_id) -> None`: kaydı ve dosyayı siler; `ScriptRun` geçmişi kalır.
    - Okuma ve yetki:
      - `get_entry(script_id) -> dict | None`
      - `can_user_run(user: dict, entry: dict) -> bool`: `admin` rolü ya da `allowed_roles` ile kesişim; `allowed_roles` boşsa herkes çalıştırabilir.
    - Çalıştırma ve geçmiş:
      - `execute(script_id, arguments: dict, username: str) -> RunResult`: `run_script` çağırır, `ScriptRun` yazar, `script.finished` event'i yayınlar.
      - `list_runs(script_id, limit: int = 50) -> list[dict]`
      - `last_run(script_id) -> dict | None`
    - Değişiklik bildirimi: `publish`, `set_enabled` ve `remove`, `scripts.changed` event'i yayınlar (data: `{"script_id"}`).
  - Nav provider: etkin ve kullanıcının çalıştırabildiği kayıtlar için `NavItem(key="script:<id>", parent_key="group:<gid>" veya "section:<key>", path="/script/<id>")`. İkonlar: `form` → `play_arrow`, `live` → `monitor_heart`, `scheduled` → `schedule`.
  - İzin: `scripts.manage`
  - Sonuç gösterimi: `show_result(result) -> None`
    - Skaler değerlerden oluşan `dict` → `stat_card` grid
    - `dict` listesi → `ui.table`
    - `str` → `ui.code` içinde
    - Diğerleri → `ui.json_editor` (salt okunur)

- [ ] **Adım 1:** Testleri yaz (bellek içi DB ve geçici scripts klasörü):
  - `test_publish_then_scan_shows_entry`
  - `test_publish_rejects_script_with_parse_error`
  - `test_upload_rejects_non_py_and_existing_without_overwrite`
  - `test_remove_deletes_file_and_entry_keeps_runs`
  - `test_can_user_run_roles`: admin her zaman çalıştırabilir; boş `allowed_roles` herkese açıktır; aksi halde kesişime bakılır.
  - `test_execute_records_run_and_publishes_event`
  - `test_orphan_when_section_missing`
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Servis ve modelleri yazınca testler → PASS.
- [ ] **Adım 4:** Sayfaları yaz:
  - **`/script/{script_id}`:** erişim kontrolü (`check_page_access` + `can_user_run`). Moda göre davranış:
    - `form`: form kartı → "Çalıştır" butonu → `await run.io_bound(service.execute, ...)` → sonuç kartı. Çalışma sırasında buton kilitli olur ve spinner görünür.
    - `live`: sayfa açılınca bir kez çalışır. `ui.timer(refresh, refresh_live_result)` her tetiklendiğinde sonuç kartını yeniden çizer. Formun varsayılan değerleri kullanılır.
    - `scheduled`: elle çalıştırma formu + `list_runs` tablosu (satıra tıklayınca sonuç dialog'da açılır).
  - **Yükleme sihirbazı** (`wizard.py`, `ui.stepper` ile, 3 adım):
    1. Dosya yükleme (`ui.upload`) veya listeden yayınlanmamış dosya seçimi.
    2. Algılanan alanlar tablosu, form önizlemesi ve varsa parse hatası.
    3. Yerleşim: başlık TR/EN; bölüm (select); grup (select + "Yeni grup" metni); mod; roller (multi-select); timeout, refresh, schedule (yalnızca ilgili modda görünür). Docstring'deki öneriler alanlara önceden doldurulur. "Yayınla" butonu.
  - **Ayar paneli "Scriptler":**
    - Tablo sütunları: başlık, dosya, bölüm/grup, mod, durum rozeti (yayında / devre dışı / hatalı / atanmamış / yayınlanmamış).
    - Satır aksiyonları: Düzenle (sihirbazı 3. adımdan açar), Devre dışı/Etkin, Kaldır (onay dialog'u).
    - Üstte "Yükle" ve "Yeniden tara" butonları.
- [ ] **Adım 5:** Örnek script'leri yaz (docstring'leri Türkçe ve tam):
  - `sistem_durumu.py` (`live`): CPU sayısı, disk doluluğu ve saati `dict` olarak döndürür.
  - `ping_testi.py` (`form`): `host` ve `count` alır, `subprocess` ile `ping` çalıştırıp çıktısını döndürür.
  - `gunluk_ozet.py` (`scheduled`, `schedule: "0 8 * * *"`): `dict` listesi döndürür.
- [ ] **Adım 6:** Tarayıcıda kontrol et: üç script sihirbazla yayınlanır; her biri kendi modunda çalışır; Log'da kayıtları görünür; kaldırılan script menüden kalkar.
- [ ] **Adım 7:** Commit: `feat(script_engine): yükleme sihirbazı, script sayfaları ve örnekler`.

### Task 13: `scheduler` eklentisi

**Dosyalar:**
- Oluştur: `plugins/scheduler/{__init__.py, plugin.py, jobs.py, README.md}`
- Test: `tests/test_scheduler_jobs.py`

**Arayüzler:**
- Tüketir: `"scripts"` servisi (`scan_folder`, `execute`), `scripts.changed` ve `database.ready` event'leri
- Üretir: `class ScriptScheduler`
  - `sync_jobs(entries: list[dict]) -> list[str]`: yalnızca `mode == "scheduled"`, etkin ve `schedule` alanı dolu kayıtlar için `CronTrigger.from_crontab` ile iş kurar. İş anahtarı `script:<id>`'dir. Geçersiz cron ifadesi loglanır ve atlanır. Kurulan işlerin anahtar listesini döndürür.
  - `run_job(script_id: str) -> None`: varsayılan değerlerle `execute(script_id, defaults, "scheduler")` çağırır.
  - `plugin.py`: `requires=["script_engine"]`. `BackgroundScheduler` NiceGUI `app.on_startup` ile başlar, `app.on_shutdown` ile durur.

- [ ] **Adım 1:** Testleri yaz (sahte bir scripts servisi ve başlatılmamış `BackgroundScheduler` ile):
  - `test_only_enabled_scheduled_entries_get_jobs`
  - `test_invalid_cron_skipped`
  - `test_resync_removes_deleted_jobs`
- [ ] **Adım 2:** Testler → FAIL.
- [ ] **Adım 3:** Kodu yaz.
- [ ] **Adım 4:** Testler → PASS.
- [ ] **Adım 5:** Commit: `feat(scheduler): periyodik rapor çalıştırma`.

### Task 14: Dokümantasyon ve uçtan uca doğrulama

**Dosyalar:**
- Oluştur: `docs/NASIL_CALISIR.md`, `plugins/ornek_eklenti_sablonu/` (kapalı şablon: `plugin.py`, `README.md`; `config.toml` içinde `disabled` listesinde)
- Değiştir: `README.md`

- [ ] **Adım 1:** `NASIL_CALISIR.md` dosyasını yaz. Bölümler:
  - Açılış sırası (`main.py` adım adım)
  - Bir sayfa isteğinin yolculuğu (`check_page_access` → `create_shell_frame` → içerik)
  - Bir script'in yolculuğu (yükle → parse → yayınla → nav → form → subprocess → `ScriptRun` → event → log)
  - Yeni eklenti yazma (şablonu kopyala, `plugin_id` değiştir, `disabled` listesinden çıkar)
  - Script docstring referansı (tüm alanlar ve tipler)
- [ ] **Adım 2:** `pytest -v` → hepsi PASS.
- [ ] **Adım 3:** `.claude/launch.json` dosyasına `python -m app.main` kaydını ekle ve uygulama içi tarayıcıda spec'teki doğrulama senaryosunu baştan sona uygula:
  - admin girişi → dil değiştirme → operator kullanıcısı açma → operator ile Settings'in görünmediğini kontrol etme
  - "urun_b" bölümünü oluşturma → script yükleyip bu bölüme yerleştirme → çalıştırma → Log kaydını görme → kaldırma
  - `config.toml` içinde `audit_log`'u kapatıp uygulamayı yeniden başlatma → Log'un kaybolduğunu ve uygulamanın çalıştığını görme
  - Koyu temayı kontrol etme
- [ ] **Adım 4:** Commit: `docs: nasıl çalışır rehberi ve eklenti şablonu`.
