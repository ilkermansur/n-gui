"""test_config.py - app/core/config.py için testler."""

from app.core.config import AppConfig, load_config, save_config_value


def test_missing_file_returns_defaults(tmp_path):
    """Olmayan dosya verilince varsayılan AppConfig dönmeli."""
    path = str(tmp_path / "yok.toml")
    expected = AppConfig()
    # Neden: config_path yüklenen dosyanın yolunu tutar, geri kalanı varsayılan olmalı.
    expected.config_path = path
    assert load_config(path) == expected


def test_reads_values(tmp_path):
    """Dosyadaki değerler AppConfig alanlarına doğru yazılmalı."""
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
    """Yazılan database.url tekrar okununca aynı olmalı."""
    path = tmp_path / "config.toml"
    save_config_value(str(path), "database", "url", "sqlite:///yeni.db")
    result = load_config(str(path))
    assert result.database_url == "sqlite:///yeni.db"


def test_save_config_value_keeps_comments(tmp_path):
    """Kaydederken yorumlar ve diğer değerler korunmalı; eksik anahtar/bölüm eklenmeli."""
    path = tmp_path / "config.toml"
    path.write_text(
        "# üst yorum\n[app]\n# başlık yorumu\ntitle = \"X\"\n\n[database]\nurl = \"a\"\n",
        encoding="utf-8",
    )
    save_config_value(str(path), "database", "url", "b")
    save_config_value(str(path), "app", "port", 9000)
    save_config_value(str(path), "plugins", "disabled", ["x"])
    text = path.read_text(encoding="utf-8")
    assert "# üst yorum" in text
    assert "# başlık yorumu" in text
    result = load_config(str(path))
    assert result.app_title == "X"
    assert result.database_url == "b"
    assert result.port == 9000
    assert result.disabled_plugins == ["x"]


def test_load_config_remembers_path(tmp_path):
    """load_config okunan dosyanın yolunu config_path alanında saklamalı (dosya olmasa da)."""
    path = str(tmp_path / "yok.toml")
    assert load_config(path).config_path == path
    assert AppConfig().config_path == "config.toml"
