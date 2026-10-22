"""test_form_validation.py - forms eklentisinin UI'dan bağımsız doğrulama testleri.

Kim kullanır: pytest.
Nasıl bağlanır: kernel yokken t() anahtarın kendisini döndürür; testler hata
mesajlarını bu anahtarlarla kontrol eder.
"""

import pytest

from app.core import kernel as kernel_module
from app.core.field_spec import FieldSpec
from plugins.forms.validation import convert_and_validate


@pytest.fixture(autouse=True)
def no_kernel(monkeypatch):
    """t() çevirisiz çalışsın diye kernel'i boşaltır."""
    monkeypatch.setattr(kernel_module, "current_kernel", None)


def test_required_missing():
    """Zorunlu alan boşsa forms.required hatası döner."""
    fields = [FieldSpec(name="host", required=True, label_tr="Sunucu")]
    values, errors = convert_and_validate(fields, {"host": ""})
    assert errors == ["forms.required"]
    values, errors = convert_and_validate(fields, {})
    assert errors == ["forms.required"]


def test_int_conversion_and_bounds():
    """'5' -> 5; min=10 ise hata; ondalıklı metin int için hata."""
    fields = [FieldSpec(name="n", field_type="int")]
    values, errors = convert_and_validate(fields, {"n": "5"})
    assert values == {"n": 5} and errors == []
    values, errors = convert_and_validate(fields, {"n": 5.0})
    assert values == {"n": 5}
    values, errors = convert_and_validate(fields, {"n": "5.5"})
    assert errors == ["forms.not_number"]
    low = [FieldSpec(name="n", field_type="int", min_value=10)]
    values, errors = convert_and_validate(low, {"n": "5"})
    assert errors == ["forms.too_small"]
    high = [FieldSpec(name="n", field_type="float", max_value=1.5)]
    values, errors = convert_and_validate(high, {"n": "2"})
    assert errors == ["forms.too_large"]
    values, errors = convert_and_validate(high, {"n": "1.25"})
    assert values == {"n": 1.25}


def test_bool_conversion():
    """bool: True/False ve 'true'/'0'/'on' gibi metinler kabul edilir."""
    fields = [FieldSpec(name="b", field_type="bool")]
    assert convert_and_validate(fields, {"b": True})[0] == {"b": True}
    assert convert_and_validate(fields, {"b": "TRUE"})[0] == {"b": True}
    assert convert_and_validate(fields, {"b": "off"})[0] == {"b": False}
    assert convert_and_validate(fields, {"b": "0"})[0] == {"b": False}
    values, errors = convert_and_validate(fields, {"b": "belki"})
    assert errors == ["forms.not_bool"]


def test_choice_not_in_options():
    """choice ve multichoice değerleri seçeneklerde olmalıdır."""
    choice = [FieldSpec(name="c", field_type="choice", options=["a", "b"])]
    assert convert_and_validate(choice, {"c": "a"}) == ({"c": "a"}, [])
    assert convert_and_validate(choice, {"c": "z"})[1] == ["forms.not_in_options"]
    multi = [FieldSpec(name="m", field_type="multichoice", options=["a", "b"])]
    assert convert_and_validate(multi, {"m": ["a", "b"]}) == ({"m": ["a", "b"]}, [])
    assert convert_and_validate(multi, {"m": ["a", "z"]})[1] == ["forms.not_in_options"]


def test_optional_empty_uses_default():
    """İsteğe bağlı boş alan varsayılan değeri alır."""
    fields = [
        FieldSpec(name="a", field_type="int", default=7),
        FieldSpec(name="b", default=None),
    ]
    values, errors = convert_and_validate(fields, {"a": "", "b": None})
    assert values == {"a": 7, "b": None} and errors == []


def test_unknown_type_treated_as_str():
    """Bilinmeyen tip metin gibi davranır; date/datetime metin kalır."""
    fields = [
        FieldSpec(name="x", field_type="weird"),
        FieldSpec(name="d", field_type="date"),
    ]
    values, errors = convert_and_validate(fields, {"x": 12, "d": "2026-01-02"})
    assert values == {"x": "12", "d": "2026-01-02"} and errors == []


@pytest.mark.parametrize("field_type", ["int", "float"])
@pytest.mark.parametrize("text", ["nan", "inf", "-inf"])
def test_non_finite_numbers_rejected(field_type, text):
    """nan/inf/-inf hem int hem float için forms.not_number olur (çökmez)."""
    fields = [FieldSpec(name="n", field_type=field_type, min_value=0, max_value=10)]
    values, errors = convert_and_validate(fields, {"n": text})
    assert errors == ["forms.not_number"]
