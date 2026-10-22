"""system_info.py - sistem bilgisi yardımcıları (Python/platform/paket listesi, DB adresi maskeleme).

Kim kullanır: system_panel.py ve database_panel.py (ekranda gösterirken).
Nasıl bağlanır: yalnızca standart kütüphaneye ve nicegui sürümüne dayanır;
NiceGUI arayüzü ya da veritabanı gerekmez, bu yüzden doğrudan test edilebilir.
"""

import platform
import sys
from importlib import metadata

from sqlalchemy.engine import make_url


def mask_database_url(url: str) -> str:
    """Veritabanı adresindeki şifreyi *** ile değiştirir.

    Parametre: url - örnek "postgresql://u:secret@h/db".
    Dönüş: şifresi gizlenmiş adres; şifre yoksa adres olduğu gibi döner.
    """
    # Neden make_url: adresi elle parçalamak yerine SQLAlchemy'nin ayrıştırıcısı kullanılır.
    try:
        parsed = make_url(url)
    except Exception:
        # Neden: bozuk adres şifre içeriyor olabilir; hiçbir şey göstermemek güvenli.
        return "***"
    if parsed.password is None:
        return url
    # Neden hide_password: SQLAlchemy şifreyi kendisi *** ile gizler.
    return parsed.render_as_string(hide_password=True)


def collect_system_info(database_url: str = "") -> dict:
    """Sistem hakkında kısa bilgiler toplar.

    Parametre: database_url - ham veritabanı adresi (maskelenerek döner).
    Dönüş: python_version, platform, nicegui_version, database_url_masked anahtarlı sözlük.
    """
    try:
        nicegui_version = metadata.version("nicegui")
    except metadata.PackageNotFoundError:
        nicegui_version = "?"
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "nicegui_version": nicegui_version,
        "database_url_masked": mask_database_url(database_url),
    }


def list_installed_packages() -> list[dict]:
    """Kurulu Python paketlerini listeler.

    Dönüş: ada göre sıralı {"name": ..., "version": ...} sözlükleri.
    """
    packages = []
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"]
        # Neden atlanır: bozuk kurulumlarda adı olmayan kayıt çıkabilir.
        if not name:
            continue
        packages.append({"name": name, "version": distribution.version})
    packages.sort(key=get_package_name_lower)
    return packages


def get_package_name_lower(package: dict) -> str:
    """Sıralama anahtarı: paket adının küçük harfli hali. Parametre: package."""
    return package["name"].lower()
