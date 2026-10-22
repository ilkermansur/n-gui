"""validation.py - form değerlerini tiplere çeviren ve doğrulayan, UI'dan bağımsız kod.

Kim kullanır: builder.py (form gönderilirken) ve ileride script motoru.
Nasıl bağlanır: FieldSpec listesi + ham değer sözlüğü alır; çevrilmiş değerleri
ve (çeviri anahtarından üretilmiş) hata mesajlarını döndürür. Çeviri için
app.core.text.t kullanılır; "i18n" servisi varsa etiket de dile göre seçilir.
"""

import math

from app.core import kernel as kernel_module
from app.core.field_spec import FieldSpec
from app.core.text import t

TRUE_TEXTS = ["true", "1", "on"]
FALSE_TEXTS = ["false", "0", "off"]


class FieldError(Exception):
    """Bir alanın doğrulaması başarısız olunca fırlatılır.

    key: çeviri anahtarı (örn. "forms.too_small"), values: metne geçecek değerler.
    """

    def __init__(self, key: str, **values) -> None:
        super().__init__(key)
        self.key = key
        self.values = values


def get_field_label(field: FieldSpec) -> str:
    """Alanın ekranda görünecek etiketini döndürür.

    Parametre: field - alan tarifi.
    Dönüş: i18n varsa dile göre seçilmiş etiket; yoksa label_tr, o da boşsa alan adı.
    """
    kernel = kernel_module.current_kernel
    if kernel is not None:
        i18n = kernel.get_service("i18n")
        if i18n is not None:
            picked = i18n.pick(field.label_tr, field.label_en)
            if picked:
                return picked
    return field.label_tr or field.name


def is_empty(value: object) -> bool:
    """Değer boş mu? None, "" ve [] boş sayılır.

    Parametre: value - ham değer. Dönüş: boşsa True.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def convert_str(field: FieldSpec, value: object) -> str:
    """Metin tiplerini (str, text, password, date, datetime, bilinmeyen) metne çevirir.

    Parametreler: field - alan tarifi; value - ham değer. Dönüş: metin.
    """
    return str(value)


def convert_bool(field: FieldSpec, value: object) -> bool:
    """bool değeri ya da "true"/"false"/"1"/"0"/"on"/"off" metnini bool'a çevirir.

    Parametreler: field - alan tarifi; value - ham değer.
    Dönüş: bool. Hata: tanınmayan metin için FieldError("forms.not_bool").
    """
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUE_TEXTS:
        return True
    if text in FALSE_TEXTS:
        return False
    raise FieldError("forms.not_bool")


def check_bounds(field: FieldSpec, number) -> None:
    """Sayının min/max sınırlarını denetler.

    Parametreler: field - alan tarifi; number - çevrilmiş sayı.
    Dönüş: yok. Hata: FieldError("forms.too_small") ya da ("forms.too_large").
    """
    if field.min_value is not None and number < field.min_value:
        raise FieldError("forms.too_small", min=field.min_value)
    if field.max_value is not None and number > field.max_value:
        raise FieldError("forms.too_large", max=field.max_value)


def convert_int(field: FieldSpec, value: object) -> int:
    """Değeri tam sayıya çevirir (5, 5.0 ve "5" olur; "5.5" olmaz) ve sınırlara bakar.

    Parametreler: field - alan tarifi; value - ham değer.
    Dönüş: int. Hata: FieldError("forms.not_number") ve sınır hataları.
    """
    # Neden bool reddedilir: True sayı gibi davranır ama formda anlamsızdır.
    if isinstance(value, bool):
        raise FieldError("forms.not_number")
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        raise FieldError("forms.not_number")
    # Neden önce kontrol: nan/inf için int() hata fırlatır.
    if math.isnan(as_float) or math.isinf(as_float):
        raise FieldError("forms.not_number")
    if as_float != int(as_float):
        raise FieldError("forms.not_number")
    number = int(as_float)
    check_bounds(field, number)
    return number


def convert_float(field: FieldSpec, value: object) -> float:
    """Değeri ondalıklı sayıya çevirir ve sınırlara bakar.

    Parametreler: field - alan tarifi; value - ham değer.
    Dönüş: float. Hata: FieldError("forms.not_number") ve sınır hataları.
    """
    if isinstance(value, bool):
        raise FieldError("forms.not_number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise FieldError("forms.not_number")
    # Neden reddedilir: nan karşılaştırmalarda hep False verir, sınırlardan geçer.
    if math.isnan(number) or math.isinf(number):
        raise FieldError("forms.not_number")
    check_bounds(field, number)
    return number


def convert_choice(field: FieldSpec, value: object) -> object:
    """Değerin seçenekler arasında olduğunu denetler (metin olarak karşılaştırır).

    Parametreler: field - alan tarifi; value - ham değer.
    Dönüş: değerin kendisi. Hata: FieldError("forms.not_in_options").
    """
    option_texts = [str(option) for option in field.options]
    if str(value) not in option_texts:
        raise FieldError("forms.not_in_options")
    return value


def convert_multichoice(field: FieldSpec, value: object) -> list:
    """Her öğenin seçeneklerde olduğunu denetler; sonuç her zaman listedir.

    Parametreler: field - alan tarifi; value - liste (ya da tek değer).
    Dönüş: liste. Hata: FieldError("forms.not_in_options").
    """
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    option_texts = [str(option) for option in field.options]
    for item in items:
        if str(item) not in option_texts:
            raise FieldError("forms.not_in_options")
    return items


def convert_value(field: FieldSpec, value: object) -> object:
    """Alanın tipine uygun çeviriciyi seçip çalıştırır.

    Parametreler: field - alan tarifi; value - boş olmayan ham değer.
    Dönüş: çevrilmiş değer. Bilinmeyen tip metin gibi işlenir.
    """
    if field.field_type == "int":
        return convert_int(field, value)
    elif field.field_type == "float":
        return convert_float(field, value)
    elif field.field_type == "bool":
        return convert_bool(field, value)
    elif field.field_type == "choice":
        return convert_choice(field, value)
    elif field.field_type == "multichoice":
        return convert_multichoice(field, value)
    return convert_str(field, value)


def validate_by_field(fields: list[FieldSpec], raw_values: dict) -> tuple[dict, dict]:
    """Tüm alanları çevirir; hataları alan adına göre toplar.

    Parametreler: fields - alan tarifleri; raw_values - {alan adı: ham değer}.
    Dönüş: (değerler sözlüğü, {alan adı: çevrilmiş hata mesajı}).
    """
    values = {}
    errors = {}
    for field in fields:
        raw = raw_values.get(field.name)
        label = get_field_label(field)
        # bool için False/0 boş değildir; is_empty yalnızca None, "" ve [] bakar.
        if is_empty(raw):
            if field.required:
                errors[field.name] = t("forms.required", field=label)
            else:
                values[field.name] = field.default
            continue
        try:
            values[field.name] = convert_value(field, raw)
        except FieldError as error:
            errors[field.name] = t(error.key, field=label, **error.values)
    return values, errors


def convert_and_validate(fields: list[FieldSpec], raw_values: dict) -> tuple[dict, list[str]]:
    """Ham form değerlerini tiplere çevirir ve doğrular.

    Parametreler: fields - alan tarifleri; raw_values - {alan adı: ham değer}.
    Dönüş: (çevrilmiş değerler, çevrilmiş hata mesajları listesi). Hata yoksa liste boştur.
    """
    values, errors = validate_by_field(fields, raw_values)
    return values, list(errors.values())
