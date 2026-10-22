# i18n eklentisi

## Ne yapar
Arayüz metinlerini Türkçe (`tr`) ve İngilizce (`en`) sunar. `"i18n"` servisini
(`Translator`) kaydeder; `app/core/text.py` içindeki `t("anahtar")` bu servisi kullanır.
Aktif dil her kullanıcının oturumunda (`app.storage.user["language"]`) tutulur;
header'daki dil düğmesi bunu değiştirir. Çeviri bulunamazsa önce `en`, o da yoksa
anahtarın kendisi gösterilir.

## Eklentiye çeviri dosyası ekleme
Eklenti klasörünüzde `locales` klasörü açın ve içine `tr.json` ile `en.json` koyun:

```
plugins/benim_eklentim/locales/tr.json   ->  {"benim.baslik": "Merhaba {name}"}
plugins/benim_eklentim/locales/en.json   ->  {"benim.baslik": "Hello {name}"}
```

Kodda `t("benim.baslik", name="Ali")` yazmanız yeterlidir. Dosyalar, tüm eklentiler
yüklendikten sonra (`plugins.loaded` olayı) otomatik okunur. Çekirdeğin kabuk metinleri
`app/core/locales/` içindedir.

## Devre dışı bırakma
`config.toml` içindeki `[plugins] disabled` listesine `"i18n"` ekleyin
(ya da uygulamayı `--only` ile i18n olmadan başlatın). Servis yoksa `t()` anahtarın
kendisini döndürür, uygulama yine çalışır; yalnızca metinler çevrilmez.
