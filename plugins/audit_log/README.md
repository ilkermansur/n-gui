# audit_log eklentisi

## Ne yapar
Sistemde olan işlemleri (giriş/çıkış, script çalıştırma, ayar değişikliği) olaylardan
dinleyip veritabanına yazar ve `/log` sayfasında durum ve metne göre süzülebilir tabloda gösterir.

## Servis (`kernel.get_service("audit")`)
- `write(username, action, target="", status="ok", duration_ms=0, details="")` - `details` 4000 karakterde kırpılır
- `search(status, text, limit=500)` - en yeni kayıt önce; `status` `"ok"`/`"error"`/`None`

## Dinlediği olaylar
`auth.login`, `auth.login_failed` (status error), `auth.logout`, `script.finished` (action `script.run`),
`scripts.changed`, `settings.changed`. Eksik anahtarlar boş kabul edilir.
Handler'lar thread'den çağrılabildiği için her çağrı kendi DB oturumunu açar.

## İzinler
`log.view` (`/log` sayfası). Menüdeki "Log" bölümünü menu eklentisi hazır kayıt olarak ekler.

## Devre dışı bırakma
`config.toml` içindeki `[plugins] disabled` listesine `"audit_log"` ekleyin; kayıt tutulmaz, `/log` açılmaz.
