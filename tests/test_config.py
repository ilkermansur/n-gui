"""test_config.py - app/core/config.py icin testler."""

from app.core.config import AppConfig, load_config, save_config_value


def test_missing_file_returns_defaults(tmp_path):
    """Olmayan dosya verilince varsayilan AppConfig donmeli."""
    result = load_config(str(tmp_path / "yok.toml"))
    assert result == AppConfig()


def test_reads_values(tmp_path):
    """Dosyadaki degerler AppConfig alanlarina dogru yazilmali."""
    path = tmp_path / "config.toml"
    path.write_text(
        '[app]\ntitle = "X"\n'
        '[database]\nurl = "sqlite:///x.db"\n'
        '[plugins]\ndisabled = ["scheduler"]\n',
        encoding="utf-8",
    )
    result = load_config(str(path))
    assert result.app_title == "X"
    assert result.database_url == "sqlite:///x.db"
    assert result.disabled_plugins == ["scheduler"]


def test_save_config_value_roundtrip(tmp_path):
    """Yazilan database.url tekrar okununca ayni olmali."""
    path = tmp_path / "config.toml"
    save_config_value(str(path), "database", "url", "sqlite:///yeni.db")
    result = load_config(str(path))
    assert result.database_url == "sqlite:///yeni.db"
