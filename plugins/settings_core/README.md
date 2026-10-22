# settings_core eklentisi

## Ne yapar
`/settings` sayfasını çizer ve kullanıcının izinli olduğu ayar panellerini sekmeler halinde gösterir.
Sayfa `settings.view` izni ister. Paneller `kernel.list_settings_panels()` ile toplanır; bu yüzden
başka eklentilerin panelleri (örn. menu eklentisinin "Menü" paneli) otomatik sekme olur.
Sekme sırası: users, roles, menu, system, database; bilinmeyenler kayıt sırasıyla sona eklenir.

## Paneller (anahtar, izin)
- `users` (`settings.users.manage`): kullanıcı tablosu, ekle/düzenle, şifre sıfırla, aktif/pasif
- `roles` (`settings.roles.manage`): rol seç, izinleri onay kutularıyla düzenle, rol ekle
- `system` (`settings.system.view`): Python/NiceGUI/platform kartları, eklenti durumları, paket listesi
- `database` (`settings.database.manage`): maskeli adres, bağlantıyı test et, `config.toml`'a kaydet (yeniden başlatma gerekir)

## Yardımcılar (`system_info.py`)
`mask_database_url(url)`, `collect_system_info(database_url)`, `list_installed_packages()`.

## Olaylar
Paneller `settings.changed` yayınlar: `{"username", "setting", "details"}` (`details` içinde parola bulunmaz).
Rol izinleri ve kullanıcı rolleri değişince açık sekmenin sol menüsü `refresh_navigation()` ile yenilenir.

## Bağımlılık ve devre dışı bırakma
`requires = ["auth"]`. `config.toml` içindeki `[plugins] disabled` listesine `"settings_core"` ekleyin; `/settings` açılmaz.
