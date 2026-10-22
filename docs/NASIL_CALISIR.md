# N-GUI Nasıl Çalışır?

> Diğer rehberler: kullanım ve işletme için [ADMINISTRATION_GUIDE.md](ADMINISTRATION_GUIDE.md),
> mimari, tasarım kararları ve görsel tasarım sistemi için [DESIGN_GUIDE.md](DESIGN_GUIDE.md).

Bu rehber, kod tabanını devralan geliştirici için yazıldı. Amaç şu: herhangi bir dosyayı açtığınızda
"bu nereden çağrılıyor, kime bağlanıyor" sorusunun cevabını bilmeniz. Her bölüm gerçek dosya ve
fonksiyon adlarını kullanır; ayrıntı için ilgili dosyanın başındaki açıklama bloğunu okuyun.

İçindekiler:

1. [Büyük resim](#1-büyük-resim)
2. [Açılış sırası (`app/main.py`)](#2-açılış-sırası-appmainpy)
3. [Bir sayfa isteğinin yolculuğu](#3-bir-sayfa-isteğinin-yolculuğu)
4. [Bir script'in yolculuğu](#4-bir-scriptin-yolculuğu)
5. [Yeni eklenti yazma](#5-yeni-eklenti-yazma)
6. [Script docstring referansı](#6-script-docstring-referansı)
7. [Olaylar, servisler, izinler ve roller](#7-olaylar-servisler-izinler-ve-roller)
8. [Bilinen sınırlar](#8-bilinen-sınırlar)

---

## 1. Büyük resim

Uygulama iki katmandan oluşur:

- **Çekirdek (`app/core/`)**: küçük ve kararlıdır, hiçbir eklentiyi import etmez.
  - `kernel.py`: `Kernel` sınıfı. Kayıt defterleri (servisler, izinler, menü sağlayıcıları, ayar panelleri) ve olay yolu (`kernel.events`).
  - `plugin.py`: eklenti sözleşmesi (`Plugin`) ve paylaşılan veri tipleri (`NavItem`, `SettingsPanel`).
  - `loader.py`: `plugins/` altındaki klasörleri bulur ve sırayla kurar.
  - `events.py`: `EventBus` (basit yayın/abone).
  - `config.py`: `config.toml` dosyasını `AppConfig` dataclass'ına okur, `save_config_value` ile tek değer yazar.
  - `db.py`: SQLAlchemy motoru, `get_session()` ve modellerin taban sınıfı `Base`.
  - `access.py`: `check_page_access(kernel, izin)`. Her sayfa bununla başlar.
  - `layout.py`: `create_shell_frame(kernel, başlık)`. Header, sol menü ve içerik kolonunu çizer.
  - `navigation.py`: düz `NavItem` listesini menü ağacına çevirir.
  - `theme.py`, `widgets.py`: renkler, Tailwind sınıfları ve ortak kart/rozet fonksiyonları.
  - `text.py`: `t("anahtar")` çeviri yardımcısı. i18n servisi yoksa anahtarın kendisini döndürür.
  - `field_spec.py`: form alanı tarifi `FieldSpec`. Script motoru ile forms eklentisi bu tipi paylaşır.
- **Eklentiler (`plugins/<ad>/`)**: her yetenek ayrı bir klasördedir.

| Eklenti | Ne yapar | `requires` |
|---|---|---|
| `i18n` | `"i18n"` servisi (`Translator`); TR/EN çeviriler | - |
| `auth` | `"auth"` servisi, `/login`, kullanıcı/rol tabloları, hazır roller ve admin | - |
| `menu` | `"menu"` servisi; bölüm ve gruplar DB'de, `/section/{key}`, Ayarlar > Menü | - |
| `forms` | `"forms"` servisi: `FieldSpec` listesinden form çizer ve doğrular | - |
| `audit_log` | `"audit"` servisi; olayları DB'ye yazar, `/log` sayfası | - |
| `settings_core` | `/settings` sayfası; Kullanıcılar, Roller, Sistem, Veritabanı panelleri | `auth` |
| `script_engine` | `"scripts"` servisi; script yükleme, yayınlama, `/script/{id}` | `forms`, `menu` |
| `scheduler` | `"scheduler"` servisi; `scheduled` modundaki script'leri cron ile çalıştırır | `script_engine` |
| `ornek_eklenti_sablonu` | Kopyalanacak şablon (`config.toml` içinde **kapalı**) | - |

Temel kural şudur: **eklentiler birbirini import etmez.** Bir eklenti başkasının işine ihtiyaç
duyarsa `kernel.get_service("ad")` ile servisi ister ya da bir olaya abone olur. Servis yoksa
(eklenti kapalıysa) `None` gelir ve kod buna göre davranır. Örneğin `auth` yoksa yetki
süzmesi yapılmaz, `i18n` yoksa çeviri anahtarları görünür.

---

## 2. Açılış sırası (`app/main.py`)

`.venv/bin/python -m app.main [--config config.toml] [--only a,b,c]` komutu `main()` fonksiyonunu çalıştırır:

1. **`parse_arguments()`** komut satırını okur. `--config` ayar dosyasını, `--only` ise yalnızca
   yüklenecek eklentileri belirler. Listede olmayan eklentiler "not selected" durumunu alır.
2. **`load_config(path)`** `config.toml` dosyasını `tomllib` ile okur ve bir `AppConfig` döndürür.
   Dosya yoksa ya da bir değer eksikse varsayılanlar kullanılır.
3. **`Kernel(config)`** oluşturulur ve **`set_kernel(kernel)`** ile modül düzeyinde saklanır.
   Sayfalar kernel'e daha sonra `get_kernel()` ile ulaşır.
4. **`init_database(config.database_url)`** motoru ve oturum fabrikasını kurar. SQLite dosyasının
   klasörü (`data/`) yoksa oluşturulur. Bu adımda henüz tablo oluşturulmaz.
5. **`load_plugins(kernel, "plugins", "plugins", only)`** (`app/core/loader.py`):
   - `discover_plugins` içinde `plugin.py` bulunan klasörleri alfabetik sırayla bulur.
   - `config.disabled_plugins` listesindekileri atlar ("disabled").
   - Diğerlerinin `plugins.<ad>.plugin` modülünü import eder ve `find_plugin_class` ile `Plugin`
     alt sınıfını bulup bir örnek oluşturur. **Import sırasında** modül düzeyindeki `@ui.page`
     dekoratörleri çalışır, yani sayfalar bu anda kaydolur (örneğin `auth/plugin.py` dosyası
     `login_page` modülünü import eder ve `/login` kaydolur).
   - Bağımlılıkları (`requires`) "loaded" olan eklentilerin `setup(kernel)` metodunu çağırır.
     Bu adım, ilerleme kalmayana dek tekrarlanır; böylece sıra bağımlılığa göre kendiliğinden oluşur.
   - Her `setup` try/except içindedir. Hata veren eklenti `"failed: <hata>"` olarak işaretlenir,
     diğerleri yüklenmeye devam eder. Bağımlılığı yüklenemeyen eklenti `"missing dependency: <ad>"` alır.
   - Sonuç `kernel.plugin_status` sözlüğüne yazılır. Bu sözlük Ayarlar > Sistem panelinde görünür.
     Yüklenen klasörler `kernel.loaded_plugin_folders` listesinde tutulur.
6. **`kernel.events.publish("plugins.loaded", {})`**: `i18n` bu olayda çekirdeğin
   (`app/core/locales/`) ve yüklenen her eklentinin `locales/tr.json` ve `en.json` dosyalarını okur.
7. **`create_all_tables()`**: eklentiler modellerini `setup` sırasında import ettiği için
   `Base.metadata` artık tüm tabloları bilir. Var olmayan tablolar oluşturulur. Var olan tablolara
   modelde olup tabloda olmayan sütunlar `add_missing_columns` ile eklenir (basit, yalnızca eklemeli göç).
8. **`kernel.events.publish("database.ready", {})`**: tablolar hazır olduktan sonra hazır kayıtlar (seed) eklenir.
   - `auth`: `seed_defaults` ile `admin`, `operator` ve `viewer` rollerini ve `admin` kullanıcısını oluşturur
     (parola: `[auth] initial_admin_password`; ilk admin için uzunluk kuralı uygulanmaz).
   - `menu`: `seed_defaults` ile `dashboard`, `operation`, `report`, `log` ve `settings` bölümlerini ekler.
     `register_all_section_permissions` her bölüm için `section.<key>.view` iznini kaydeder.
     `log` ve `settings` sistem bölümleridir: menü, sahibi eklenti (`audit_log`, `settings_core`)
     yüklü değilse bu bölümü göstermez. Eşleme `plugins/menu/service.py` içindeki
     `SYSTEM_SECTION_OWNERS` sözlüğündedir; yeni bir sistem bölümü eklenirse oraya da eklenmelidir.
   - `scheduler`: zamanlanmış işleri eşitler.
   - `audit_log` ve `script_engine`: `[audit] retention_days` doluysa eski Log ve çalışma
     kayıtlarını siler (aynı temizlik `app.timer` ile günde bir tekrarlanır).
9. Eklenti durumları loglanır ve **`enforce_security(kernel)`** güvenlik kontrolünü yapar:
   varsayılan/kısa `storage_secret` ve `admin` parolasının hâlâ `"admin"` olması `Güvenlik:` uyarısı
   olarak yazılır; `[app] environment = "production"` ise uygulama `sys.exit(1)` ile durur.
10. **`ui.run(...)`** NiceGUI sunucusunu başlatır
   (`storage_secret` oturum çerezini imzalar, `reload=False`). `scheduler` eklentisi kendi
   zamanlayıcısını `app.on_startup` ile başlatır ve `app.on_shutdown` ile durdurur.

`main.py` ayrıca `"/"` sayfasını (`home_page`) kaydeder. Bu sayfa giriş kontrolünden sonra
kullanıcının menüsündeki ilk sayfaya (`find_first_page_path`) yönlendirir. Menü boşsa boş bir kabuk gösterir.
`ui.run(root=not_found_page)` ile verilen `not_found_page` ise eşleşen sayfası olmayan her adreste
çağrılır ve kabuk içinde çevrilmiş bir "Sayfa bulunamadı" kartı çizer (kapalı bir eklentinin `/log` adresi gibi).

---

## 3. Bir sayfa isteğinin yolculuğu

Örnek: giriş yapmış bir kullanıcı `/section/operation` adresini açıyor
(`plugins/menu/section_page.py` içindeki `section_page`).

1. **NiceGUI** adresi `@ui.page("/section/{key}")` ile kaydedilmiş fonksiyona yönlendirir.
2. **İlk satır yetki kontrolüdür:**
   ```python
   kernel = get_kernel()
   if not check_page_access(kernel, "section." + key + ".view"):
       return
   ```
   `check_page_access` (`app/core/access.py`) şöyle çalışır:
   - `"auth"` servisi yoksa (auth eklentisi kapalıysa) her sayfa açıktır ve `True` döner.
   - `auth.current_user()` kullanıcıyı her istekte veritabanından okur. Oturumda yalnızca
     `app.storage.user["user_id"]` tutulur. Kullanıcı yoksa, silinmişse ya da pasifse
     `/login` adresine yönlendirilir ve `False` döner. Ayrı bir middleware yoktur; kontrolü her sayfa kendisi yapar.
   - İzin `None` ise giriş yapmış olmak yeterlidir.
   - `auth.has_permission(user, izin)`: kullanıcının rollerindeki izinlerde `"*"` ya da aranan anahtar varsa `True` döner.
   - İzin yoksa çerçeve ve "Bu sayfaya erişim izniniz yok" kartı çizilir, `False` döner.
     Kullanıcı menüyü kullanarak başka sayfaya geçebilir.
3. **`create_shell_frame(kernel, başlık)`** (`app/core/layout.py`):
   - `apply_theme()`: renkler, font, ek CSS (`EXTRA_CSS`) ve koyu tema. Koyu tema `app.storage.user["dark_mode"]`
     değerine bağlıdır. Ayrıca sayfaya `<html lang>` değerini ve Türkçe için Quasar dil paketini ekler.
   - `draw_sidebar` sol menünün çerçevesini (logo ve boş bir menü kolonu), `draw_header` üst çubuğu
     çizer: menü düğmesi, başlık, arama, TR/EN düğmesi (`on_language_click`: dili değiştirir ve sayfayı
     yeniden yükler), tema düğmesi (`on_dark_mode_click`; ipucu geçilecek temayı söyler) ve kullanıcı
     menüsü ("Çıkış" için `on_logout_click`). Telefon genişliğinde arama ve kullanıcı adı gizlenir.
   - İç fonksiyon `redraw_navigation` menüyü doldurur: `kernel.collect_nav_items(user)` tüm menü
     sağlayıcılarını çağırır (`menu` bölüm ve grupları, `script_engine` script'leri verir; hata veren
     sağlayıcı atlanır), `build_navigation_tree` düz listeyi `parent_key` ile ağaca çevirir (sahipsiz
     öğeler atılır), ağaç menü kolonuna çizilir ve arama seçenekleri güncellenir. Fonksiyon
     `app.storage.client` içinde saklanır.
   - Dönüş değeri içerik kolonudur (`ui.column`).
4. **İçerik**: sayfa kendi kartlarını `with content:` bloğu içine çizer (`page_card()`, `stat_card()`, `empty_state()`...).

Önemli ayrıntılar:

- Menü her sayfa çiziminde yeniden hesaplanır. Ayarlar'daki paneller menüyü etkileyen bir
  değişiklikten sonra (script yayınlama/kaldırma/devre dışı bırakma, bölüm ve grup düzenleme, rol
  değişikliği) `refresh_navigation()` çağırır; açık sekmenin menüsü sayfa yenilenmeden güncellenir.
  Diğer kullanıcılar değişikliği bir sonraki sayfa açılışında görür. `refresh_navigation()` paneli
  yeniden çizmeden **önce** çağrılmalıdır: yeniden çizim tıklanan düğmeyi siler ve NiceGUI bağlamı kaybolur.
- Metinler `t()` ile çizim anında çevrilir. Dil `app.storage.user["language"]` içinde durur.
  Bir anahtar seçilen dilde yoksa önce `en`, o da yoksa anahtarın kendisi gösterilir.
- `/script/{script_id}` sayfası `check_page_access(kernel, None)` ile yalnızca girişi kontrol eder.
  Çalıştırma yetkisi ayrıca `scripts.can_user_run(user, entry)` ile denetlenir (bkz. bölüm 7).

---

## 4. Bir script'in yolculuğu

Örnek: admin `ping_testi.py` dosyasını yüklüyor, "Ürün B" bölümüne yerleştiriyor ve bir operatör onu çalıştırıyor.

**1. Yükleme** (`plugins/script_engine/wizard.py`, `ScriptWizard`): Ayarlar > Scriptler > "Yükle".
- Adım 1, "Dosya": `.py` dosyası `ui.upload` ile yüklenir ya da `scripts/` klasöründe duran ama
  henüz yayınlanmamış bir dosya seçilir. Yüklenen dosya `service.save_uploaded_file()` ile
  `<script_id>.py` adıyla `[scripts] folder` klasörüne yazılır.
- Script kimliği `make_script_id(dosya_adı)` ile üretilir: Türkçe harfler ASCII'ye çevrilir,
  küçük harf yapılır ve yalnızca `[a-z0-9_]` karakterleri kalır.

**2. Parse** (`plugins/script_engine/parser.py`, `parse_script_file(path)`):
- Script **import edilmez**. Dosya metni `ast.parse` ile okunur, bu yüzden hatalı ya da zararlı
  bir dosya uygulamayı etkileyemez.
- `find_run_function` modül düzeyindeki `run` fonksiyonunu bulur, `fields_from_signature`
  parametrelerinden alan (`FieldSpec`) listesi üretir. Tip ipucu alan tipini, varsayılan değer
  `default` değerini belirler. Varsayılanı olmayan parametre zorunludur.
- Docstring `split_docstring` ile açıklama ve `---` arasındaki YAML olarak ikiye ayrılır.
  `apply_yaml_settings` ayarları, `apply_yaml_inputs` girdi tariflerini uygular.
- Sonuç bir `ScriptSpec` dataclass'ıdır. Sorun varsa hata fırlatılmaz; `spec.error` alanına
  Türkçe bir mesaj yazılır. Hatalı script listede "hatalı" durumuyla görünür ve yayınlanamaz.
- Adım 2, "Önizleme": algılanan alanlar tablosu ve formun canlı önizlemesi
  (`forms.build_form(spec.fields)`) gösterilir.

**3. Yayınla** (adım 3, "Yerleşim" → `service.publish(...)`):
- Admin başlık (TR/EN), bölüm, grup (ya da "yeni grup" adı), görünüm modu, roller, zaman aşımı,
  yenileme aralığı ve cron programını seçer. Docstring'deki öneriler alanlara önceden doldurulur.
  Docstring bölüm önermiyorsa moda göre varsayılan kullanılır: `form` → operation, `live` → dashboard, `scheduled` → report.
- `publish` dosyayı yeniden parse eder, modu ve bölüm/grubu (`check_placement`) doğrular, sonra
  `ScriptEntry` tablosuna kaydı yazar ya da günceller ve `"scripts.changed"` olayını
  `change="published"` ile yayınlar. `audit_log` bu olayı kaydeder, `scheduler` işlerini yeniden eşitler.

**4. Menü** (`service.build_nav_items(user)`):
- Etkin ve kullanıcının çalıştırabildiği her kayıt için bir `NavItem` üretilir: `key="script:<id>"`,
  `path="/script/<id>"`, ebeveyn olarak `group:<id>` ya da `section:<key>`.
- Bölümü ya da grubu silinmiş kaydın ebeveyni bulunamaz; menü ağacı onu göstermez ("sahipsiz").

**5. Form** (`plugins/script_engine/script_page.py`, `/script/{script_id}`):
- Sayfa `check_page_access(kernel, None)` ve `user_may_run` kontrollerinden sonra `ScriptPageView.build()` ile çizilir.
- Mod `form` ise `forms.build_form(spec.fields)` iki sütunlu (telefonda tek sütun) formu çizer. "Çalıştır" düğmesi
  `on_run_click` metodunu çağırır. Bu metot `form.submit()` ile değerleri doğrular; hata varsa script çalıştırılmaz.

**6. Subprocess** (`service.execute` → `prepare_and_run` → `runner.run_script`):
- Arayüz kilitlenmesin diye çağrı `await run.io_bound(service.execute, ...)` ile ayrı bir thread'de yapılır.
- `prepare_and_run` kaydı ve dosyayı kontrol eder, dosyayı yeniden parse eder (değişmemişse
  `parse_cache` önbelleğinden) ve argümanları `forms.convert_and_validate` ile tiplerine çevirip doğrular.
- `run_script` argümanları geçici bir JSON dosyasına yazar ve şu komutu başlatır:
  `<python> -I -B runner_shim.py <script> <args.json>`. `<python>` `[scripts] python` ayarıdır
  (boşsa uygulamanın yorumlayıcısı). Komut script'in klasöründe, yeni bir süreç grubunda ve yalnızca
  `[scripts] env_passthrough` listesindeki ortam değişkenleriyle çalışır.
- Çalıştırma bitince (başarılı ya da değil) dosya alanlarına yüklenmiş dosyalar
  `forms.discard_uploaded_file` ile silinir.
- `runner_shim.py` script'i yükler, `run(**argümanlar)` çağırır ve dönen değeri stdout'a
  `__NGUI_RESULT__` ile başlayan tek bir satır olarak yazar. Hata olursa traceback stderr'e gider ve çıkış kodu 1 olur.
- Süre (`timeout`) dolarsa süreç grubu `killpg` ile öldürülür (macOS/Linux).
- Sonuç bir `RunResult` olur: `success`, `result`, `output_text` (print çıktıları), `error_text`,
  `duration_ms`, `timed_out`. Hiçbir durumda istisna fırlatılmaz.

**7. `ScriptRun`**: `record_run` çalıştırmayı `ScriptRun` tablosuna yazar. Script kaldırılsa bile bu geçmiş silinmez.

**8. Olay**: `execute` şu olayı yayınlar:
`"script.finished"` → `{"username", "script_id", "success", "duration_ms", "error_text"}`.

**9. Log**: `audit_log` eklentisi `on_script_finished` ile bu olayı `action="script.run"`,
`status="ok"/"error"` olarak `AuditEntry` tablosuna yazar. Kayıt `/log` sayfasında görünür.

**Sonuç gösterimi** (`result_view.py`): değerleri tek değer (skaler) olan bir `dict` istatistik kartlarına
(`True`/`False` "Evet"/"Hayır", `None` "-" olarak gösterilir; `display_value`),
`dict` listesi tabloya dönüşür. `str` kod bloğu olarak, diğer değerler salt okunur JSON olarak gösterilir.
`print` çıktısı "Çıktı" bölümünde görünür.

**Modlara göre fark:**
- `form`: form kartı → "Çalıştır" → sonuç kartı.
- `live`: sayfa açılınca ve sonra her `refresh` saniyede bir (`ui.timer`) `service.run_live` çağrılır.
  `run_live` sonucu **izleyiciler arasında paylaşır**: önbellekteki sonuç `refresh - 1` saniyeden
  yeniyse script çalıştırılmaz; script başına bir kilit aynı anda tek çalıştırma yapılmasını sağlar.
  Script alanların varsayılan değerleriyle çalışır. **Başarılı sonuç yalnızca pano bir süredir
  izlenmiyorken** (önceki sonuç iki aralıktan eskiyse) geçmişe ve Log'a yazılır; diğer başarılı
  yenilemeler `execute(..., record_success=False)` ile yazılmaz, başarısızlar her zaman yazılır.
  "Son güncelleme" etiketi sonucun üretildiği saati gösterir.
- `scheduled`: elle çalıştırma formu ve geçmiş çalıştırmalar tablosu. Satıra tıklanınca sonuç
  bir dialogda açılır. `scheduler` eklentisi kaydı `schedule` cron ifadesine göre `"scheduler"`
  kullanıcısı adına çalıştırır. Yalnızca varsayılanı olan alanlar verilir.

**Kaldırma**: Ayarlar > Scriptler > satırdaki çöp kutusu → `service.remove(script_id)`. Bu işlem
`ScriptEntry` kaydını ve **diskteki dosyayı** siler, sonra `"scripts.changed"` olayını
`change="removed"` ile yayınlar. Script menüden kalkar, `/script/<id>` adresi "bulunamadı" gösterir
ve çalıştırma geçmişi kalır. Satırdaki anahtar düğmesi ise kaydı yalnızca devre dışı bırakır (`set_enabled`).

---

## 5. Yeni eklenti yazma

Hazır şablon: `plugins/ornek_eklenti_sablonu/`. Bir izin, bir menü öğesi ve bir sayfa ekler.
`config.toml` içinde kapalıdır.

1. **Şablonu kopyalayın:**
   ```bash
   cp -r plugins/ornek_eklenti_sablonu plugins/stok_takip
   ```
2. **`plugin_id` değerini değiştirin.** `plugins/stok_takip/plugin.py` içinde:
   - `plugin_id = "stok_takip"` ve `name = "stok_takip"`. Klasör adıyla aynı olmalı; `requires`
     listeleri ve `disabled` listesi bu adı kullanır.
   - Sınıf adını (`StokTakipPlugin`), `PAGE_PATH` (`"/stok-takip"`), `VIEW_PERMISSION`
     (`"stok_takip.view"`) ve `NavItem` `key` değerlerini değiştirin.
   - `locales/tr.json` ve `en.json` içindeki `ornek_eklenti.` önekli anahtarları `stok_takip.` ile değiştirin.
3. **`disabled` listesinden çıkarın.** Kopyaladığınız klasörün adı `config.toml` içindeki
   `[plugins] disabled` listesinde olmamalıdır. Şablonun kendisi listede kalabilir.
4. **Yeniden başlatın ve deneyin.** Tek başına denemek için:
   ```bash
   .venv/bin/python -m app.main --only auth,i18n,menu,stok_takip
   ```
   Durum Ayarlar > Sistem panelinde ("loaded" / "failed: ..." / "missing dependency: ...") ve konsol logunda görünür.

`setup(kernel)` içinde yapabilecekleriniz:

| İhtiyaç | Kod |
|---|---|
| Servis sunmak | `kernel.register_service("stok", StokService(kernel))` |
| Başka eklentinin servisini kullanmak | `forms = kernel.get_service("forms")` (kapalıysa `None`) |
| İzin tanımlamak | `kernel.register_permission("stok_takip.view", "stok_takip.permission.view")` |
| Menü öğesi eklemek | `kernel.add_nav_provider(self.build_nav_items)`: fonksiyon `user` alır, `list[NavItem]` döner |
| Ayarlar'a sekme eklemek | `kernel.register_settings_panel(SettingsPanel(key, label_key, icon, permission, build_function))` |
| Olay dinlemek | `kernel.events.subscribe("script.finished", self.on_script_finished)` |
| Olay yayınlamak | `kernel.events.publish("stok.updated", {"username": ...})` |
| Tablo eklemek | `models.py` içinde `app.core.db.Base` alt sınıfı yazıp `plugin.py` içinde import edin. Tablo açılışta oluşturulur |
| Seed verisi | `kernel.events.subscribe("database.ready", self.on_database_ready)` |
| Sayfa eklemek | Modül düzeyinde `@ui.page("/adres")`. İlk satır `if not check_page_access(kernel, "<izin>"): return` olmalı |

Kurallar (`docs/superpowers/specs/2026-10-22-modular-shell-design.md`, "Kod yazım kuralları"):
lambda, closure, kendi yazdığımız decorator, `functools.partial` ve karmaşık comprehension kullanılmaz.
Düğme handler'ları isimli fonksiyonlar ya da metotlardır. Her dosyanın başında Türkçe açıklama bloğu,
her fonksiyonda Türkçe docstring bulunur. Veri tutucular için `dataclass` kullanılır. Eklentiler
`plugins.X` modüllerini import etmez. Bir bölümün altına menü öğesi koymak için `parent_key="section:<key>"` verin.

Sayfa kaydı hakkında bir not: `@ui.page`, `plugin.py` (ya da onun import ettiği bir modül) import
edildiği anda çalışır. Kapalı eklentinin modülü import edilmediği için sayfası da kaydolmaz.

---

## 6. Script docstring referansı

```python
"""Kısa açıklama (sayfada başlığın altında görünür).

İstenirse birkaç satır daha açıklama.
---
title: {tr: Servis Yeniden Başlat, en: Restart Service}
section: Operation
group: Ürün A
mode: form
roles: [operator, admin]
timeout: 60
refresh: 30
schedule: "0 8 * * 1"
inputs:
  host: {type: str, label: {tr: Sunucu, en: Host}, required: true, help: "Örnek: 10.0.0.5"}
  port: {type: int, default: 22, min: 1, max: 65535}
  restart_mode: {type: choice, options: [soft, hard], default: soft}
  start: {type: date}
---
"""
def run(host: str, port: int = 22, restart_mode: str = "soft", start=None):
    return {"durum": "ok"}
```

### Üst düzey anahtarlar

| Anahtar | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `title` | metin ya da `{tr, en}` | dosya adından (`ping_testi` → "Ping testi") | Menü ve sayfa başlığı. Biri eksikse diğeri kullanılır |
| `section` | metin | boş | Bölüm **önerisi** (anahtar ya da TR/EN ad, büyük/küçük harf fark etmez). Asıl yer sihirbazda seçilir |
| `group` | metin | boş | Grup önerisi. Eşleşen grup yoksa sihirbaz bunu "yeni grup" olarak önerir |
| `mode` | `form` \| `live` \| `scheduled` | `form` | Görünüm modu (bkz. bölüm 4) |
| `roles` | metin listesi | `[]` | Çalıştırabilecek roller. Boşsa giriş yapmış herkes çalıştırır. `admin` her zaman çalıştırır |
| `timeout` | pozitif tam sayı | `60` | Saniye. Süre dolunca süreç grubu öldürülür |
| `refresh` | pozitif tam sayı | `30` | `live` modunda yenileme aralığı (saniye) |
| `schedule` | cron metni | boş | `scheduled` modunda 5 alanlı cron: `dakika saat gün ay haftanın-günü` |
| `inputs` | sözlük | - | Alan adı → alan tarifi |

### Alan tarifi anahtarları (`inputs` altında)

| Anahtar | Açıklama |
|---|---|
| `type` | 11 tipten biri (aşağıda). Verilmezse tip ipucundan gelir |
| `label` | metin ya da `{tr, en}`. Verilmezse alan adı kullanılır |
| `required` | `true` / `false` (yalnızca gerçek bool kabul edilir). Verilmezse imzaya bakılır: varsayılanı yoksa zorunludur |
| `default` | Varsayılan değer. İmzadaki varsayılanın üzerine yazar |
| `options` | Liste; `choice` ve `multichoice` için seçenekler |
| `min`, `max` | Sayısal sınırlar (`int`, `float`). Tip çevrildikten sonra denetlenir |
| `help` | Alanın altında görünen yardım metni |

### 11 alan tipi

| Tip | Form bileşeni | Değer |
|---|---|---|
| `str` | tek satır input | metin |
| `text` | çok satırlı textarea | metin |
| `int` | sayı girişi | tam sayı (`"5.5"` hatadır) |
| `float` | sayı girişi | ondalıklı sayı |
| `bool` | anahtar (switch) | `True`/`False` (`true/false/1/0/on/off` metinleri de kabul edilir) |
| `choice` | açılır liste | `options` içinden bir değer |
| `multichoice` | çoklu seçimli liste | `options` içinden değerler listesi |
| `date` | tarih girişi | `"YYYY-MM-DD"` metni |
| `datetime` | tarih-saat girişi | `"YYYY-MM-DDTHH:MM"` metni |
| `file` | dosya yükleme | sunucudaki dosya yolu (`data/uploads/<uuid>_<ad>`) |
| `password` | gizli input | metin |

Tip ipucundan otomatik eşleme (`ANNOTATION_TYPES`): `str`→str, `int`→int, `float`→float,
`bool`→bool, `list`/`list[...]`→multichoice, `date`→date, `datetime`→datetime. Diğer her şey ve tip ipucu olmayan parametre `str` sayılır.

### Alanlar nereden gelir?

- **Temel kaynak `run()` imzasıdır.** Docstring hiç olmasa bile parametrelerden form üretilir.
  YAML `inputs` yalnızca **aynı adlı** parametreyi zenginleştirir (etiket, tip, seçenekler, sınırlar).
- `inputs` içinde imzada olmayan bir ad varsa:
  - `run(**kwargs)` biçiminde bir **`**kwargs`** parametresi varsa bu girdi **YAML'dan yeni bir alan olarak eklenir**
    (tip verilmezse `str`, `required` verilmezse isteğe bağlı). Yani `def run(**kwargs)` yazan
    bir script'in bütün alanları YAML'dan gelir.
  - `**kwargs` yoksa bu bir hatadır: `inputs içindeki 'x' run() imzasında yok`.
- `*args` ve `**kwargs` parametrelerinin kendisi alan olmaz.
- Boş bırakılan isteğe bağlı alan `default` değerini alır. Boş bırakılan zorunlu alan doğrulama hatası verir.

### `run()` ne döndürmeli?

JSON'a çevrilebilen bir değer: `dict` (tek değerliyse kartlar), `dict` listesi (tablo), `str` (metin),
sayı ya da liste. JSON'a uymayan değerler (`datetime` gibi) `str` ile metne çevrilir. Hata
göstermek için istisna fırlatın: sonuç "Başarısız" olur ve traceback "Hata" bölümünde görünür.
Örnekler için `scripts/ping_testi.py` (form), `scripts/sistem_durumu.py` (live) ve `scripts/gunluk_ozet.py` (scheduled) dosyalarına bakın.

### Sık görülen parse hataları

`Satır N: söz dizimi hatası`, `run() fonksiyonu bulunamadı`, `YAML okunamadı: ...`, `Geçersiz mod: x`,
`Geçersiz alan tipi: x (girdi 'y')`, `roles bir liste olmalı`, `timeout pozitif bir tam sayı olmalı`,
`Girdi 'x' required true/false olmalı`.

---

## 7. Olaylar, servisler, izinler ve roller

### Olaylar (`kernel.events`)

| Olay | Yayınlayan | Veri | Dinleyen |
|---|---|---|---|
| `plugins.loaded` | `main.py` | `{}` | `i18n` (çevirileri yükler) |
| `database.ready` | `main.py` | `{}` | `auth`, `menu` (seed), `scheduler` (eşitleme), `audit_log` ve `script_engine` (saklama süresi temizliği) |
| `auth.login` | `auth/login_page.py` | `{"username"}` | `audit_log` |
| `auth.login_failed` | `auth/login_page.py` | `{"username", "reason"?}`; hesap kilitliyse `reason: "locked"` | `audit_log` (status error) |
| `auth.logout` | `auth/service.py` | `{"username"}` | `audit_log` |
| `auth.password_changed` | `auth/password_dialog.py` | `{"username"}` | `audit_log` |
| `script.finished` | `script_engine/service.py` (`execute`) | `{"username", "script_id", "success", "duration_ms", "error_text"}` | `audit_log` (`script.run`) |
| `scripts.changed` | `script_engine/service.py` | `{"script_id", "change", "username"}`; `change`: `published`/`enabled`/`disabled`/`removed` | `audit_log`, `scheduler` |
| `settings.changed` | `settings_core/changes.py`, `menu/settings_panel.py` | `{"username", "setting", "details"}`; `setting`: `users`/`roles`/`database`/`menu` | `audit_log` |

Bir handler hata verirse `EventBus.publish` hatayı loglar ve diğer handler'ları çağırmaya devam eder.

### Servisler (`kernel.get_service(ad)`)

`"i18n"`, `"auth"`, `"menu"`, `"forms"`, `"audit"`, `"scripts"`, `"scheduler"`. Her eklentinin
`README.md` dosyası kendi servis metotlarını listeler.

### İzin anahtarları

| İzin | Kaydeden | Ne açar |
|---|---|---|
| `section.<key>.view` | `menu` (her bölüm için) | Bölümün menüde görünmesi ve `/section/<key>` sayfası |
| `settings.menu.manage` | `menu` | Ayarlar > Menü |
| `settings.users.manage` | `auth` | Ayarlar > Kullanıcılar |
| `settings.roles.manage` | `auth` | Ayarlar > Roller |
| `settings.view` | `settings_core` | `/settings` sayfası |
| `settings.system.view` | `settings_core` | Ayarlar > Sistem |
| `settings.database.manage` | `settings_core` | Ayarlar > Veritabanı |
| `log.view` | `audit_log` | `/log` sayfası |
| `scripts.manage` | `script_engine` | Ayarlar > Scriptler (yükleme, yayınlama, kaldırma) |

### Hazır roller (`plugins/auth/service.py`, `DEFAULT_ROLES`)

| Rol | İzinler |
|---|---|
| `admin` | `*` (her şey) |
| `operator` | `section.dashboard.view`, `section.operation.view`, `section.report.view`, `section.log.view`, `log.view` |
| `viewer` | `section.dashboard.view`, `section.report.view` |

Rol-izin eşlemesi Ayarlar > Roller ekranından değiştirilebilir. Yeni bir bölüm oluşturduğunuzda
(örneğin `urun_b`) yalnızca admin görür. Diğer rollerin görmesi için o role `section.urun_b.view` izni verilmelidir.

**Script çalıştırma yetkisi** izinle değil rol listesiyle belirlenir (`ScriptService.can_user_run`):
kullanıcının `admin` rolü ya da `*` izni varsa her zaman çalıştırabilir. Kaydın `allowed_roles`
listesi boşsa giriş yapmış herkes çalıştırabilir. Aksi halde kullanıcının rollerinden en az biri listede olmalıdır.

### Oturumda saklananlar (`app.storage.user`)

`user_id` (giriş), `language` (`tr`/`en`) ve `dark_mode` (`True`/`False`). Bu değerler `storage_secret`
ile imzalanmış çerez üzerinden tarayıcıya bağlıdır ve sunucuda `.nicegui/` klasöründe tutulur.

---

## 8. Bilinen sınırlar

- Script runner süreç grubunu `os.killpg` ile öldürür. Bu yöntem macOS/Linux içindir, Windows desteklenmez.
- Giriş kilitleri, canlı mod önbelleği ve zamanlayıcı süreç içindedir; uygulama tek süreç olarak çalışmalıdır.
- Göç yalnızca yeni sütun ekler; silme/yeniden adlandırma elle yapılır.
