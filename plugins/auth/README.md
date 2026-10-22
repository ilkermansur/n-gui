# auth eklentisi

## Ne yapar
Kullanıcı, rol, parola (bcrypt), oturum ve `/login` sayfasını sağlar. `"auth"` servisini
(`AuthService`) kaydeder; çekirdekteki `check_page_access` ve kabuk header'ı bu servisi kullanır.
Oturum bilgisi `app.storage.user["user_id"]` içindedir; kullanıcı her istekte DB'den okunur
(pasif/silinmiş kullanıcı hemen oturumunu kaybeder).

## Servis (`kernel.get_service("auth")`)
- Giriş: `authenticate` (kilitliyse ya da hatalıysa `None`), `is_locked_out`, `get_user_by_id`,
  `login_user`, `logout_current_user`, `current_user`
- Yetki: `has_permission(user, izin)` (`*` her şeyi kapsar)
- Yönetim: `list_users`, `create_user`, `update_user`, `change_password` (admin sıfırlaması),
  `change_own_password(user_id, mevcut, yeni)`, `has_default_admin_password`,
  `list_roles`, `create_role`, `set_role_permissions`, `delete_role` (admin ve atanmış roller silinmez)
- Kullanıcı sözlüğü: `id`, `username`, `full_name`, `roles`, `permissions`

## Parola ve giriş kuralları (`config.toml` `[auth]`)
- `min_password_length` (varsayılan 8); en fazla 72 bayt. İlk admin oluşturulurken uygulanmaz.
- `max_login_attempts` (varsayılan 5, `0` = kapalı) üst üste hatada kullanıcı adı
  `lockout_minutes` (varsayılan 15) dakika kilitlenir. Kilit bellektedir; yeniden başlatınca sıfırlanır.

## Kullanıcı menüsü
Avatar menüsüne "Şifremi değiştir" eklenir (`kernel.add_user_menu_item`, `password_dialog.py`):
mevcut parola + iki kez yeni parola.

## İzinler
`settings.users.manage`, `settings.roles.manage`

## Olaylar
`auth.login`, `auth.login_failed` (kilitliyse ayrıca `"reason": "locked"`), `auth.logout`,
`auth.password_changed` (veri: `{"username": ...}`; parola asla olayda yoktur)

## Hazır kayıtlar (seed)
`database.ready` olayında bir kez oluşur; var olanlara dokunulmaz.
- `admin`: `*`
- `operator`: dashboard, operation, report bölümleri ve `log.view`
- `viewer`: dashboard ve report bölümleri
- `admin` kullanıcısı: parola `config.toml` içindeki `[auth] initial_admin_password`.
  Parola hâlâ `admin` ise main.py açılışta uyarı yazar; `[app] environment = "production"` iken uygulama açılmaz.

## Devre dışı bırakma
`config.toml` içindeki `[plugins] disabled` listesine `"auth"` ekleyin. Servis yoksa
sayfalar girişsiz açılır (`check_page_access` servis yoksa izin verir).
