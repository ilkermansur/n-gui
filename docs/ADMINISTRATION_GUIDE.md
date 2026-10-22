# N-GUI Yönetim Rehberi (Administration Guide)

Bu rehber N-GUI'yi **kuran, işleten ve kullanan** kişiler içindir: sistem yöneticisi, uygulama
yöneticisi (admin rolü), operatörler ve izleyiciler. Kod bilgisi gerekmez. Uygulamanın iç yapısı
ve kod mantığı için [DESIGN_GUIDE.md](DESIGN_GUIDE.md), adım adım kod turu için
[NASIL_CALISIR.md](NASIL_CALISIR.md) dosyasına bakın.

İçindekiler:

1. [N-GUI nedir?](#1-n-gui-nedir)
2. [Kurulum ve çalıştırma](#2-kurulum-ve-çalıştırma)
3. [`config.toml` başvurusu](#3-configtoml-başvurusu)
4. [İlk giriş ve canlıya çıkış kontrol listesi](#4-ilk-giriş-ve-canlıya-çıkış-kontrol-listesi)
5. [Arayüzü tanıma](#5-arayüzü-tanıma)
6. [Kullanıcı yönetimi](#6-kullanıcı-yönetimi)
7. [Roller ve izinler](#7-roller-ve-izinler)
8. [Menü yönetimi: bölümler ve gruplar](#8-menü-yönetimi-bölümler-ve-gruplar)
9. [Script yönetimi](#9-script-yönetimi)
10. [Script çalıştırma (operatör gözüyle)](#10-script-çalıştırma-operatör-gözüyle)
11. [Log (işlem kayıtları)](#11-log-işlem-kayıtları)
12. [Sistem paneli](#12-sistem-paneli)
13. [Veritabanı](#13-veritabanı)
14. [Eklentileri açma ve kapatma](#14-eklentileri-açma-ve-kapatma)
15. [Yedekleme, geri yükleme ve güncelleme](#15-yedekleme-geri-yükleme-ve-güncelleme)
16. [Sorun giderme](#16-sorun-giderme)
17. [Bilinen sınırlar](#17-bilinen-sınırlar)

---

## 1. N-GUI nedir?

N-GUI, kurum içinde kullanılan bir **web kabuğudur**. Asıl işi şudur: Python script'lerinizi
tarayıcıdan çalıştırılabilir sayfalara çevirmek.

- Bir `.py` dosyası yüklersiniz. N-GUI dosyadaki `run(...)` fonksiyonunu ve açıklama bloğunu
  (docstring) okur, **formu kendisi üretir**.
- Script'in menüde nerede duracağını (bölüm/grup), kimlerin çalıştırabileceğini ve nasıl
  görüneceğini (form, canlı pano, zamanlanmış rapor) bir sihirbazdan seçersiniz.
- Script her çalıştırmada **ayrı bir süreçte ve zaman sınırıyla** çalışır. Sonuç ekranda görünür,
  kayıt Log'a düşer.
- Menü, kullanıcılar, roller ve izinler kod yazmadan **Ayarlar** ekranından yönetilir.
- Arayüz Türkçe/İngilizce, açık/koyu tema ve telefon ekranı destekler.

Sistemde üç hazır rol vardır:

| Rol | Kimdir | Ne görür |
|---|---|---|
| `admin` | Uygulama yöneticisi | Her şeyi. Ayarlar, script yükleme, kullanıcı yönetimi |
| `operator` | Script'leri çalıştıran ekip | Dashboard, Operasyon, Rapor bölümleri ve Log |
| `viewer` | Yalnızca izleyen | Dashboard ve Rapor bölümleri |

Rollerin ne görebileceği tamamen değiştirilebilir (bkz. [bölüm 7](#7-roller-ve-izinler)).

---

## 2. Kurulum ve çalıştırma

### Gereksinimler

- **Python 3.12** ya da üstü.
- **macOS ya da Linux.** Script'ler zaman aşımında süreç grubuyla birlikte sonlandırılır
  (`os.killpg`); bu Windows'ta çalışmaz.
- Tarayıcı: güncel Chrome, Edge, Firefox ya da Safari. Uygulama WebSocket kullanır.

### İlk kurulum

```bash
git clone <depo-adresi> n-gui
cd n-gui
python3 -m venv .venv
.venv/bin/pip install -e .
```

### Çalıştırma

```bash
.venv/bin/python -m app.main
```

Tarayıcıda `http://<sunucu>:8080` adresini açın (port `config.toml` içinden değişir).

Komut satırı seçenekleri:

| Seçenek | Ne yapar | Örnek |
|---|---|---|
| `--config <dosya>` | Başka bir ayar dosyası kullanır | `--config /etc/n-gui/prod.toml` |
| `--only a,b,c` | Yalnızca listelenen eklentileri yükler. Sorun ayıklarken ya da yeni eklenti denerken kullanılır | `--only auth,i18n,menu` |

### Servis olarak çalıştırma (Linux, systemd örneği)

Uygulama bir ön plan sürecidir. Sunucu açılınca kendiliğinden başlasın diye bir systemd birimi yazabilirsiniz:

```ini
# /etc/systemd/system/n-gui.service
[Unit]
Description=N-GUI
After=network.target

[Service]
User=ngui
WorkingDirectory=/opt/n-gui
ExecStart=/opt/n-gui/.venv/bin/python -m app.main --config /opt/n-gui/config.toml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now n-gui
journalctl -u n-gui -f      # logları izle
```

Önemli: `WorkingDirectory` proje klasörü olmalıdır. Varsayılan yollar (`data/app.db`, `scripts/`,
`data/uploads/`) bu klasöre göre çözülür.

### Ters vekil (reverse proxy) arkasında çalıştırma

nginx gibi bir vekil kullanıyorsanız **WebSocket yükseltmesine** izin verin, yoksa sayfa açılır
ama düğmeler çalışmaz:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 3600;
}
```

Uygulamayı bir alt yolda (`/ngui/` gibi) yayınlamak desteklenmez; kök yolda yayınlayın.

---

## 3. `config.toml` başvurusu

Ayar dosyası proje kökündedir. Dosya yoksa ya da bir değer eksikse aşağıdaki varsayılanlar
kullanılır. **Her değişiklik uygulama yeniden başlatılınca geçerli olur.**

| Bölüm | Anahtar | Varsayılan | Açıklama |
|---|---|---|---|
| `[app]` | `title` | `"N-GUI"` | Tarayıcı sekmesinde ve sol menünün üstünde görünen ad |
| `[app]` | `port` | `8080` | Web sunucusunun dinlediği port |
| `[app]` | `storage_secret` | `"degistir-beni"` | Oturum çerezini imzalayan gizli anahtar. **Canlıda uzun ve rastgele bir değer verin.** Değiştirirseniz herkesin oturumu kapanır |
| `[app]` | `default_language` | `"tr"` | Henüz dil seçmemiş kullanıcının arayüz dili (`tr` ya da `en`) |
| `[database]` | `url` | `"sqlite:///data/app.db"` | SQLAlchemy bağlantı adresi (bkz. [bölüm 13](#13-veritabanı)) |
| `[plugins]` | `disabled` | `[]` | Yüklenmeyecek eklentilerin klasör adları (bkz. [bölüm 14](#14-eklentileri-açma-ve-kapatma)) |
| `[scripts]` | `folder` | `"scripts"` | Script dosyalarının durduğu klasör. Yoksa açılışta oluşturulur |
| `[auth]` | `initial_admin_password` | `"admin"` | `admin` kullanıcısının **yalnızca ilk oluşturulurken** aldığı parola. Admin var olduktan sonra bu değeri değiştirmek parolayı değiştirmez |

Örnek canlı ayar dosyası:

```toml
[app]
title = "Operasyon Paneli"
port = 8080
storage_secret = "q3J8...en-az-32-karakter-rastgele-metin..."
default_language = "tr"

[database]
url = "sqlite:///data/app.db"

[plugins]
disabled = ["ornek_eklenti_sablonu"]

[scripts]
folder = "scripts"

[auth]
initial_admin_password = "IlkGiris!2026"
```

Rastgele bir `storage_secret` üretmek için:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Ayarlar > Veritabanı ekranı `[database] url` değerini bu dosyaya kendisi yazar (dosyadaki
yorumlar korunur). Diğer değerleri elle düzenlersiniz.

---

## 4. İlk giriş ve canlıya çıkış kontrol listesi

### İlk giriş

1. Uygulamayı başlatın. Konsolda `Varsayılan admin kullanıcısı oluşturuldu` satırını görürsünüz.
2. Tarayıcıda giriş ekranı açılır. Kullanıcı adı: `admin`, parola: `[auth] initial_admin_password`.
3. Giriş yapınca menünüzdeki ilk sayfaya yönlendirilirsiniz.

Parola varsayılan değerde (`admin`) ise uygulama her açılışta konsola şu uyarıyı yazar:
`Admin şifresi varsayılan değerde ("admin"); config.toml içindeki [auth] initial_admin_password değerini değiştirin.`

### Canlıya çıkmadan önce

- [ ] `[app] storage_secret` değerini rastgele, uzun bir metinle değiştirin.
- [ ] Admin parolasını değiştirin: **Ayarlar > Kullanıcılar** > `admin` satırını seçin > **Şifre sıfırla**.
- [ ] Her kişiye kendi kullanıcısını açın; `admin` hesabını ortak kullanmayın.
- [ ] Rollerin izinlerini gözden geçirin (bkz. [bölüm 7](#7-roller-ve-izinler)).
- [ ] `scripts/` klasöründeki örnek script'leri isterseniz silin ya da yayınlamayın.
- [ ] Uygulamayı yalnızca şirket ağından erişilebilir yapın. Dışarıya açacaksanız önüne
      HTTPS sağlayan bir ters vekil koyun.
- [ ] Yedekleme planı kurun (bkz. [bölüm 15](#15-yedekleme-geri-yükleme-ve-güncelleme)).
- [ ] Script'leri çalıştıran işletim sistemi kullanıcısının yetkilerini sınırlayın. Script'ler
      uygulamayla **aynı işletim sistemi kullanıcısı** adına çalışır.

---

## 5. Arayüzü tanıma

```
┌──────────────┬───────────────────────────────────────────────────────────┐
│ ▣ N-GUI      │ ☰  Sayfa başlığı        [ Ara ▾ ]   TR   ☾   (Y) Yönetici │
│              ├───────────────────────────────────────────────────────────┤
│ ▦ Dashboard ▾│                                                           │
│ 🔧 Operasyon ▴│   ┌───────────────── kart ─────────────────┐              │
│   📁 Ağ      ▴│   │                                        │              │
│     ▶ Ping   │   └────────────────────────────────────────┘              │
│ 📊 Rapor     ▾│                                                           │
│ 🧾 Log        │                                                           │
│ ⚙ Ayarlar    │                                                           │
└──────────────┴───────────────────────────────────────────────────────────┘
```

- **Sol menü:** Bölümler, gruplar ve script'ler. Altında sayfa olan bölüm ve gruplar
  katlanabilir. Açık sayfa vurgulanır. Menüde yalnızca sizin görme izniniz olan öğeler bulunur.
- **☰ düğmesi:** Sol menüyü açar/kapatır. Telefonda menü kapalı başlar, bu düğmeyle açılır.
- **Ara:** Menüdeki sayfalar arasında adıyla arama yapar; seçince o sayfaya gider.
  Telefon genişliğinde gizlenir.
- **TR / EN:** Arayüz dilini değiştirir. Seçim tarayıcı oturumunuzda saklanır.
- **☾ / ☀:** Koyu ve açık tema arasında geçiş yapar. Seçim saklanır.
- **Kullanıcı menüsü (avatar):** Tıklayınca **Çıkış** seçeneği çıkar.

Bir sayfaya izniniz yoksa "Bu sayfaya erişim izniniz yok" kartı görünür. Var olmayan bir adrese
giderseniz "Sayfa bulunamadı" kartı ve **Ana sayfaya dön** düğmesi görünür.

Ana sayfa (`/`), menünüzdeki ilk sayfaya yönlendirir. Menünüz boşsa "Henüz gösterilecek bir sayfa yok" mesajı görünür.

---

## 6. Kullanıcı yönetimi

**Ayarlar > Kullanıcılar** (izin: `settings.users.manage`). Tablodan bir satır seçip üstteki
düğmeleri kullanırsınız.

| İşlem | Nasıl | Notlar |
|---|---|---|
| Ekle | **Ekle** → kullanıcı adı, ad soyad, şifre, roller → **Kaydet** | Kullanıcı adı büyük/küçük harf duyarsızdır ve küçük harfe çevrilir. Aynı ad iki kez kullanılamaz |
| Düzenle | Satırı seç → **Düzenle** | Ad soyad, aktiflik ve roller değişir. Kullanıcı adı değiştirilemez |
| Şifre sıfırla | Satırı seç → **Şifre sıfırla** | Eski şifre gerekmez. Kullanıcıya yeni şifreyi güvenli bir yoldan iletin |
| Aktif / pasif | Satırı seç → **Aktif / pasif** | Pasif kullanıcı giriş yapamaz; **açık oturumu da bir sonraki sayfa açılışında kapanır** |

Kurallar:

- **Şifre** en az 4 karakter, en fazla 72 bayt olmalıdır (Türkçe harfler 2 bayt sayılır).
  Şifreler bcrypt ile özetlenerek saklanır; kimse düz halini göremez.
- **Kendi hesabınızı pasif yapamazsınız** (sistemin dışında kalmayasınız diye).
- **Kullanıcı silme yoktur.** Ayrılan kişiyi pasif yapın; geçmiş Log kayıtları onun adıyla kalır.
- Bir kullanıcının rolleri değişince yeni izinler **o kullanıcının bir sonraki sayfa açılışında**
  geçerli olur. Kendi rollerinizi değiştirirseniz sol menünüz hemen güncellenir.
- Bütün kullanıcı işlemleri Log'a `settings.changed` / `users` olarak yazılır. Şifreler asla Log'a yazılmaz.

---

## 7. Roller ve izinler

### Kavramlar

- **İzin**, bir şeyi açan metin anahtarıdır: `log.view`, `section.report.view` gibi.
- **Rol**, izinlerin bir listesidir. Kullanıcıya bir ya da birden çok rol verilir; kullanıcının
  izinleri, rollerinin izinlerinin birleşimidir.
- **`*` izni** her şeyi kapsar. Hazır `admin` rolünde bu izin vardır.

### Rol düzenleme

**Ayarlar > Roller** (izin: `settings.roles.manage`):

1. **Rol** listesinden bir rol seçin. Sistemdeki bütün izinler onay kutusu olarak, açıklamalarıyla listelenir.
2. Kutuları işaretleyin/kaldırın ve **Kaydet** deyin.
3. Yeni rol için **Rol ekle** → ad → **Kaydet**. Yeni rol boş izinle başlar.

`*` iznine sahip bir rol seçildiğinde bir uyarı görünür: bu rol, kutular işaretli olmasa da her
şeyi yapabilir. Kapalı bir eklentinin izni kutularda görünmez ama rolden silinmez; eklenti
yeniden açılınca izin geri gelir. Rol silme yoktur; kullanmadığınız rolü kimseye vermeyin.

### Tüm izinler

| İzin | Ne açar | Kaydeden eklenti |
|---|---|---|
| `section.<anahtar>.view` | Bölümün menüde görünmesi ve `/section/<anahtar>` sayfası. **Her bölüm için ayrı izin vardır** | `menu` |
| `log.view` | `/log` sayfası | `audit_log` |
| `settings.view` | `/settings` sayfasının kendisi. **Diğer bütün ayar izinleri bunu da gerektirir** | `settings_core` |
| `settings.users.manage` | Ayarlar > Kullanıcılar | `auth` |
| `settings.roles.manage` | Ayarlar > Roller | `auth` |
| `settings.menu.manage` | Ayarlar > Menü | `menu` |
| `settings.system.view` | Ayarlar > Sistem | `settings_core` |
| `settings.database.manage` | Ayarlar > Veritabanı | `settings_core` |
| `scripts.manage` | Ayarlar > Scriptler (yükleme, yayınlama, düzenleme, kaldırma) | `script_engine` |

Hazır rollerin izinleri:

| Rol | İzinler |
|---|---|
| `admin` | `*` |
| `operator` | `section.dashboard.view`, `section.operation.view`, `section.report.view`, `section.log.view`, `log.view` |
| `viewer` | `section.dashboard.view`, `section.report.view` |

Hazır roller yalnızca **ilk açılışta** oluşturulur; sonradan yaptığınız değişiklikler korunur.

### Sık kullanılan tarifler

**"Yalnızca kullanıcıları yönetebilen" bir yardımcı yönetici:**
yeni rol `kullanici_yoneticisi` → `settings.view` + `settings.users.manage`.

**"Script yükleyebilen ama kullanıcı yönetemeyen" bir geliştirici:**
yeni rol `script_yoneticisi` → `settings.view` + `scripts.manage` (+ isterseniz `log.view`, `section.log.view`).

**Yeni bölümü bir role göstermek:** yeni bölüm (ör. `urun_b`) oluşturulduğunda yalnızca admin
görür. Operatörlerin görmesi için `operator` rolüne `section.urun_b.view` iznini verin.

### Script'leri kim görür, kim çalıştırır?

Script'lerin yetkisi **izinle değil, script'e atanan rol listesiyle** belirlenir. İki kural birlikte geçerlidir:

1. **Çalıştırma kuralı:** Kullanıcının `admin` rolü (ya da `*` izni) varsa her script'i
   çalıştırabilir. Script'in rol listesi boşsa giriş yapmış herkes çalıştırabilir. Aksi halde
   kullanıcının rollerinden en az biri listede olmalıdır.
2. **Menü kuralı:** Script menüde, yerleştirildiği bölümün altında görünür. Kullanıcının o
   bölümü görme izni (`section.<anahtar>.view`) yoksa script menüde görünmez.

Yani bir operatörün "Ürün B" altındaki bir script'i menüde görmesi için hem script'in rol
listesinde `operator` olmalı (ya da liste boş olmalı), hem de `operator` rolünde
`section.urun_b.view` izni bulunmalıdır. Rolü uygun olan kullanıcı, bölümü göremese bile
script'in adresini (`/script/<kimlik>`) doğrudan açarak çalıştırabilir.

---

## 8. Menü yönetimi: bölümler ve gruplar

**Ayarlar > Menü** (izin: `settings.menu.manage`). Menü kodda değil veritabanında durur.

```
Bölüm (section)            ör. "Operasyon"   →  /section/operation
 ├── Grup (group)          ör. "Ağ"          (adresi yoktur, katlanır başlıktır)
 │    └── Script           ör. "Ping Testi"  →  /script/ping_testi
 └── Script                (doğrudan bölümün altında da durabilir)
```

### Bölümler

| Alan | Kural |
|---|---|
| Anahtar | Yalnızca küçük harf, rakam ve alt çizgi (`urun_b`). **Sonradan değiştirilemez**; izin adı (`section.urun_b.view`) ve adres (`/section/urun_b`) buna bağlıdır |
| Ad (TR) | Zorunlu |
| Ad (EN) | İsteğe bağlı. Boşsa İngilizce arayüzde de Türkçe ad görünür |
| İkon | [Material Icons](https://fonts.google.com/icons) adı: `inventory_2`, `dns`, `analytics`, `folder`... |
| Sıra | Küçük sayı önce gelir. Yeni bölüm en sona eklenir; sırayı **Düzenle** ile değiştirin |

İşlemler: tablodan bir bölüm seçin, sonra:

- **Ekle:** yeni bölüm. Oluşturulunca yalnızca admin görür (bkz. [bölüm 7](#7-roller-ve-izinler)).
- **Düzenle:** ad, ikon ve sıra değişir.
- **Gizle / Göster:** bölüm menüden kalkar ama silinmez. Altındaki script'ler de menüde görünmez.
- **Sil:** onay ister. Bölüm ve **grupları** silinir. Altındaki script'ler silinmez ama
  "atanmamış" duruma düşer ve menüden kalkar; Ayarlar > Scriptler'den yeni bir yere taşıyabilirsiniz.

**Sistem bölümleri:** `log` (Log sayfası) ve `settings` (Ayarlar sayfası) silinemez; adları ve
ikonları değiştirilebilir. Sayfasını sunan eklenti kapalıysa bu bölüm menüde görünmez.

Hazır bölümler (ilk açılışta oluşur): `dashboard`, `operation`, `report`, `log`, `settings`.

### Gruplar

Bölüm tablosundan bir bölüm seçin; alttaki **Gruplar** kartında o bölümün grupları listelenir.

- **Grup ekle:** Ad (TR) zorunlu, Ad (EN) isteğe bağlı.
- **Sil (çöp kutusu):** onay ister. Gruptaki script'ler "atanmamış" duruma düşer.
- Grup, script yayınlarken sihirbazdaki **Yeni grup** alanından da oluşturulabilir.

Menüdeki her değişiklik sizin ekranınızda hemen görünür. Diğer kullanıcılar değişikliği bir
sonraki sayfa açılışında görür. Bütün menü işlemleri Log'a `settings.changed` / `menu` olarak yazılır.

### Bölüm sayfası

`/section/<anahtar>` sayfası, bölümdeki grupları ve sayfaları kartlar halinde listeler.
Altında sayfa bulunan bir bölüm sol menüde katlanabilir başlık olarak görünür; bölüm sayfasına
o zaman arama kutusundan ya da adresten ulaşılır.

---

## 9. Script yönetimi

### Bir script'in yaşam döngüsü

```mermaid
stateDiagram-v2
    [*] --> Yayınlanmamış: .py yüklendi / klasöre bırakıldı
    Yayınlanmamış --> Hatalı: docstring/söz dizimi hatası
    Hatalı --> Yayınlanmamış: dosya düzeltildi + Yeniden tara
    Yayınlanmamış --> Yayında: Sihirbaz > Yayınla
    Yayında --> DevreDışı: anahtar düğmesi
    DevreDışı --> Yayında: anahtar düğmesi
    Yayında --> Atanmamış: bölümü/grubu silindi
    Atanmamış --> Yayında: Düzenle > yeni yer seç
    Yayında --> [*]: Kaldır (dosya da silinir)
    DevreDışı --> [*]: Kaldır
```

### Script yazmak

En basit script yalnızca bir `run` fonksiyonudur; N-GUI formu parametrelerden üretir:

```python
def run(host: str, count: int = 3):
    return {"Sunucu": host, "Paket": count}
```

Docstring'e `---` arasında bir YAML bloğu ekleyerek başlığı, etiketleri, seçenekleri ve
varsayılan yerleşimi tanımlayabilirsiniz:

```python
"""Bir sunucuya ping atar.
---
title: {tr: Ping Testi, en: Ping Test}
section: Operation
group: Ağ
mode: form
roles: [operator, admin]
timeout: 30
inputs:
  host: {type: str, label: {tr: Sunucu adresi, en: Host}, required: true, help: "Örnek: 8.8.8.8"}
  count: {type: int, label: {tr: Paket sayısı, en: Packet count}, default: 3, min: 1, max: 10}
---
"""
def run(host: str, count: int = 3):
    ...
```

Bütün anahtarlar, 11 alan tipi ve kurallar: [NASIL_CALISIR.md, bölüm 6](NASIL_CALISIR.md#6-script-docstring-referansı).
Örnekler: `scripts/ping_testi.py` (form), `scripts/sistem_durumu.py` (canlı), `scripts/gunluk_ozet.py` (zamanlanmış).

Script yazarken dikkat edilecekler:

- `run()` **JSON'a çevrilebilen** bir değer döndürmelidir. Nasıl göründüğü döndürdüğünüz değere bağlıdır:

  | Dönüş değeri | Ekranda |
  |---|---|
  | Değerleri tek değer (metin/sayı/bool) olan `dict` | Her anahtar için bir istatistik kartı. Anahtar kartın başlığıdır, okunur adlar kullanın (`"Paket kaybı"`) |
  | `dict` listesi | Tablo (sütunlar anahtarlardan) |
  | `str` | Kod bloğu |
  | Diğer (iç içe yapılar, liste) | Salt okunur JSON görünümü |

  `True`/`False` kartlarda "Evet"/"Hayır", `None` ise "-" olarak görünür.
- `print(...)` çıktıları sonucun altındaki katlanır **Çıktı** bölümünde görünür (en fazla 20.000 karakter).
- Hata göstermek için **istisna fırlatın** (`raise ValueError("...")`). Sonuç "Hatalı" olur ve
  traceback kırmızı **Hata** kartında görünür.
- Script **uygulamayla aynı Python ortamında** (`.venv`) çalışır. Script'in ihtiyaç duyduğu
  paketleri bu ortama kurun: `.venv/bin/pip install <paket>`.
- Script'in çalışma klasörü script'in kendi klasörüdür (`scripts/`).
- Uzun süren işler için docstring'de `timeout` verin (varsayılan 60 sn). Süre dolunca script
  ve başlattığı bütün alt süreçler sonlandırılır.
- Docstring'deki ilk paragraf sayfada başlığın altında görünür. Boş satırla paragraf ayırabilir,
  `` `kod` `` yazımı kullanabilirsiniz.

### Script yüklemek: sihirbaz

**Ayarlar > Scriptler > Yükle** (izin: `scripts.manage`).

**Adım 1 — Dosya.** İki yol vardır:

- `.py` dosyasını seçip yükleyin. Dosya `scripts/` klasörüne `<kimlik>.py` adıyla kaydedilir.
  Kimlik dosya adından üretilir: Türkçe harfler sadeleşir, küçük harfe çevrilir, boşluklar alt
  çizgi olur (`Ping Testi.py` → `ping_testi`). Aynı kimlikte dosya varsa **Aynı adlı script varsa üzerine yaz**
  kutusunu işaretlemeden yükleme reddedilir.
- Ya da dosyayı sunucuda doğrudan `scripts/` klasörüne kopyalayıp listeden seçin
  ("Yayınlanmamış dosya").

**Adım 2 — Önizleme.** Algılanan alanlar tablosu (ad, tip, etiket, zorunluluk, varsayılan, seçenekler)
ve formun canlı önizlemesi görünür. Burada formu kontrol edin. Dosyada hata varsa hata mesajı
görünür ve ilerleyemezsiniz.

**Adım 3 — Yerleşim.** Docstring'deki öneriler alanlara önceden doldurulur:

| Alan | Açıklama |
|---|---|
| Başlık (TR / EN) | Menüdeki ve sayfadaki ad. TR zorunlu |
| Bölüm | Script'in duracağı bölüm. Docstring öneri vermezse moda göre seçilir: form → Operasyon, canlı → Dashboard, zamanlanmış → Rapor |
| Grup | Bölüm içindeki grup ya da "(Grup yok)" |
| Yeni grup | Doluysa bu adla yeni bir grup oluşturulur ve script oraya konur |
| Görünüm modu | `Form`, `Canlı`, `Zamanlanmış` (aşağıda) |
| Roller | Çalıştırabilecek roller. **Boş bırakılırsa giriş yapmış herkes** çalıştırabilir; admin her zaman çalıştırır |
| Zaman aşımı (sn) | Bu sürede bitmeyen çalıştırma sonlandırılır |
| Yenileme aralığı (sn) | Yalnızca **Canlı** modda görünür |
| Zamanlama (cron) | Yalnızca **Zamanlanmış** modda görünür |

**Yayınla** deyince script menüye eklenir ve sayfası açılır.

### Görünüm modları

| Mod | Sayfa | Kim çalıştırır | Log'a ne yazılır |
|---|---|---|---|
| **Form** | Form → **Çalıştır** → sonuç kartı | Kullanıcı | Her çalıştırma |
| **Canlı** | Form yok. Sayfa açılınca alanların varsayılanlarıyla çalışır, sonra her *yenileme aralığı* saniyede bir tekrar çalışır | Sayfayı açık tutan her tarayıcı | Sayfa açılışındaki ilk çalıştırma ve **yalnızca başarısız** yenilemeler (Log dolmasın diye) |
| **Zamanlanmış** | Elle çalıştırma formu + **Geçmiş çalıştırmalar** tablosu (son 50). Satıra tıklayınca sonuç açılır | Zamanlayıcı (`scheduler` kullanıcısı adına) ve isteyen kullanıcı | Her çalıştırma |

Zamanlanmış çalışmalar alanların **varsayılan değerleriyle** yapılır; varsayılanı olmayan alan
hiç verilmez. Zorunlu ve varsayılansız alanı olan bir script zamanlayıcıda hata verir.

Cron biçimi 5 alandır: `dakika saat gün ay haftanın-günü`. Sunucunun yerel saat dilimi kullanılır.

| İfade | Anlamı |
|---|---|
| `*/5 * * * *` | Her 5 dakikada bir |
| `0 8 * * *` | Her gün 08:00 |
| `30 17 * * 1-5` | Hafta içi 17:30 |
| `0 0 1 * *` | Her ayın ilk günü gece yarısı |

Geçersiz cron ifadesi konsola loglanır ve o script zamanlanmaz. Aynı script'in bir önceki
zamanlanmış çalışması bitmeden yenisi başlamaz.

### Script listesi

**Ayarlar > Scriptler** klasördeki her dosyayı ve kaydı durumuyla gösterir:

| Durum | Anlamı | Ne yapılır |
|---|---|---|
| yayında | Menüde görünüyor ve çalıştırılabilir | — |
| devre dışı | Kaydı var ama menüde yok, çalıştırılamaz, zamanlanmaz | Anahtar düğmesiyle tekrar açın |
| hatalı | Dosya okunamadı (söz dizimi, YAML, `run()` yok, dosya silinmiş...). Hata mesajı satırda görünür | Dosyayı düzeltip **Yeniden tara** |
| atanmamış | Bölümü ya da grubu silinmiş; menüde görünmez | **Düzenle** ile yeni bir yer seçin |
| yayınlanmamış | Dosya klasörde ama hiç yayınlanmamış | **Düzenle** (kalem) ile sihirbazı açıp yayınlayın |

Satır düğmeleri:

- **✎ Düzenle:** sihirbazı yerleşim adımından açar. Dosyayı değiştirmeden başlığı, yeri, rolleri,
  modu ve zamanlamayı değiştirirsiniz.
- **Anahtar (etkin/devre dışı):** script'i silmeden menüden kaldırır ya da geri getirir.
- **🗑 Kaldır:** onay ister. Kaydı ve **diskteki dosyayı siler**. Çalışma geçmişi ve Log kayıtları kalır.

**Yeniden tara:** klasöre elle bıraktığınız ya da düzenlediğiniz dosyaları listeye getirir.

Script dosyasını yerinde güncellemek için iki yol vardır: sihirbazdan **üzerine yaz** kutusuyla
yeniden yükleyin ya da dosyayı klasörde değiştirin. Kayıt (yer, roller) korunur; sonraki
çalıştırma yeni dosyayı kullanır. Formdaki alanlar sayfa her açıldığında dosyadan yeniden okunur.

Bütün script işlemleri Log'a `scripts.changed` olarak yazılır (`published`, `enabled`, `disabled`, `removed`).

---

## 10. Script çalıştırma (operatör gözüyle)

1. Sol menüden script'i açın (ya da üstteki **Ara** kutusuna adını yazın).
2. Formu doldurun. Zorunlu alanlar boşsa ya da değer kurala uymuyorsa alanın altında kırmızı
   bir mesaj çıkar ve script çalıştırılmaz.
3. **Çalıştır** deyin. Script çalışırken düğme beklemede kalır.
4. Sonuç kartında:
   - **Başarılı / Hatalı** rozeti ve süre (ms),
   - sonuç (kartlar, tablo, metin ya da JSON),
   - **Çıktı** (script'in yazdırdıkları; tıklayınca açılır),
   - hata varsa kırmızı **Hata** kartı.

Dosya alanı olan formlarda yüklenen dosya sunucuda `data/uploads/` klasörüne kaydedilir ve
script'e dosyanın yolu verilir.

Bir script'i çalıştırma yetkiniz yoksa sayfası "Bu sayfaya erişim izniniz yok" mesajını gösterir.
Devre dışı bırakılmış ya da kaldırılmış bir script'in adresi "Script bulunamadı ya da devre dışı" gösterir.

---

## 11. Log (işlem kayıtları)

**Log** sayfası (izin: `log.view`) sistemde olanları en yeni önce gösterir.

| İşlem (`action`) | Ne zaman | Hedef | Detay |
|---|---|---|---|
| `auth.login` | Başarılı giriş | — | — |
| `auth.login_failed` | Hatalı giriş (durum: ERROR) | — | Kullanıcı sütununda denenen ad |
| `auth.logout` | Çıkış | — | — |
| `script.run` | Script çalıştırması | script kimliği | Hata metni (varsa), süre |
| `scripts.changed` | Yayın, etkinleştirme, devre dışı bırakma, kaldırma | script kimliği | `published` / `enabled` / `disabled` / `removed` |
| `settings.changed` | Kullanıcı, rol, menü ve veritabanı ayarı değişiklikleri | `users` / `roles` / `menu` / `database` | Kısa açıklama (şifre içermez) |

Süzme: **Durum** (Hepsi / OK / ERROR) ve **Ara** (kullanıcı, işlem, hedef ve detayda geçen metin).
**Yenile** düğmesi süzgeci uygular. Sayfa **en fazla 500 kaydı** gösterir; daha eskileri için süzgeci daraltın.

Zaman damgaları sunucunun yerel saatindedir.

**Saklama:** Log kayıtları kendiliğinden silinmez. Veritabanı büyürse eski kayıtları elle
temizleyebilirsiniz (önce yedek alın):

```bash
sqlite3 data/app.db "DELETE FROM audit_entries WHERE created_at < date('now', '-180 days');"
sqlite3 data/app.db "DELETE FROM script_runs  WHERE started_at < date('now', '-180 days');"
sqlite3 data/app.db "VACUUM;"
```

---

## 12. Sistem paneli

**Ayarlar > Sistem** (izin: `settings.system.view`):

- Python ve NiceGUI sürümleri, işletim sistemi, veritabanı adresi (şifresi gizlenmiş).
- **Eklentiler:** her eklentinin durumu.

  | Durum | Anlamı |
  |---|---|
  | `loaded` | Çalışıyor |
  | `disabled` | `config.toml` içinde kapatılmış |
  | `not selected` | Uygulama `--only` ile başlatılmış ve bu eklenti listede yok |
  | `failed: <hata>` | Yüklenirken hata verdi; uygulama onsuz çalışıyor. Ayrıntı konsol logunda |
  | `missing dependency: <ad>` | İhtiyaç duyduğu eklenti yüklenemedi |

- **Kurulu paketler:** Python ortamındaki paketler ve sürümleri. Script'lerin ihtiyaç duyduğu
  paketin kurulu olup olmadığını buradan kontrol edebilirsiniz.

---

## 13. Veritabanı

Varsayılan veritabanı tek bir SQLite dosyasıdır: `data/app.db`. Küçük ve orta ekipler için yeterlidir.

**Ayarlar > Veritabanı** (izin: `settings.database.manage`):

1. **Yeni veritabanı adresi** kutusuna adresi yazın.
2. **Bağlantıyı test et** ile deneyin.
3. **Kaydet** deyin. Adres `config.toml` dosyasına yazılır; **uygulamayı yeniden başlatınca** geçerli olur.

Adres örnekleri:

| Veritabanı | Adres | Ek paket |
|---|---|---|
| SQLite | `sqlite:///data/app.db` (göreli) ya da `sqlite:////var/lib/n-gui/app.db` (mutlak) | — |
| PostgreSQL | `postgresql+psycopg://kullanici:sifre@sunucu:5432/ngui` | `.venv/bin/pip install "psycopg[binary]"` |
| MS SQL Server | `mssql+pyodbc://kullanici:sifre@DSN_ADI` | `pyodbc` ve ODBC sürücüsü |

Önemli:

- **Veri taşınmaz.** Yeni veritabanı boş başlar: tablolar oluşturulur, hazır roller, bölümler ve
  `admin` kullanıcısı (`initial_admin_password` ile) yeniden eklenir. Kullanıcıları, menüyü ve
  script yayınlarını yeniden yapmanız gerekir.
- Ekranda ve Log'da adresin şifresi `***` ile gizlenir. `config.toml` dosyasında açık durur;
  dosyanın okuma izinlerini kısıtlayın.

---

## 14. Eklentileri açma ve kapatma

Her yetenek bir eklentidir (`plugins/` altındaki klasörler). Kapatmak için `config.toml`:

```toml
[plugins]
disabled = ["ornek_eklenti_sablonu", "scheduler"]
```

Uygulamayı yeniden başlatın; durum **Ayarlar > Sistem** panelinde görünür. Hatalı bir eklenti
uygulamayı çökertmez, yalnızca kendisi "failed" olur.

| Eklenti | Kapatınca ne olur | Ona bağlı olanlar |
|---|---|---|
| `i18n` | Metinler çevrilmez; ekranda çeviri anahtarları (`settings.title` gibi) görünür | — |
| `auth` | **Giriş ve yetki kontrolü kalkar; herkes her sayfayı açar.** Yalnızca deneme ortamında kapatın | `settings_core` |
| `menu` | Sol menü boş kalır, bölüm sayfaları açılmaz | `script_engine` |
| `forms` | Script formları çizilemez | `script_engine` |
| `audit_log` | Kayıt tutulmaz, Log menüden kalkar, `/log` "Sayfa bulunamadı" gösterir | — |
| `settings_core` | `/settings` açılmaz (kullanıcı, rol, sistem, veritabanı panelleri gider) | — |
| `script_engine` | Script'ler menüden kalkar, Scriptler paneli gider | `scheduler` |
| `scheduler` | Zamanlanmış script'ler kendiliğinden çalışmaz (elle çalıştırılabilir) | — |
| `ornek_eklenti_sablonu` | Varsayılan olarak kapalıdır; yeni eklenti için şablondur | — |

Bir eklentiyi kapatmak verilerini silmez; yeniden açınca her şey geri gelir.

Sorun ayıklarken bütün sistemi kapatmadan yalnızca belirli eklentilerle başlatabilirsiniz:

```bash
.venv/bin/python -m app.main --only auth,i18n,menu
```

---

## 15. Yedekleme, geri yükleme ve güncelleme

### Neyi yedeklemeli?

| Yol | İçerik | Önem |
|---|---|---|
| `data/app.db` (ya da harici veritabanı) | Kullanıcılar, roller, menü, script yayınları, çalışma geçmişi, Log | **Kritik** |
| `scripts/` (`[scripts] folder`) | Script dosyaları | **Kritik** |
| `config.toml` | Ayarlar (`storage_secret` dahil) | **Kritik** |
| `data/uploads/` | Formlardan yüklenen dosyalar | İsteğe bağlı |
| `.nicegui/` | Tarayıcı oturumları (dil, tema, giriş) | Gerekmez; silinirse herkes yeniden giriş yapar |

SQLite için tutarlı yedek (uygulama çalışırken de alınabilir):

```bash
sqlite3 data/app.db ".backup 'yedek/app-$(date +%F).db'"
tar czf yedek/scripts-$(date +%F).tgz scripts config.toml
```

**Geri yükleme:** uygulamayı durdurun, dosyaları yerine koyun, başlatın.

### Güncelleme

```bash
sudo systemctl stop n-gui        # ya da uygulamayı durdurun
# önce yedek alın
git pull
.venv/bin/pip install -e .
sudo systemctl start n-gui
```

Açılışta eksik tablolar kendiliğinden oluşturulur. **Var olan tablolara yeni sütun eklenmez**
(otomatik veritabanı göçü yoktur). Bir güncelleme var olan bir tabloyu değiştiriyorsa sürüm
notlarındaki elle yapılacak adımları izleyin.

---

## 16. Sorun giderme

| Belirti | Olası neden | Çözüm |
|---|---|---|
| Sayfa açılıyor ama düğmeler tepki vermiyor | Vekil WebSocket'e izin vermiyor | [Bölüm 2](#ters-vekil-reverse-proxy-arkasında-çalıştırma)'deki nginx ayarı |
| Herkesin oturumu kapandı | `storage_secret` değişti ya da `.nicegui/` silindi | Normaldir; yeniden giriş yapılır |
| Admin parolasını unuttum | — | Başka bir yetkili admin şifreyi sıfırlasın. Kimse yoksa: uygulamayı durdurun, `sqlite3 data/app.db "DELETE FROM auth_user_roles WHERE user_id=(SELECT id FROM auth_users WHERE username='admin'); DELETE FROM auth_users WHERE username='admin';"` komutuyla admin kaydını silin, `initial_admin_password` değerini ayarlayıp başlatın; admin yeniden oluşturulur |
| Yeni bölümü operatör görmüyor | Role `section.<anahtar>.view` verilmemiş | Ayarlar > Roller |
| Script menüde görünmüyor | Devre dışı / atanmamış / kullanıcının rolü listede yok / bölümü görme izni yok | Ayarlar > Scriptler'deki durum ve [bölüm 7](#scriptleri-kim-görür-kim-çalıştırır) |
| Script listede "hatalı" | Söz dizimi, YAML ya da `run()` eksik | Satırdaki mesajı okuyun, dosyayı düzeltip **Yeniden tara** |
| "Zaman aşımı: N saniye içinde bitmedi" | Script `timeout` süresini aştı | Sihirbazda zaman aşımını artırın |
| `ModuleNotFoundError` script hatası | Script'in paketi `.venv`'de yok | `.venv/bin/pip install <paket>` |
| Zamanlanmış script hiç çalışmıyor | `scheduler` kapalı, mod "Zamanlanmış" değil, cron boş/geçersiz, script devre dışı ya da atanmamış | Konsol logunda `Geçersiz cron ifadesi` satırını arayın |
| Ayarlar > Sistem'de `failed: ...` | Eklenti yüklenirken hata verdi | Konsol logundaki traceback'e bakın |
| Log'da `auth.login_failed` birikmesi | Hatalı/kaba kuvvet giriş denemeleri | Kaynağı ağ tarafında kısıtlayın; uygulamada hesap kilitleme yoktur |

Uygulamanın kendi logları standart çıktıya (konsol / `journalctl`) yazılır.

---

## 17. Bilinen sınırlar

- Windows sunucu desteklenmez (script sonlandırma `os.killpg` kullanır).
- Kullanıcı ve rol silme yoktur (pasif yapın / kullanmayın).
- Hesap kilitleme, parola karmaşıklık kuralı ve LDAP/AD girişi yoktur. Giriş `auth` eklentisinde
  olduğu için ileride bir LDAP eklentisiyle değiştirilebilir.
- Script'ler uygulamayla aynı işletim sistemi kullanıcısı ve Python ortamı ile çalışır; ayrı bir
  kum havuzu (sandbox) yoktur. Script yükleme yetkisini (`scripts.manage`) yalnızca güvendiğiniz kişilere verin.
- Log'da en fazla 500 kayıt gösterilir ve kayıtlar kendiliğinden silinmez.
- Otomatik veritabanı göçü yoktur.
- Menü değişiklikleri diğer kullanıcılara bir sonraki sayfa açılışında yansır.
