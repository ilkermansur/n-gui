"""config.py - config.toml dosyasini okuyup yazar.

Kim kullanir: uygulama baslangici (main) ve ayarlar sayfasi.
Nasil baglanir: load_config() bir AppConfig dondurur; kernel bu nesneyi
diger modullere dagitir. save_config_value() tek bir degeri dosyaya yazar.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w


@dataclass
class AppConfig:
    """Uygulamanin tum ayarlarini tutan veri sinifi (varsayilanlarla birlikte)."""

    app_title: str = "N-GUI"
    database_url: str = "sqlite:///data/app.db"
    storage_secret: str = "degistir-beni"
    scripts_folder: str = "scripts"
    disabled_plugins: list[str] = field(default_factory=list)
    default_language: str = "tr"
    port: int = 8080
    initial_admin_password: str = "admin"


def load_config(path: str) -> AppConfig:
    """config.toml dosyasini okuyup AppConfig dondurur.

    Parametre: path - toml dosyasinin yolu.
    Donus: AppConfig; dosya yoksa ya da bir deger eksikse varsayilanlar kullanilir.
    """
    config = AppConfig()

    # Neden: dosya yoksa uygulama yine de varsayilanlarla acilabilmeli.
    if not Path(path).exists():
        return config

    with open(path, "rb") as file:
        data = tomllib.load(file)

    app_section = data.get("app", {})
    database_section = data.get("database", {})
    plugins_section = data.get("plugins", {})
    scripts_section = data.get("scripts", {})
    auth_section = data.get("auth", {})

    config.app_title = app_section.get("title", config.app_title)
    config.port = app_section.get("port", config.port)
    config.storage_secret = app_section.get("storage_secret", config.storage_secret)
    config.default_language = app_section.get("default_language", config.default_language)
    config.database_url = database_section.get("url", config.database_url)
    config.disabled_plugins = plugins_section.get("disabled", config.disabled_plugins)
    config.scripts_folder = scripts_section.get("folder", config.scripts_folder)
    config.initial_admin_password = auth_section.get(
        "initial_admin_password", config.initial_admin_password
    )
    return config


def save_config_value(path: str, section: str, key: str, value) -> None:
    """config.toml icindeki tek bir degeri degistirip dosyayi geri yazar.

    Parametreler: path - toml yolu; section - bolum adi (ornek "database");
    key - anahtar adi (ornek "url"); value - yazilacak yeni deger.
    Donus: yok.
    """
    data = {}
    if Path(path).exists():
        with open(path, "rb") as file:
            data = tomllib.load(file)

    # Neden: bolum henuz yoksa once bos bir bolum olusturmaliyiz.
    if section not in data:
        data[section] = {}
    data[section][key] = value

    # Not: tomli_w yorum satirlarini korumaz; yazim sirasinda yorumlar kaybolur.
    with open(path, "wb") as file:
        tomli_w.dump(data, file)
