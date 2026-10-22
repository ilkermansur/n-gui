"""config.py - config.toml dosyasını okuyup yazar.

Kim kullanır: uygulama başlangıcı (main) ve ayarlar sayfası.
Nasıl bağlanır: load_config() bir AppConfig döndürür; kernel bu nesneyi
diğer modüllere dağıtır. save_config_value() tek bir değeri dosyaya yazar.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w


@dataclass
class AppConfig:
    """Uygulamanın tüm ayarlarını tutan veri sınıfı (varsayılanlarla birlikte)."""

    app_title: str = "N-GUI"
    database_url: str = "sqlite:///data/app.db"
    storage_secret: str = "degistir-beni"
    scripts_folder: str = "scripts"
    disabled_plugins: list[str] = field(default_factory=list)
    default_language: str = "tr"
    port: int = 8080
    initial_admin_password: str = "admin"
    # Neden burada: ayarlar sayfası değişiklikleri hangi dosyaya yazacağını bilmeli.
    config_path: str = "config.toml"


def load_config(path: str) -> AppConfig:
    """config.toml dosyasını okuyup AppConfig döndürür.

    Parametre: path - toml dosyasının yolu.
    Dönüş: AppConfig; dosya yoksa ya da bir değer eksikse varsayılanlar kullanılır.
    """
    config = AppConfig()
    config.config_path = path

    # Neden: dosya yoksa uygulama yine de varsayılanlarla açılabilmeli.
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
    """config.toml içindeki tek bir değeri yerinde değiştirir; yorumlar korunur.

    Parametreler: path - toml yolu; section - bölüm adı (örnek "database");
    key - anahtar adı (örnek "url"); value - yazılacak yeni değer.
    Dönüş: yok.
    """
    lines = []
    if Path(path).exists():
        with open(path, encoding="utf-8") as file:
            lines = file.read().splitlines()

    # Neden: değeri toml kurallarına uygun yazmak için (tırnak, liste vb.) tomli_w kullanılır.
    new_line = tomli_w.dumps({key: value}).strip()
    section_header = "[" + section + "]"

    inside_section = False
    section_header_index = -1
    replaced = False
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            inside_section = stripped == section_header
            if inside_section:
                section_header_index = len(result)
        elif inside_section and not replaced and "=" in stripped:
            if stripped.split("=")[0].strip() == key:
                line = new_line
                replaced = True
        result.append(line)

    if not replaced:
        if section_header_index >= 0:
            # Neden: anahtar yoksa bölüm başlığının hemen altına eklenir.
            result.insert(section_header_index + 1, new_line)
        else:
            # Neden: bölüm hiç yoksa dosyanın sonuna yeni bölüm açılır.
            if len(result) > 0 and result[-1].strip() != "":
                result.append("")
            result.append(section_header)
            result.append(new_line)

    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(result) + "\n")
