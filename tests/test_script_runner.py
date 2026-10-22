"""test_script_runner.py - plugins/script_engine/runner.py için testler.

Kim kullanır: pytest.
Nasıl bağlanır: her test geçici klasöre küçük bir script yazar ve run_script ile
gerçek bir alt süreçte çalıştırır.
"""

import os
import time

import pytest

from plugins.script_engine.runner import run_script


def write_script(folder, body):
    """Geçici klasöre script.py yazar ve yolunu döner.

    Parametreler: folder (tmp_path), body (script metni).
    """
    script_path = folder / "script.py"
    script_path.write_text(body, encoding="utf-8")
    return str(script_path)


def test_returns_dict(tmp_path):
    path = write_script(tmp_path, "def run(**inputs):\n    return {'a': 1}\n")
    result = run_script(path, {}, 10)
    assert result.success is True
    assert result.result == {"a": 1}
    assert result.timed_out is False
    assert result.duration_ms >= 0


def test_print_output_captured_and_separated_from_result(tmp_path):
    body = "def run(**inputs):\n    print('merhaba')\n    return 5\n"
    result = run_script(write_script(tmp_path, body), {}, 10)
    assert result.success is True
    assert result.result == 5
    assert "merhaba" in result.output_text
    assert "__NGUI_RESULT__" not in result.output_text


def test_exception_gives_error_text_with_message(tmp_path):
    body = "def run(**inputs):\n    raise ValueError('bozuk veri')\n"
    result = run_script(write_script(tmp_path, body), {}, 10)
    assert result.success is False
    assert result.result is None
    assert "bozuk veri" in result.error_text
    assert "ValueError" in result.error_text


def test_timeout(tmp_path):
    body = "import time\n\ndef run(**inputs):\n    time.sleep(5)\n"
    result = run_script(write_script(tmp_path, body), {}, 1)
    assert result.timed_out is True
    assert result.success is False
    assert "Zaman aşımı" in result.error_text


def test_non_json_result_stringified(tmp_path):
    body = (
        "import datetime\n\n"
        "def run(**inputs):\n"
        "    return {'when': datetime.datetime(2026, 1, 2, 3, 4), 'items': {1}}\n"
    )
    result = run_script(write_script(tmp_path, body), {}, 10)
    assert result.success is True
    assert "2026-01-02" in result.result["when"]


def test_huge_output_truncated(tmp_path):
    body = "def run(**inputs):\n    print('x' * 100000)\n    return 1\n"
    result = run_script(write_script(tmp_path, body), {}, 10)
    assert result.success is True
    assert len(result.output_text) <= 20000


def test_arguments_passed(tmp_path):
    body = "def run(**inputs):\n    return inputs['isim'] + '!'\n"
    result = run_script(write_script(tmp_path, body), {"isim": "Çağrı Şükrü İğ"}, 10)
    assert result.success is True
    assert result.result == "Çağrı Şükrü İğ!"


def test_no_marker_when_script_exits_early(tmp_path):
    body = "import sys\n\ndef run(**inputs):\n    sys.exit(0)\n"
    result = run_script(write_script(tmp_path, body), {}, 10)
    assert result.success is False
    assert "sonuç üretmedi" in result.error_text


def test_script_printing_marker_does_not_confuse_parsing(tmp_path):
    body = "def run(**inputs):\n    print('__NGUI_RESULT__ 999')\n    return 7\n"
    result = run_script(write_script(tmp_path, body), {}, 10)
    assert result.success is True
    assert result.result == 7


def test_sibling_module_import_and_cwd(tmp_path):
    (tmp_path / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
    (tmp_path / "data.txt").write_text("veri", encoding="utf-8")
    body = (
        "import helper\n\n"
        "def run(**inputs):\n"
        "    return [helper.VALUE, open('data.txt').read()]\n"
    )
    result = run_script(write_script(tmp_path, body), {}, 10)
    assert result.success is True
    assert result.result == [42, "veri"]


def test_timeout_kills_grandchildren(tmp_path):
    pid_file = tmp_path / "grandchild.pid"
    body = (
        "import subprocess, sys, time\n\n"
        "def run(**inputs):\n"
        "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "    open(%r, 'w').write(str(child.pid))\n"
        "    time.sleep(30)\n" % str(pid_file)
    )
    result = run_script(write_script(tmp_path, body), {}, 1)
    assert result.timed_out is True
    grandchild_pid = int(pid_file.read_text())
    # Öldürülen süreç toplanana kadar kısa bir süre beklenebilir.
    for _ in range(20):
        try:
            os.kill(grandchild_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    with pytest.raises(ProcessLookupError):
        os.kill(grandchild_pid, 0)


def test_nonzero_exit_without_stderr_has_fallback_message(tmp_path):
    body = "import sys\n\ndef run(**inputs):\n    sys.exit(3)\n"
    result = run_script(write_script(tmp_path, body), {}, 10)
    assert result.success is False
    assert "3 koduyla çıktı" in result.error_text


def test_unserializable_arguments_do_not_raise(tmp_path):
    path = write_script(tmp_path, "def run(**inputs):\n    return 1\n")
    result = run_script(path, {"x": object()}, 10)
    assert result.success is False
    assert "Script başlatılamadı" in result.error_text
