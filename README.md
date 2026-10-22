# N-GUI

Kurum içi kullanım için modüler bir NiceGUI web kabuğu. Python script'lerinizi yüklersiniz;
kabuk, script'in docstring'inden ve `run()` imzasından formu kendisi üretir ve script'i seçtiğiniz
menü bölümüne yerleştirir. Script her çalıştırmada ayrı bir süreçte, zaman sınırıyla çalışır.
Sonuç ekranda görünür, kayıt da Log'a düşer.

- **Çekirdek** (`app/core/`): küçük ve kararlıdır, eklentileri tanımaz.
- **Eklentiler** (`plugins/<ad>/`): her yetenek bir klasördedir (giriş/yetki, menü, formlar, log,
  ayarlar, script motoru, zamanlayıcı). Takılıp sökülebilir; hatalı bir eklenti uygulamayı çökertmez.
- **Menü veridir**: bölümler ve gruplar veritabanında tutulur ve Ayarlar'dan kod yazmadan değiştirilir.
- TR/EN arayüz, açık/koyu tema, rol tabanlı yetki (admin / operator / viewer).

Dokümanlar:

- **[docs/ADMINISTRATION_GUIDE.md](docs/ADMINISTRATION_GUIDE.md)**: kurulum, ayarlar, kullanıcı/rol/menü/script
  yönetimi, Log, yedekleme ve sorun giderme (yöneticiler ve operatörler için).
- **[docs/DESIGN_GUIDE.md](docs/DESIGN_GUIDE.md)**: mimari, eklenti modeli, veri modeli, yetki ve menü modeli,
  script motorunun tasarımı, görsel tasarım sistemi, kod kuralları ve genişletme tarifleri (geliştiriciler için).
- **[docs/NASIL_CALISIR.md](docs/NASIL_CALISIR.md)**: adım adım kod turu ve script docstring başvurusu.

## Kurulum

Python 3.12 gerekir.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Çalıştırma

```bash
.venv/bin/python -m app.main
```

Tarayıcıda `http://localhost:8080` adresini açın. Ayarlar `config.toml` dosyasındadır: başlık, port,
`storage_secret`, veritabanı adresi, kapalı eklentiler, script klasörü ve ilk admin parolası.

Seçenekler:

- `--config baska.toml`: başka bir ayar dosyası kullanır.
- `--only auth,i18n,menu`: yalnızca listelenen eklentileri yükler (bir eklentiyi tek başına denemek için).

## İlk giriş

- Kullanıcı adı: `admin`
- Parola: `config.toml` içindeki `[auth] initial_admin_password` değeri.

Admin kullanıcısı ilk açılışta bu parolayla oluşturulur. **Varsayılan değeri (`admin`) canlıya
çıkmadan önce mutlaka değiştirin.** İlk girişten sonra Ayarlar > Kullanıcılar > "Şifre sıfırla"
ile admin parolasını da değiştirin. Ayrıca `[app] storage_secret` değerini rastgele, uzun bir metinle değiştirin.

## Script ekleme (sihirbaz)

1. Script'inizi yazın: modül düzeyinde bir `run(...)` fonksiyonu olsun, docstring'e isteğe bağlı
   bir YAML bloğu ekleyin (biçim: `docs/NASIL_CALISIR.md`, bölüm 6; örnekler `scripts/` klasöründe).
2. Admin olarak **Ayarlar > Scriptler > Yükle** yolunu izleyin.
   - **Dosya**: `.py` dosyasını yükleyin ya da `scripts/` klasörüne bıraktığınız (yayınlanmamış) dosyayı seçin.
   - **Önizleme**: algılanan alanları ve formun önizlemesini kontrol edin.
   - **Yerleşim**: başlık, bölüm/grup, görünüm modu (`form` / `live` / `scheduled`) ve rolleri seçip **Yayınla** deyin.
3. Script menüde görünür. Aynı listeden **düzenleyebilir**, **devre dışı bırakabilir** ya da
   **kaldırabilirsiniz**. Kaldırma işlemi dosyayı da siler; çalışma geçmişi Log'da kalır.

Yeni bir menü bölümü (örneğin "Ürün B") için: **Ayarlar > Menü > Ekle**. Admin dışındaki rollerin
yeni bölümü görmesi için Ayarlar > Roller ekranından `section.<anahtar>.view` iznini verin.

## Eklenti kapatma

`config.toml` içinde eklentinin klasör adını `disabled` listesine ekleyin ve uygulamayı yeniden başlatın:

```toml
[plugins]
disabled = ["ornek_eklenti_sablonu", "scheduler"]
```

Eklentilerin durumu (loaded / disabled / failed / missing dependency) Ayarlar > Sistem panelinde görünür.
Her eklentinin klasöründe ne yaptığını ve kapatılınca ne olacağını anlatan bir `README.md` vardır.
Yeni eklenti yazmak için `plugins/ornek_eklenti_sablonu/` şablonunu kopyalayın
(adımlar: `docs/NASIL_CALISIR.md`, bölüm 5).

## Testler

```bash
.venv/bin/pytest
```

Testler bellek içi SQLite kullanır; `data/app.db` dosyanıza dokunmaz.
