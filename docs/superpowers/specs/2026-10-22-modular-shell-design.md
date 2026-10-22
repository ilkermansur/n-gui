# NiceGUI Modüler Kabuk + Script Motoru — Plan

## Context
Kurum içi bir ekip (5-50 kişi) şirket ağı üzerinden kullanacak ve scriptler sunucuda çalışacak. Bu yüzden genel amaçlı bir web kabuğu gerekiyor. Kabukta RBAC, oturum, TR/EN dil desteği, form altyapısı ve Dashboard / Operation / Report / Log / Settings bölümleri bulunacak. Asıl hedef şu: sisteme Python scriptleri yüklenecek, her scriptin docstring'i girdilerini ve hangi bölümde görüneceğini tanımlayacak, kabuk da bunlardan otomatik form ve menü üretecek.

Ana tasarım ilkesi lego gibi çalışmak. Her yetenek ayrı bir klasördeki eklenti olacak; eklentiyi takıp sökmek çekirdeği bozmayacak, hatalı bir eklenti de uygulamayı çökertmeyecek.

Proje klasörü (`/Users/ilkermansur/Desktop/mac_studio/project/n_gui`) boş, Python 3.12 kurulu. Mevcut koda bağlanma ihtiyacı yok, her şey sıfırdan kurulacak.

**Kullanıcının netleştirdiği hedef:** GUI ile yalnızca bir kez uğraşılacak; sonrası no-code/low-code olacak. Akış şu: script'i yükle → form kendiliğinden oluşsun → menüdeki yerini seç → bitti. Script'i kaldırınca menüden de kalkar. Kabuk olabildiğince geniş bir kullanım alanına hitap etmeli. Dashboard/Operation/Report/Log/Settings yalnızca örnek; bölümler kod yazmadan artırılabilmeli. Bu yüzden **menü ve bölümler koddan değil veriden** gelir (aşağıdaki "Menü veridir" bölümüne bak).

