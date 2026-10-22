"""test_translator.py - i18n eklentisindeki Translator sınıfının testleri.

Kim kullanır: pytest.
Nasıl bağlanır: plugins/i18n/translator.py içindeki Translator'ı doğrudan dener;
NiceGUI oturumu gerekmeyen metotlar (translate, load_folder) test edilir.
"""

import json

from plugins.i18n.translator import Translator


def make_translator() -> Translator:
    """İçinde birkaç TR ve EN kaydı olan Translator döndürür."""
    translator = Translator("tr")
    translator.add_translations("tr", {"hello": "Merhaba {name}", "only_tr": "Sadece TR"})
    translator.add_translations("en", {"hello": "Hello {name}", "only_en": "Only EN"})
    return translator


def test_translate_existing():
    """Var olan anahtar istenen dilde döner."""
    translator = make_translator()
    assert translator.translate("only_tr", "tr") == "Sadece TR"
    assert translator.translate("hello", "en", name="Ali") == "Hello Ali"


def test_fallback_to_english():
    """TR'de olmayan anahtar için EN metni döner."""
    translator = make_translator()
    assert translator.translate("only_en", "tr") == "Only EN"


def test_fallback_to_key():
    """Hiçbir dilde yoksa anahtarın kendisi döner."""
    translator = make_translator()
    assert translator.translate("yok.boyle.anahtar", "tr") == "yok.boyle.anahtar"


def test_format_values():
    """Yer tutucular verilen değerlerle doldurulur."""
    translator = make_translator()
    assert translator.translate("hello", "tr", name="Ali") == "Merhaba Ali"


def test_missing_placeholder_value_returns_raw_text():
    """Değer verilmezse hata fırlatılmaz, ham metin döner."""
    translator = make_translator()
    assert translator.translate("hello", "tr") == "Merhaba {name}"


def test_load_folder_merges(tmp_path):
    """İki klasör yüklenince anahtarlar birleşir."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "tr.json").write_text(json.dumps({"a": "Bir"}), encoding="utf-8")
    (second / "tr.json").write_text(json.dumps({"b": "İki"}), encoding="utf-8")
    (second / "en.json").write_text(json.dumps({"b": "Two"}), encoding="utf-8")

    translator = Translator("tr")
    translator.load_folder(str(first))
    translator.load_folder(str(second))

    assert translator.translate("a", "tr") == "Bir"
    assert translator.translate("b", "tr") == "İki"
    assert translator.translate("b", "en") == "Two"


def test_outside_request_uses_default_language():
    """İstek bağlamı dışında dil varsayılandır; set_language hata vermez."""
    translator = make_translator()
    assert translator.get_language() == "tr"
    translator.set_language("en")
    assert translator.get_language() == "tr"
    assert translator.t("hello", name="Ali") == "Merhaba Ali"
    assert translator.pick("merhaba", "hello") == "merhaba"
