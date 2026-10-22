"""test_theme.py - app/core/theme.py içindeki UI'sız yardımcıların testleri.

Kim kullanır: pytest.
Nasıl bağlanır: yalnızca NiceGUI bağlamı gerektirmeyen betik üreticileri test edilir.
"""

from app.core.theme import html_lang_script, quasar_language_html


def test_script_sets_document_language():
    """Betik <html> öğesinin lang özelliğini verilen dile ayarlar."""
    assert html_lang_script("tr") == '<script>document.documentElement.lang = "tr";</script>'


def test_script_escapes_language_value():
    """Dil değeri tırnak içinde kaçışlanır; betiğin dışına taşamaz."""
    script = html_lang_script('x";alert(1);"')
    assert 'lang = "x\\";alert(1);\\"";' in script


def test_turkish_loads_quasar_language_pack():
    """Türkçe için Quasar'ın tr paketi yüklenir ve etkinleştirilir."""
    html = quasar_language_html("tr")
    assert "/static/lang/tr.umd.prod.js" in html
    assert 'Quasar.Lang.set(Quasar.Lang["tr"])' in html


def test_english_and_unknown_language_need_no_pack():
    """İngilizce NiceGUI'nin varsayılanıdır; bilinmeyen dilde de betik eklenmez."""
    assert quasar_language_html("en") == ""
    assert quasar_language_html("de") == ""
