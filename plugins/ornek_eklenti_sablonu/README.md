# ornek_eklenti_sablonu eklentisi

## Ne yapar
Hiçbir iş yapmaz; **yeni bir eklenti yazarken kopyalanacak şablondur**. Açılırsa sol menüye
"Örnek Eklenti" öğesini ve `/ornek-eklenti` sayfasını ekler. Sayfa iki istatistik kartı gösterir
(bulunan eklenti sayısı, kayıtlı izin sayısı).

## İçindekiler
- `plugin.py` - `Plugin` alt sınıfı (`setup` içinde izin + menü sağlayıcı kaydı) ve `@ui.page` sayfası
- `locales/tr.json`, `locales/en.json` - çeviriler (i18n eklentisi kendiliğinden okur)
- `__init__.py` - klasörü Python paketi yapar (loader `plugins.<ad>.plugin` olarak import eder)

## Yeni eklenti çıkarmak
1. Klasörü kopyalayın: `cp -r plugins/ornek_eklenti_sablonu plugins/yeni_eklenti`
2. `plugin.py` içinde `plugin_id` ve `name` değerlerini klasör adıyla (`yeni_eklenti`) aynı yapın;
   sınıf adını, `PAGE_PATH`, `VIEW_PERMISSION` ve NavItem `key` değerlerini değiştirin.
3. `locales/*.json` içindeki `ornek_eklenti.` önekli anahtarları kendi önekinizle değiştirin.
4. `config.toml` içindeki `[plugins] disabled` listesinde yeni eklentinin adı olmadığından emin olun.
5. Uygulamayı yeniden başlatın. Tek başına denemek için:
   `.venv/bin/python -m app.main --only auth,i18n,yeni_eklenti`

## İzinler
`ornek_eklenti.view` - sayfayı görme. `admin` rolü (`*`) otomatik görür; diğer rollere
Ayarlar > Roller ekranından verilir.

## Açma / kapatma
Bu şablon `config.toml` içinde `[plugins] disabled = ["ornek_eklenti_sablonu"]` ile **kapalı** gelir.
Denemek için listeden çıkarıp uygulamayı yeniden başlatın.
