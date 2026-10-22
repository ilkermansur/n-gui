# menu eklentisi

## Ne yapar
Yan menüyü veriden üretir: bölümler (`Section`) ve gruplar (`MenuGroup`) veritabanında durur.
Admin, kod yazmadan bölüm ekleyebilir, yeniden adlandırabilir, gizleyebilir ve silebilir
(Ayarlar > Menü paneli). `/section/<key>` sayfası bir bölümün altındaki sayfaları kartlar halinde listeler.

## Servis (`kernel.get_service("menu")`)
- Bölümler: `list_sections`, `create_section(key, name_tr, name_en, icon)` (key yalnızca `[a-z0-9_]`),
  `update_section`, `delete_section` (sistem bölümü silinmez, grupları da silinir)
- Gruplar: `list_groups(section_key=None)`, `create_group`, `delete_group`
- `seed_defaults()`, `build_menu_nav_items(user)` (nav provider)

## Menü öğesi anahtarları
Bölüm `section:<key>`, grup `group:<id>` (ebeveyni `section:<section_key>`).
Başka eklentiler öğelerini `parent_key="section:<key>"` ile bir bölümün altına koyar.

## İzinler
`section.<key>.view` (her bölüm için), `settings.menu.manage`

## Hazır kayıtlar (seed)
`database.ready` olayında bir kez eklenir: dashboard, operation, report, log, settings.
`log` (`/log`) ve `settings` (`/settings`) sistem bölümüdür: silinemez, ama yeniden adlandırılabilir.

## Devre dışı bırakma
`config.toml` içindeki `[plugins] disabled` listesine `"menu"` ekleyin; yan menü boş kalır.
"auth" yoksa bölümler izin süzmesi olmadan gösterilir; "i18n" yoksa Türkçe ad kullanılır.
