# scheduler eklentisi

## Ne yapar
Yayınlanmış, etkin ve modu `scheduled` olan script'leri cron programına göre kendiliğinden
çalıştırır. Çalıştırma `scheduler` kullanıcısı adına, alanların varsayılan değerleriyle yapılır
(varsayılanı olmayan alan hiç verilmez). Hata veren iş loglanır, zamanlayıcıyı durdurmaz.

## Nasıl çalışır
- `BackgroundScheduler` NiceGUI açılışında başlar, kapanışında durur.
- İşler `database.ready` ve her `scripts.changed` olayında (yayın/etkinleştirme/devre dışı/kaldırma)
  yeniden eşitlenir. Dosyası silinmiş (sahipsiz) kayıtlar çalışmaz.
- İş anahtarı `script:<id>`; aynı iş aynı anda en fazla bir kez çalışır, kaçırılan çalışmalar
  birleştirilir ve en çok 60 sn gecikmeyle yine de çalıştırılır.
- Saat dilimi: sunucunun yerel saat dilimi.
- Geçersiz cron ifadesi loglanır ve o script atlanır.

## Cron biçimi (5 alan: dakika saat gün ay haftanın-günü)
- `*/5 * * * *` her 5 dakikada bir
- `0 8 * * *` her gün 08:00
- `30 17 * * 1-5` hafta içi 17:30
- `0 0 1 * *` her ayın ilk günü gece yarısı

## Devre dışı bırakma
- Tek script için: Ayarlar > Scriptler panelinden script'i devre dışı bırakın.
- Tüm eklenti için: `config.toml` içindeki `[plugins] disabled` listesine `"scheduler"` ekleyin.
