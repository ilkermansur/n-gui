"""test_system_info.py - plugins/settings_core/system_info.py için testler."""

from plugins.settings_core.system_info import (
    collect_system_info,
    list_installed_packages,
    mask_database_url,
)


def test_mask_database_url():
    """Şifre *** olur; şifresiz adres aynı kalır."""
    assert mask_database_url("postgresql://u:secret@h/db") == "postgresql://u:***@h/db"
    assert mask_database_url("sqlite:///x.db") == "sqlite:///x.db"
    assert mask_database_url("postgresql://u@h/db") == "postgresql://u@h/db"


def test_collect_system_info_keys():
    """Beklenen dört anahtar bulunur ve şifre sızmaz."""
    info = collect_system_info("postgresql://u:secret@h/db")
    assert sorted(info.keys()) == [
        "database_url_masked", "nicegui_version", "platform", "python_version",
    ]
    assert "secret" not in info["database_url_masked"]


def test_list_installed_packages():
    """Her öğe name ve version içerir; pytest listede olmalı."""
    packages = list_installed_packages()
    names = []
    for package in packages:
        assert "version" in package
        names.append(package["name"].lower())
    assert "pytest" in names
