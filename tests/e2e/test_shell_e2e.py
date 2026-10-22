"""test_shell_e2e.py - kabuğun uçtan uca senaryoları (gerçek tarayıcı, gerçek uygulama).

Kim kullanır: pytest, yalnızca NGUI_E2E=1 ile (bkz. tests/conftest.py).
Nasıl bağlanır: app_server fixture'ı geçici veritabanıyla uygulamayı başlatır; testler
Playwright ile arayüzü kullanır. Testler dosyadaki sırayla çalışır ve aynı uygulamayı
paylaşır: ilk test admin parolasını değiştirir, sonrakiler yeni parolayla girer.
Arayüz Türkçedir (varsayılan dil), bu yüzden düğmeler Türkçe adlarıyla bulunur.
"""

import subprocess

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import ADMIN_PASSWORD, find_free_port, start_app, write_config

pytestmark = pytest.mark.e2e

# İlk testte admin'in yeni parolası; sonraki testler bununla girer.
NEW_ADMIN_PASSWORD = "yeni-parola-456"

SAMPLE_SCRIPT = '''"""İki sayıyı toplar.
---
title: {tr: Toplama Testi, en: Sum Test}
mode: form
inputs:
  a: {type: int, label: {tr: Birinci sayı, en: First}, required: true}
  b: {type: int, label: {tr: İkinci sayı, en: Second}, default: 2}
---
"""


def run(a: int, b: int = 2):
    return {"Toplam": a + b}
'''


def is_not_login_url(url: str) -> bool:
    """Adres giriş sayfası değilse True (giriş sonrası yönlendirmeyi beklemek için)."""
    return "/login" not in url


def login(page, base_url: str, username: str, password: str) -> None:
    """Giriş sayfasından giriş yapar ve kabuğun açılmasını bekler."""
    page.goto(base_url + "/login")
    page.get_by_label("Kullanıcı adı").fill(username)
    page.get_by_label("Şifre").fill(password)
    page.get_by_role("button", name="Giriş").click()
    page.wait_for_url(is_not_login_url)


def menu_links(page) -> list[str]:
    """Sol menüdeki bağlantıların adreslerini döndürür."""
    return page.locator(".q-drawer a").evaluate_all("links => links.map(link => link.getAttribute('href'))")


def open_settings_tab(page, base_url: str, tab_name: str) -> None:
    """Ayarlar sayfasını açar ve verilen sekmeye geçer."""
    page.goto(base_url + "/settings")
    page.get_by_role("tab", name=tab_name).click()


def test_admin_changes_own_password(page, app_server):
    """Admin ilk parolayla girer, kullanıcı menüsünden parolasını değiştirir ve yeni parolayla girer."""
    base_url = app_server["url"]
    login(page, base_url, "admin", ADMIN_PASSWORD)
    page.locator(".q-header .q-avatar").click()
    page.get_by_text("Şifremi değiştir").click()
    dialog = page.locator(".q-dialog")
    dialog.get_by_label("Mevcut şifre").fill(ADMIN_PASSWORD)
    dialog.get_by_label("Yeni şifre", exact=True).fill(NEW_ADMIN_PASSWORD)
    dialog.get_by_label("Yeni şifre (tekrar)").fill(NEW_ADMIN_PASSWORD)
    dialog.get_by_role("button", name="Kaydet").click()
    expect(page.get_by_text("Şifreniz değiştirildi.")).to_be_visible()

    page.context.clear_cookies()
    login(page, base_url, "admin", NEW_ADMIN_PASSWORD)
    expect(page.locator(".q-header")).to_be_visible()


def test_operator_does_not_see_settings(page, app_server):
    """Admin bir operatör açar; operatörün menüsünde Ayarlar yoktur ve sayfa yetki hatası verir."""
    base_url = app_server["url"]
    login(page, base_url, "admin", NEW_ADMIN_PASSWORD)
    open_settings_tab(page, base_url, "Kullanıcılar")
    page.get_by_role("button", name="Ekle").first.click()
    dialog = page.locator(".q-dialog")
    dialog.get_by_label("Kullanıcı adı").fill("op1")
    dialog.get_by_label("Ad soyad").fill("Operatör Bir")
    dialog.get_by_label("Şifre").fill("operator-123")
    dialog.get_by_label("Roller").click()
    page.locator(".q-menu").get_by_text("operator", exact=True).click()
    page.keyboard.press("Escape")
    dialog.get_by_role("button", name="Kaydet").click()
    expect(page.locator("table")).to_contain_text("op1")

    page.context.clear_cookies()
    login(page, base_url, "op1", "operator-123")
    assert "/settings" not in menu_links(page)
    page.goto(base_url + "/settings")
    expect(page.get_by_text("Bu sayfaya erişim izniniz yok.").first).to_be_visible()


