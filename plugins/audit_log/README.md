# audit_log eklentisi

## Ne yapar
Sistemde olan işlemleri (giriş/çıkış, script çalıştırma, ayar değişikliği) olaylardan
dinleyip veritabanına yazar ve `/log` sayfasında durum ve metne göre süzülebilir tabloda gösterir.

## Servis (`kernel.get_service("audit")`)
- `write(username, action, target="", status="ok", duration_ms=0, details="")` - `details` 4000 karakterde kırpılır
- `search(status, text, limit=2000, date_from="", date_to="")` - en yeni kayıt önce; `status`
  `"ok"`/`"error"`/`None`; tarihler `"YYYY-MM-DD"`, iki gün de dahil
- `purge_older_than(days)` - verilen günden eski kayıtları siler (`0` = hiçbir şey silmez)

## Dinlediği olaylar
`auth.login`, `auth.login_failed` (status error, detay `reason`), `auth.logout`, `auth.password_changed`,
`script.finished` (action `script.run`),
`scripts.changed`, `settings.changed`. Eksik anahtarlar boş kabul edilir.
Handler'lar thread'den çağrılabildiği için her çağrı kendi DB oturumunu açar.

## Log sayfası
Durum, metin ve başlangıç/bitiş tarihi süzgeçleri; tablo 50'şer satırlık sayfalara bölünür.

## Saklama süresi
`config.toml` `[audit] retention_days` doluysa (varsayılan `0` = sonsuza dek) bu günden eski
kayıtlar açılışta (`database.ready`) ve günde bir (`app.timer`) silinir.

## İzinler
`log.view` (`/log` sayfası). Menüdeki "Log" bölümünü menu eklentisi hazır kayıt olarak ekler.

## Devre dışı bırakma
`config.toml` içindeki `[plugins] disabled` listesine `"audit_log"` ekleyin; kayıt tutulmaz, `/log` açılmaz.
