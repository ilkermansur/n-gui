"""test_script_parser.py - script_engine parser testleri.

Kim kullanır: pytest.
Nasıl bağlanır: tests/sample_scripts içindeki örnek dosyaları ve geçici
dosyaları parse_script_file ile okuyup ScriptSpec sonucunu kontrol eder.
"""

import os

from plugins.script_engine.parser import make_script_id, parse_script_file

SAMPLES = os.path.join(os.path.dirname(__file__), "sample_scripts")


def sample(name):
    """Örnek script dosyasının tam yolunu döndürür."""
    return os.path.join(SAMPLES, name)


def write_script(tmp_path, text, name="s.py"):
    """Geçici bir script dosyası yazar ve yolunu döndürür."""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_full_metadata():
    spec = parse_script_file(sample("full_metadata.py"))
    assert spec.error == ""
    assert spec.script_id == "full_metadata"
    assert spec.description == "Cihazdaki servisi yeniden başlatır."
    assert spec.title_tr == "Servis Yeniden Başlat"
    assert spec.title_en == "Restart Service"
    assert spec.suggested_section == "Operation"
    assert spec.suggested_group == "Ürün A"
    assert spec.mode == "form"
    assert spec.roles == ["operator", "admin"]
    assert spec.timeout == 60
    assert spec.refresh == 30
    assert spec.schedule == "0 8 * * 1"
    assert [f.name for f in spec.fields] == ["host", "port", "mode", "start"]
    host, port, mode, start = spec.fields
    assert host.label_tr == "Sunucu" and host.label_en == "Sunucu"
    assert host.required is True
    assert port.field_type == "int"
    assert port.default == 22
    assert port.min_value == 1 and port.max_value == 65535
    assert mode.field_type == "choice"
    assert mode.options == ["soft", "hard"]
    assert mode.default == "soft"
    assert start.field_type == "date"
    assert start.required is False


def test_signature_only():
    spec = parse_script_file(sample("signature_only.py"))
    assert spec.error == ""
    assert spec.title_tr == "Signature only"
    assert spec.title_en == "Signature only"
    assert spec.mode == "form"
    assert len(spec.fields) == 3
    host, port, verbose = spec.fields
    assert host.required is True
    assert port.required is False
    assert port.default == 22
    assert port.field_type == "int"
    assert verbose.field_type == "bool"
    assert verbose.default is False


def test_yaml_overrides_signature_label_and_type(tmp_path):
    text = '"""Aciklama\n---\ninputs:\n  n: {type: float, label: {tr: Sayı, en: Number}, required: true, default: 2.5}\n---\n"""\ndef run(n: int = 1):\n    return n\n'
    spec = parse_script_file(write_script(tmp_path, text))
    assert spec.error == ""
    field = spec.fields[0]
    assert field.field_type == "float"
    assert field.label_tr == "Sayı"
    assert field.label_en == "Number"
    assert field.required is True
    assert field.default == 2.5


def test_syntax_error_sets_error():
    spec = parse_script_file(sample("syntax_error.py"))
    assert spec.error.startswith("Satır 3: söz dizimi hatası")


def test_missing_run_sets_error():
    spec = parse_script_file(sample("no_run.py"))
    assert spec.error == "run() fonksiyonu bulunamadı"


def test_bad_yaml_sets_error():
    spec = parse_script_file(sample("bad_yaml.py"))
    assert spec.error.startswith("YAML okunamadı")


def test_invalid_mode_sets_error(tmp_path):
    text = '"""x\n---\nmode: foo\n---\n"""\ndef run():\n    return 1\n'
    spec = parse_script_file(write_script(tmp_path, text))
    assert spec.error == "Geçersiz mod: foo"


def test_make_script_id():
    assert make_script_id("Servis Yönet-1.py") == "servis_yonet_1"
    assert make_script_id("ÇığÖşÜİ.py") == "cigosui"
    assert make_script_id("__a___b__.py") == "a_b"
    assert make_script_id("...py") == "script"


def test_missing_file_sets_error(tmp_path):
    spec = parse_script_file(str(tmp_path / "yok.py"))
    assert spec.error != ""


def test_non_utf8_file_sets_error(tmp_path):
    path = tmp_path / "bad.py"
    path.write_bytes(b"\xff\xfe\x00bad")
    spec = parse_script_file(str(path))
    assert spec.error != ""


def test_no_closing_separator_treats_rest_as_yaml(tmp_path):
    text = '"""Aciklama\n---\nmode: live\n"""\ndef run():\n    return 1\n'
    spec = parse_script_file(write_script(tmp_path, text))
    assert spec.error == ""
    assert spec.mode == "live"
    assert spec.description == "Aciklama"


def test_unknown_type_timeout_roles_errors(tmp_path):
    bad_type = '"""x\n---\ninputs:\n  a: {type: foo}\n---\n"""\ndef run(a):\n    return 1\n'
    assert "foo" in parse_script_file(write_script(tmp_path, bad_type)).error
    bad_timeout = '"""x\n---\ntimeout: -5\n---\n"""\ndef run():\n    return 1\n'
    assert parse_script_file(write_script(tmp_path, bad_timeout)).error != ""
    bad_roles = '"""x\n---\nroles: admin\n---\n"""\ndef run():\n    return 1\n'
    assert parse_script_file(write_script(tmp_path, bad_roles)).error != ""


def test_kwargs_ignored_and_input_not_in_signature(tmp_path):
    text = 'def run(a: str, *args, **kwargs):\n    return 1\n'
    spec = parse_script_file(write_script(tmp_path, text))
    assert [f.name for f in spec.fields] == ["a"]
    text = '"""x\n---\ninputs:\n  zzz: {type: str}\n---\n"""\ndef run(a: str):\n    return 1\n'
    spec = parse_script_file(write_script(tmp_path, text))
    assert "zzz" in spec.error


def test_yaml_non_yamlerror_exceptions_set_error(tmp_path):
    text = '"""x\n---\ntitle: 2001-13-45\n---\n"""\ndef run():\n    return 1\n'
    spec = parse_script_file(write_script(tmp_path, text))
    assert spec.error.startswith("YAML okunamadı")
    deep = '"""x\n---\ntitle: ' + "[" * 5000 + '\n---\n"""\ndef run():\n    return 1\n'
    spec = parse_script_file(write_script(tmp_path, deep, "deep.py"))
    assert spec.error.startswith("YAML okunamadı")


def test_kwargs_run_takes_fields_from_yaml(tmp_path):
    text = (
        '"""x\n---\ninputs:\n  host: {type: int, label: Sunucu, required: true, default: 5, min: 1}\n'
        '  note: {}\n---\n"""\ndef run(**kwargs):\n    return 1\n'
    )
    spec = parse_script_file(write_script(tmp_path, text))
    assert spec.error == ""
    host, note = spec.fields
    assert host.field_type == "int" and host.required is True
    assert host.default == 5 and host.min_value == 1 and host.label_tr == "Sunucu"
    assert note.field_type == "str" and note.required is False


def test_required_must_be_bool_and_text_fields_not_list(tmp_path):
    text = '"""x\n---\ninputs:\n  a: {required: "false"}\n---\n"""\ndef run(a):\n    return 1\n'
    assert "required" in parse_script_file(write_script(tmp_path, text)).error
    for key in ["title", "section", "group"]:
        text = '"""x\n---\n' + key + ': [a, b]\n---\n"""\ndef run():\n    return 1\n'
        assert parse_script_file(write_script(tmp_path, text)).error != ""
