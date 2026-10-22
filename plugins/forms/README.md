# forms eklentisi

## Ne yapar
Bir script'in girdi tariflerinden (`FieldSpec` listesi) NiceGUI formu çizer ve
gönderilen değerleri tiplere çevirip doğrular. Doğrulama UI'dan bağımsızdır.

## Servis (`kernel.get_service("forms")`)
- `build_form(fields)` - çağrıldığı yere iki sütunlu (telefonda tek sütun) bir form çizer, `FormHandle` döner
  - `handle.get_raw_values()` - widget'lardaki ham değerler
  - `handle.submit()` - `(değerler, hatalar)` döner; hatalar alanın altında gösterilir, eskiler silinir
- `convert_and_validate(fields, raw_values)` - `(değerler, hata_mesajları)`; mesajlar çevrilmiştir

## Tip - widget
`str` input, `text` textarea, `password` input(password), `int`/`float` number, `bool` switch,
`choice` select, `multichoice` select(multiple), `date`/`datetime` input (type=date / datetime-local),
`file` upload. Bilinmeyen tip `str` gibi çizilir ve işlenir.

## Kurallar
- Boş = `None`, `""` ya da `[]`. İsteğe bağlı boş alan `default` değerini alır; zorunlu boş alan hatadır.
- `bool`: `true/false/1/0/on/off` metinleri kabul edilir. `int` için `"5.5"` hatadır.
- `min_value`/`max_value` çeviriden sonra denetlenir.
- Dosyalar `data/uploads/<uuid>_<ad>` olarak kaydedilir; alanın değeri bu yoldur.
- Hata anahtarları: `forms.required`, `forms.not_number`, `forms.not_bool`, `forms.too_small`,
  `forms.too_large`, `forms.not_in_options`.

## Bağımlılık
Yok. `i18n` varsa etiketler dile göre seçilir, yoksa `label_tr` (o da boşsa alan adı) kullanılır.

## Devre dışı bırakma
`config.toml` içindeki `[plugins] disabled` listesine `"forms"` ekleyin.
