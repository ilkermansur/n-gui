"""test_form_uploads.py - plugins/forms/builder.py içindeki discard_uploaded_file testleri.

Kim kullanır: pytest.
Nasıl bağlanır: geçici bir yükleme klasörü kurulur; NiceGUI arayüzü gerekmez.
"""

from plugins.forms.builder import discard_uploaded_file


def test_deletes_file_inside_upload_folder(tmp_path):
    """Yükleme klasöründeki dosya silinir."""
    folder = tmp_path / "uploads"
    folder.mkdir()
    uploaded = folder / "abc_rapor.txt"
    uploaded.write_text("x", encoding="utf-8")
    assert discard_uploaded_file(str(uploaded), str(folder)) is True
    assert not uploaded.exists()


def test_never_deletes_outside_upload_folder(tmp_path):
    """Klasör dışındaki (ya da ../ ile kaçan) dosyaya dokunulmaz."""
    folder = tmp_path / "uploads"
    folder.mkdir()
    outside = tmp_path / "config.toml"
    outside.write_text("x", encoding="utf-8")
    assert discard_uploaded_file(str(outside), str(folder)) is False
    assert discard_uploaded_file(str(folder / ".." / "config.toml"), str(folder)) is False
    assert outside.exists()


def test_missing_file_is_ignored(tmp_path):
    """Olmayan dosya hata vermez."""
    assert discard_uploaded_file(str(tmp_path / "yok.txt"), str(tmp_path)) is False
