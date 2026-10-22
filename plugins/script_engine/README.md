# script_engine eklentisi

## Ne yapar
`scripts/` klasöründeki (config.toml `[scripts] folder`) Python script'lerini menüde çalışan
sayfalara çevirir. Admin bir `.py` yükler, sihirbaz docstring'i ve `run()` imzasını okuyup formu
gösterir, admin menüdeki yerini seçip "Yayınla" der; script menüde görünür. "Kaldır" script'i
menüden ve diskten siler, çalışma geçmişi kalır.

Script **import edilmez**: metadata `ast` ile okunur (`parser.py`, sonuç dosyanın değişme zamanına
göre önbelleğe alınır), çalıştırma ayrı bir Python sürecinde zaman sınırıyla yapılır
(`runner.py`, `runner_shim.py`).

## Çalıştırma ortamı (`config.toml` `[scripts]`)
- `python`: script'leri çalıştıran yorumlayıcı (boşsa uygulamanınki). Script paketleri için ayrı sanal ortam önerilir.
- `env_passthrough`: script'e aktarılan ortam değişkenleri; listede olmayanlar geçmez.
- Dosya alanlarına yüklenen dosyalar çalıştırma bitince `forms.discard_uploaded_file` ile silinir.

## Script biçimi
```python
"""Açıklama.
---
title: {tr: Ping Testi, en: Ping Test}
section: Operation        # öneri; asıl yer sihirbazda seçilir
group: Ağ                 # öneri; yoksa "Yeni grup" olarak önerilir
mode: form                # form | live | scheduled
roles: [operator, admin]  # boşsa giriş yapmış herkes
timeout: 30
refresh: 15               # live modunda yenileme (sn)
schedule: "0 8 * * *"     # scheduled modunda cron
inputs:
  host: {type: str, label: Sunucu, required: true}
---
"""
def run(host: str, count: int = 3):
    return {"host": host}
```
Sonuç gösterimi: skaler değerli `dict` -> istatistik kartları, `dict` listesi -> tablo,
`str` -> kod bloğu, diğerleri -> salt okunur JSON. `print` çıktısı "Çıktı" bölümünde görünür.

## Servis (`kernel.get_service("scripts")`)
- Dosyalar: `scan_folder()` (`spec`, `entry`, `is_orphan`), `save_uploaded_file(file_name, content, overwrite)`
  (ad `<script_id>.py` olarak normalleştirilir), `parse(script_id)`
- Yayın: `publish(script_id, title_tr, title_en, section_key, group_id, mode, allowed_roles, timeout,
  refresh, schedule, username="")`, `set_enabled(script_id, enabled)`, `remove(script_id)`
- Okuma/yetki: `get_entry`, `list_entries`, `can_user_run(user, entry)`
- Çalıştırma: `execute(script_id, arguments, username) -> RunResult` (thread'den çağrılabilir),
  `run_live(script_id, username) -> LiveResult` (canlı mod; sonuç izleyiciler arasında paylaşılır,
  yenileme aralığı başına bir çalıştırma), `list_runs(script_id, limit=50)`, `last_run(script_id)`,
  `purge_runs_older_than(days)` (`[audit] retention_days`; açılışta ve günde bir)
- Uyarı: `find_roles_without_section_access(section_key, roles)` - script'i çalıştırabilen ama
  bölümü göremeyen roller (sihirbaz yerleşim adımında uyarı olarak gösterir)

## Sayfalar
- `/script/<script_id>`: giriş + `can_user_run` kontrolü. `form` modu form ve sonuç kartı,
  `live` modu her `refresh` saniyede kendini yeniler, `scheduled` modu elle çalıştırma ve geçmiş tablosu.
- Ayarlar > Scriptler: liste (yayında / devre dışı / hatalı / atanmamış / yayınlanmamış),
  "Yükle" (3 adımlı sihirbaz), "Yeniden tara", satırda Düzenle / Etkin-Devre dışı / Kaldır.

## Olaylar
- `script.finished` `{"username", "script_id", "success", "duration_ms", "error_text"}`
- `scripts.changed` `{"script_id", "change": "published"|"enabled"|"disabled"|"removed", "username"}`

## İzinler
`scripts.manage` (Scriptler paneli: yükleme, yayınlama, kaldırma). Script sayfaları rol listesine göre açılır.

## Bağımlılıklar
`requires = ["forms", "menu"]`; `auth` ve `i18n` varsa kullanılır.

## Devre dışı bırakma
`config.toml` içindeki `[plugins] disabled` listesine `"script_engine"` ekleyin; script'ler menüden kalkar.
