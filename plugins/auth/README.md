# auth eklentisi

## Ne yapar
Kullanıcı, rol, parola (bcrypt), oturum ve `/login` sayfasını sağlar. `"auth"` servisini
(`AuthService`) kaydeder; çekirdekteki `check_page_access` ve kabuk header'ı bu servisi kullanır.
Oturum bilgisi `app.storage.user["user_id"]` içindedir; kullanıcı her istekte DB'den okunur
(pasif/silinmiş kullanıcı hemen oturumunu kaybeder).

## Servis (`kernel.get_service("auth")`)
- Giriş: `authenticate`, `get_user_by_id`, `login_user`, `logout_current_user`, `current_user`
- Yetki: `has_permission(user, izin)` (`*` her şeyi kapsar)
- Yönetim: `list_users`, `create_user`, `update_user`, `change_password`,
  `list_roles`, `create_role`, `set_role_permissions`
- Kullanıcı sözlüğü: `id`, `username`, `full_name`, `roles`, `permissions`

## İzinler
`settings.users.manage`, `settings.roles.manage`

## Olaylar
`auth.login`, `auth.login_failed`, `auth.logout` (veri: `{"username": ...}`)

## Hazır kayıtlar (seed)
`database.ready` olayında bir kez oluşur; var olanlara dokunulmaz.
- `admin`: `*`
- `operator`: dashboard, operation, report bölümleri ve `log.view`
- `viewer`: dashboard ve report bölümleri
- `admin` kullanıcısı: parola `config.toml` içindeki `[auth] initial_admin_password`.
  Değer varsayılan `admin` ise logda uyarı yazılır.

## Devre dışı bırakma
`config.toml` içindeki `[plugins] disabled` listesine `"auth"` ekleyin. Servis yoksa
sayfalar girişsiz açılır (`check_page_access` servis yoksa izin verir).
