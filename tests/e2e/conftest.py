"""conftest.py - uçtan uca testlerin ortak fixture'ları: çalışan uygulama ve tarayıcı.

Kim kullanır: tests/e2e altındaki testler.
Nasıl bağlanır:
- app_server: geçici bir klasörde config.toml, boş bir SQLite veritabanı ve scripts klasörü
  hazırlar, uygulamayı `python -m app.main --config ...` ile ayrı bir süreçte başlatır ve
  adresini döndürür. Testler bittiğinde süreç durdurulur. Geliştirici veritabanına dokunulmaz.
- browser: Playwright Chromium. Hazır kurulu bir Chromium kullanmak için
  NGUI_CHROMIUM=/yol/chrome verin (yoksa `playwright install chromium` gerekir).
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

# Depo kökü: uygulama eklentileri "plugins" klasöründen göreli olarak bulur.
REPO_ROOT = Path(__file__).resolve().parents[2]
# Testlerin kullandığı ilk admin parolası.
ADMIN_PASSWORD = "ilk-parola-123"
# Uygulamanın açılmasını beklemenin üst sınırı (saniye).
STARTUP_TIMEOUT_SECONDS = 60


def find_free_port() -> int:
    """İşletim sisteminden boş bir TCP portu alır."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def write_config(folder: Path, port: int, environment: str, storage_secret: str) -> Path:
    """Test için config.toml yazar ve yolunu döndürür.

    Parametreler: folder - geçici klasör; port; environment - "development"/"production";
    storage_secret - oturum anahtarı.
    """
    config_path = folder / "config.toml"
    config_path.write_text(
        "[app]\n"
        'title = "N-GUI Test"\n'
        "port = " + str(port) + "\n"
        'storage_secret = "' + storage_secret + '"\n'
        'environment = "' + environment + '"\n'
        "[database]\n"
        'url = "sqlite:///' + str(folder / "test.db") + '"\n'
        "[plugins]\n"
        'disabled = ["ornek_eklenti_sablonu"]\n'
        "[scripts]\n"
        'folder = "' + str(folder / "scripts") + '"\n'
        "[auth]\n"
        'initial_admin_password = "' + ADMIN_PASSWORD + '"\n'
        "max_login_attempts = 3\n"
        "lockout_minutes = 1\n",
        encoding="utf-8",
    )
    return config_path


def start_app(config_path: Path, storage_folder: Path) -> subprocess.Popen:
    """Uygulamayı verilen ayarlarla ayrı bir süreçte başlatır."""
    environment = dict(os.environ)
    # Neden: tarayıcı oturumları geliştiricinin .nicegui klasörüne karışmasın.
    environment["NICEGUI_STORAGE_PATH"] = str(storage_folder)
    # Neden: NiceGUI bu değişkeni görünce kendi test moduna geçer ve gerçek sunucu açmaz.
    environment.pop("PYTEST_CURRENT_TEST", None)
    return subprocess.Popen(
        [sys.executable, "-m", "app.main", "--config", str(config_path)],
        cwd=str(REPO_ROOT),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_until_ready(base_url: str, process: subprocess.Popen) -> None:
    """Uygulama /login adresine cevap verene kadar bekler; açılamazsa testi durdurur."""
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read()
            pytest.fail("Uygulama açılırken kapandı:\n" + output)
        try:
            urllib.request.urlopen(base_url + "/login", timeout=2)
            return
        except OSError:
            time.sleep(0.5)
    pytest.fail("Uygulama " + str(STARTUP_TIMEOUT_SECONDS) + " saniyede açılmadı")


@pytest.fixture(scope="session")
def app_server(tmp_path_factory):
    """Geçici veritabanıyla çalışan uygulamanın adresini döndürür (oturum boyunca tek süreç)."""
    folder = tmp_path_factory.mktemp("ngui_app")
    (folder / "scripts").mkdir()
    port = find_free_port()
    config_path = write_config(folder, port, "development", "e2e-test-" + "x" * 40)
    process = start_app(config_path, folder / "storage")
    base_url = "http://127.0.0.1:" + str(port)
    wait_until_ready(base_url, process)
    yield {"url": base_url, "folder": folder}
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.fixture(scope="session")
def browser():
    """Başsız (headless) Chromium döndürür."""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    executable_path = os.environ.get("NGUI_CHROMIUM") or None
    chromium = playwright.chromium.launch(executable_path=executable_path)
    yield chromium
    chromium.close()
    playwright.stop()


@pytest.fixture
def page(browser):
    """Her test için temiz çerezli yeni bir sekme döndürür."""
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    new_page = context.new_page()
    new_page.set_default_timeout(15000)
    yield new_page
    context.close()