**Varsayılan kararlar** (son sorulara cevap gelmediği için önerilen seçenekleri aldım; itiraz edersen değiştiririm):
- Giriş: lokal kullanıcılar (şifreler bcrypt ile hash'lenir). Auth bir eklenti olduğu için ileride LDAP/AD eklentisi takılabilir.
- Veritabanı: SQLAlchemy + SQLite ile başlanacak. Bağlantı URL'si değiştirilerek PostgreSQL veya MSSQL'e geçilebilir.
- Script çalıştırma: her çalıştırma ayrı bir process'te olacak; zaman aşımı uygulanacak, stdout/stderr yakalanacak.
- İlk tur: kabuk ve script motorunun çalışan ilk hali, 2-3 örnek scriptle birlikte.

## Kod yazım kuralları (teslim edilecek kod; okuyucu orta seviye Python bilen biri)
- **Basit olan kazanır.** Kısa ama karmaşık bir yol ile uzun ama düz bir yol arasında seçim varsa, uzun ve düz olan seçilir.
- **Kullanılmayacaklar:** lambda, iç içe fonksiyon (closure), kendi yazdığımız decorator ve wrapper, metaclass, karmaşık comprehension, `functools.partial`, gereksiz kalıtım zincirleri.
  - NiceGUI'nin kendi `@ui.page` dekoratörü kütüphanenin zorunlu kullanımı olduğu için kalır.
  - Buton tıklamaları için lambda yerine adı olan, ayrı tanımlanmış fonksiyonlar kullanılır.
- **Yetki kontrolü** decorator ile değil, açık bir satırla yapılır:
  `if not auth.has_permission(user, "script.run"): show_forbidden(); return`
- **Ayarlar** pydantic-settings yerine standart kütüphanedeki `tomllib` ile okunur; sonuç sade bir dataclass'a aktarılır.
- **Yorumlar Türkçe ve bol olur:**
  - Her dosyanın başında bir açıklama bloğu bulunur: bu dosya ne işe yarar, kim kullanır, nereye bağlanır.
  - Her fonksiyonun Türkçe bir docstring'i olur: ne yapar, parametreler, dönüş değeri.
  - Bariz olmayan her adımın üstünde "neden böyle yapıyoruz" açıklaması yer alır.
- **Dosya ve fonksiyon boyutu:** dosyalar küçük ve tek amaçlı tutulur; fonksiyonlar mümkünse ekrana sığacak uzunlukta olur.
- **İsimlendirme:** değişken ve fonksiyon adları İngilizce ama açıklayıcıdır (`selected_section`, `build_form_for_script`); kısaltma kullanılmaz.
- **Tip ipuçları:** basit tip ipuçları kullanılır (`str`, `list[str]`, `dict`). İleri seviye typing (Protocol, Generic, TypeVar) kullanılmaz.
- **Rehber dokümanlar:** her eklenti klasöründe Türkçe kısa bir `README.md` bulunur: ne yapar, nasıl kapatılır. Ayrıca kök dizinde `docs/NASIL_CALISIR.md` olur: uygulama açılınca sırasıyla ne olur, bir isteğin yolculuğu, yeni eklenti nasıl yazılır.
- **Onaydan sonra:** bu kurallar ileride de geçerli olsun diye proje hafızasına kaydedilir.

## Görsel dil (TailAdmin benzeri: temiz, modern)
- **Yerleşim:**
  - Solda beyaz bir sidebar: logo, ikonlu menü öğeleri, gruplar katlanabilir, aktif öğe vurgulanır.
  - Üstte ince bir header: sayfa başlığı, arama, dil seçimi (TR/EN), açık/koyu tema düğmesi, kullanıcı avatarı ve menüsü.
  - İçerik alanı açık gri (`#F1F5F9`) zemin üzerinde, beyaz ve yuvarlak köşeli (`rounded-xl`), hafif gölgeli ve ince kenarlıklı kartlardan oluşur.
- **Renk ve yazı:**
  - Ana renk tek bir mavi (`#3C50E0`, TailAdmin'in birincil rengi); durum renkleri yeşil, sarı ve kırmızı.
  - Font olarak Inter (Google Fonts) kullanılır; başlıklar yarı kalın, yazılar koyu gri.
- **Koyu tema:** NiceGUI `ui.dark_mode` ile açılır; kullanıcının seçimi oturumda saklanır.
- **Bileşenler:**
  - Dashboard için istatistik kartları: büyük sayı, küçük etiket, artış/azalış rozeti.
  - Tablolar sade olur: zebra çizgisi yok, satır üzerine gelince hafif vurgu.
  - Formlar `outlined` girişlerden oluşur ve kart içinde iki sütunlu düzende yer alır.
  - Durum rozetleri renkli ve yuvarlaktır (pill).
- **Teknik uygulama:**
  - Tüm stil tek bir yerde toplanır: `app/core/theme.py`. Renkler, gölgeler ve köşe değerleri burada değişken olarak durur, yani görünümü değiştirmek tek dosyayı düzenlemek demektir.
  - Bileşenler NiceGUI'nin hazır Tailwind sınıflarıyla (`.classes(...)`) stillendirilir.
  - Tekrar eden kart ve rozetler `app/core/widgets.py` içindeki basit fonksiyonlarla üretilir (`stat_card(title, value)`, `status_badge(text, color)`); eklentiler de bu fonksiyonları kullanır, böylece her sayfa aynı görünür.

## Mimari: Çekirdek + Eklentiler

```
n_gui/
  app/
    main.py            # giriş noktası: Kernel kur → eklentileri yükle → ui.run(storage_secret=...)
    core/              # ÇEKİRDEK: küçük, kararlı, hiçbir eklentiyi import etmez
      kernel.py        # Kernel: registry (nav, sayfalar, servisler, izinler, ayar panelleri) + event bus
      plugin.py        # Plugin sözleşmesi: id, name, version, requires[], setup(kernel), teardown()
      loader.py        # plugins/* keşfi, config'e göre aç/kapat, bağımlılık sırası, hata izolasyonu
      events.py        # basit pub/sub (ör. "script.finished", "auth.login_failed")
      config.py        # config.toml'u tomllib ile okur, sade bir dataclass'a koyar
      db.py            # SQLAlchemy engine/session; eklentiler kendi modellerini kaydeder
      layout.py        # kabuk çerçevesi: header, registry'den üretilen sol menü, dil ve kullanıcı menüsü
  plugins/             # her klasör bağımsız bir lego parçası
    i18n/              # t("key"), locales/tr.json, en.json; her eklenti kendi locales/ klasörünü getirir
    auth/              # login sayfası, User/Role/Permission modelleri, has_permission(), oturum
    menu/              # DB'deki bölüm ve grup ağacından menüyü üretir + Settings'te menü editörü
    forms/             # alan şemasından NiceGUI formu üreten builder (+ doğrulama)
    audit_log/         # event'leri DB'ye yazar, Log sayfası (filtre: kullanıcı, durum, tarih)
    settings_core/     # kullanıcı/rol yönetimi, sistem bilgisi (Python sürümü, paketler), DB bağlantısı
    script_engine/     # docstring parser, script registry, subprocess runner, bölüm sayfalarına katkı
    scheduler/         # APScheduler; periyodik rapor scriptleri
  scripts/             # kullanıcı scriptleri buraya bırakılır (veya UI'dan yüklenir)
  config.toml
  tests/
```

### Takıp sökme nasıl çalışır
- Bir eklenti, `plugin.py` dosyasında `Plugin` sınıfı olan bir klasördür. `setup(kernel)` içinde menü öğesi, sayfa, izin, ayar paneli ve event dinleyicisi kaydeder. Çekirdeğin bildiği tek şey bu sözleşmedir.
- `config.toml` içindeki `[plugins] disabled = ["scheduler"]` satırı bir eklentiyi söker. Klasörü silmek ya da yeni bir klasör eklemek de yeterlidir.
- Yeni bir iş `plugins/yeni_ozellik/` altında geliştirilir. Sistem tamamen kapalıyken bile tek başına denenebilir: `python -m app.main --only auth,i18n,yeni_ozellik`.
- Loader her eklentinin `setup` çağrısını try/except ile sarar. Hata veren eklenti "failed" olarak işaretlenir ve Settings'te görünür; uygulama çalışmaya devam eder. Bağımlılığı eksik olan eklenti yüklenmez.
- Eklentiler birbirini import etmez. Birbirleriyle `kernel.services["forms"]` ve event bus üzerinden konuşurlar. Bu sayede biri değiştiğinde diğerleri kırılmaz.

### RBAC ve oturum
- Oturum: NiceGUI `app.storage.user` (imzalı cookie) + bir middleware. Giriş yapmamış kullanıcı `/login` sayfasına yönlendirilir.
- İzinler metin anahtarlarıdır: `section.operation.view`, `script.<id>.run`, `settings.users.manage`. Eklentiler kendi izinlerini kaydeder.
- Hazır roller: `admin`, `operator`, `viewer`. Rol ile izin eşlemesi Settings'ten yönetilir. Menü yalnızca kullanıcının yetkili olduğu öğeleri gösterir.

### i18n
- `t("key", **kw)` fonksiyonu kullanıcının dilini (`app.storage.user["lang"]`) okur. Anahtar o dilde yoksa EN, EN'de de yoksa anahtarın kendisi döner.
- Her eklentinin `locales/*.json` dosyaları otomatik birleştirilir. Scriptler etiketlerini docstring'de `label: {tr: ..., en: ...}` şeklinde verebilir.

### Menü veridir (no-code)
- Bölümler (Section) ve gruplar (Group) DB tablolarında tutulur: ad (TR/EN), ikon, sıra, üst öğe, görebilecek roller. İlk kurulumda Dashboard, Operation, Report, Log ve Settings tohum (seed) olarak eklenir; admin bunları yeniden adlandırabilir, gizleyebilir ve yeni bölüm ekleyebilir (ör. "Ağ", "Ürün B"). Bunun için kod yazmak gerekmez.
- Log ve Settings sistem bölümleridir: içerikleri eklentilerden gelir, silinemez ama yeniden adlandırılabilir veya taşınabilir.
- Bir script herhangi bir bölüme veya gruba yerleşebilir. Script'in nasıl görüneceği bölüme bağlı değildir; script'in **görünüm modu** belirler:
  - `form`: form, ardından sonuç
  - `live`: otomatik yenilenen kart veya tablo
  - `scheduled`: zamanlanmış çalışma + geçmiş çıktılar listesi

### Yükleme sihirbazı (asıl kullanıcı deneyimi)
1. Settings → Scripts → "Yükle" ile `.py` dosyası seçilir (veya dosya `scripts/` klasörüne bırakılır).
2. Sistem docstring'i ve `run()` imzasını okur. Algılanan girdileri ve formun canlı önizlemesini gösterir.
3. Admin şu bilgileri seçer: başlık, bölüm/grup (açılır menüden ya da "yeni grup"), görünüm modu, roller, zamanlama. Docstring'de bu bilgiler varsa ön-doldurulur.
4. "Yayınla" denince script menüde görünür. Script listesinde her satırda şu aksiyonlar bulunur: Taşı / Devre dışı bırak / Kaldır. "Kaldır" script'i menüden ve diskten siler (çalışma geçmişi log'da kalır).
- Script'te hiç docstring olmasa bile `run()` fonksiyonunun parametrelerinden (tip ipuçları ve varsayılan değerler) form üretilir. Docstring yalnızca zenginleştirir: etiket, seçenekler, doğrulama.

### Script motoru (asıl hedef)
Scriptin docstring'inde `---` ile ayrılmış bir YAML bloğu bulunur. Script **import edilmez**; metadata `ast` ile okunur, bu yüzden hatalı bir script yükleme sırasında uygulamayı etkilemez.

```python
"""Cihazdaki servisi yeniden başlatır.
---
title: {tr: Servis Yeniden Başlat, en: Restart Service}
section: Operation          # opsiyonel öneri; asıl yer sihirbazda seçilir
group: Ürün A               # opsiyonel öneri
mode: form                  # form | live | scheduled
roles: [operator, admin]
timeout: 60
refresh: 30                 # dashboard için saniye
schedule: "0 8 * * 1"       # report için opsiyonel cron
inputs:
  host: {type: str, label: Sunucu, required: true}
  port: {type: int, default: 22, min: 1, max: 65535}
  mode: {type: choice, options: [soft, hard]}
  start: {type: date}
---
"""
def run(host: str, port: int = 22, mode: str = "soft", start=None):
    return {"status": "ok"}      # dict/list → tablo/kart, str → metin
```

- **Desteklenen tipler:** str, text, int, float, bool, choice, multichoice, date, datetime, file, password.
- **Akış:** parser bir `ScriptSpec` (pydantic) üretir. Script'in menüdeki yeri ve ayarları DB'deki `ScriptEntry` kaydında tutulur; sihirbaz bu kaydı yazar. Menü, `ScriptEntry` kayıtlarından üretilir. `forms` servisi formu üretir. Runner, `python -I runner_shim.py <script> <args.json>` komutunu subprocess olarak çalıştırır; sonuç JSON olarak döner ve `script.finished` event'i yayınlanır. `audit_log` bu event'i kaydeder.
- **Bölümlere göre davranış:**
  - Dashboard: kartlar `refresh` aralığıyla kendini yeniler.
  - Operation: form, ardından sonuç.
  - Report: form ile anlık çalıştırma, ya da `schedule` varsa scheduler'ın ürettiği ve geçmiş çıktıların listelendiği sayfa.
- **Yükleme:** Settings'ten `.py` yüklemek (yalnızca admin) veya dosyayı `scripts/` klasörüne bırakıp "Yeniden tara" demek. Parse hatası olan script, hata mesajıyla birlikte listede görünür.

## Uygulama sırası
1. İskelet: `pyproject.toml` (nicegui, sqlalchemy, pydantic, pyyaml, bcrypt, apscheduler, pytest), `core/` ve loader + testleri (devre dışı eklenti, bozuk eklenti, bağımlılık sırası).
2. `i18n` + `auth` (login, seed admin, RBAC, middleware) + `layout`.
3. `menu` (DB'den gelen bölümler + menü editörü) + `audit_log` + `settings_core`.
4. `forms` + `script_engine` (parser, runner, yükleme sihirbazı, script listesi) + 3 örnek script (form, live, scheduled).
5. `scheduler` (periyodik raporlar).
6. Onaydan sonraki ilk adım: bu tasarımı `docs/superpowers/specs/2026-10-22-modular-shell-design.md` dosyasına yazmak, `git init` yapmak ve uygulama planını çıkarmak.

## Doğrulama
- `pytest`: loader izolasyonu, docstring parser (geçerli/bozuk YAML, eksik alanlar), RBAC izin kontrolleri, runner (başarı, exception, timeout).
- Uygulamayı uygulama içi tarayıcıda (`preview_start`) açıp şu senaryoyu uçtan uca deneme: admin ile giriş → dil değiştirme → operator kullanıcısı açma → operator ile girişte Settings'in görünmediğini kontrol etme → Settings'ten yeni bir bölüm ("Ürün B") oluşturma → sihirbazla bir script yükleyip bu bölüme yerleştirme → formdan çalıştırma → Log'da kaydı görme → script'i kaldırıp menüden kalktığını görme → bir eklentiyi config'te kapatıp menüden kaybolduğunu ve uygulamanın çalıştığını doğrulama.