def test_script_lifecycle(page, app_server):
    """Bölüm aç → script yükle ve yayınla → çalıştır → Log'da gör → kaldır ve menüden kalksın."""
    base_url = app_server["url"]
    script_path = app_server["folder"] / "toplama_testi.py"
    script_path.write_text(SAMPLE_SCRIPT, encoding="utf-8")
    login(page, base_url, "admin", NEW_ADMIN_PASSWORD)

    open_settings_tab(page, base_url, "Menü")
    page.locator(".q-tab-panel:visible").get_by_role("button", name="Ekle").first.click()
    dialog = page.locator(".q-dialog")
    dialog.get_by_label("Anahtar").fill("urun_b")
    dialog.get_by_label("Ad (TR)").fill("Ürün B")
    dialog.get_by_label("Ad (EN)").fill("Product B")
    dialog.get_by_role("button", name="Kaydet").click()
    expect(page.locator(".q-drawer")).to_contain_text("Ürün B")

    page.get_by_role("tab", name="Scriptler").click()
    page.locator(".q-tab-panel:visible").get_by_role("button", name="Yükle").first.click()
    dialog = page.locator(".q-dialog")
    dialog.locator("input[type=file]").set_input_files(str(script_path))
    dialog.get_by_role("button", name="İleri").first.click()
    dialog.get_by_label("Bölüm").click()
    page.locator(".q-menu").get_by_text("Ürün B").click()
    dialog.get_by_role("button", name="Yayınla").click()
    page.wait_for_url("**/script/toplama_testi")
    assert "/script/toplama_testi" in menu_links(page)

    page.get_by_role("button", name="Çalıştır").click()
    expect(page.get_by_text("Birinci sayı zorunludur")).to_be_visible()
    page.get_by_label("Birinci sayı").fill("40")
    page.get_by_role("button", name="Çalıştır").click()
    expect(page.get_by_text("Başarılı")).to_be_visible()
    expect(page.locator(".q-page")).to_contain_text("42")

    page.goto(base_url + "/log")
    expect(page.locator("tbody")).to_contain_text("script.run")

    open_settings_tab(page, base_url, "Scriptler")
    row = page.locator("tr", has_text="toplama_testi.py")
    row.get_by_role("button").last.click()
    page.locator(".q-dialog").get_by_role("button", name="Kaldır").click()
    expect(page.get_by_text("Script kaldırıldı.")).to_be_visible()
    # Neden: menü sayfa yenilenmeden güncellenmeli (refresh_navigation).
    assert "/script/toplama_testi" not in menu_links(page)


def test_login_lockout(page, app_server):
    """Üst üste 3 hatalı denemeden sonra doğru parola da kabul edilmez ve kilit mesajı görünür."""
    base_url = app_server["url"]
    page.goto(base_url + "/login")
    for attempt in range(3):
        page.get_by_label("Kullanıcı adı").fill("op1")
        page.get_by_label("Şifre").fill("yanlis-parola")
        page.get_by_role("button", name="Giriş").click()
    page.get_by_label("Şifre").fill("operator-123")
    page.get_by_role("button", name="Giriş").click()
    expect(page.get_by_text("Çok fazla hatalı deneme").first).to_be_visible()
    assert "/login" in page.url


def test_not_found_page(page, app_server):
    """Var olmayan adres kabuk içinde çevrilmiş "Sayfa bulunamadı" kartı gösterir."""
    base_url = app_server["url"]
    login(page, base_url, "admin", NEW_ADMIN_PASSWORD)
    page.goto(base_url + "/boyle-bir-sayfa-yok")
    expect(page.get_by_text("Sayfa bulunamadı.").first).to_be_visible()
    expect(page.get_by_role("button", name="Ana sayfaya dön")).to_be_visible()


def test_production_refuses_default_secret(tmp_path):
    """Canlı ortam ayarıyla varsayılan gizli anahtar verilirse uygulama açılmaz (çıkış kodu 1)."""
    (tmp_path / "scripts").mkdir()
    config_path = write_config(tmp_path, find_free_port(), "production", "degistir-beni")
    process = start_app(config_path, tmp_path / "storage")
    try:
        exit_code = process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        process.kill()
        pytest.fail("Uygulama canlı ortamda güvensiz ayarlarla açıldı")
    assert exit_code == 1
    assert "storage_secret" in process.stdout.read()
