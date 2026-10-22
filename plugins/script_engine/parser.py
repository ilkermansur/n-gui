"""parser.py - yüklenen Python script'inden ScriptSpec üretir.

Kim kullanır: script yükleme sihirbazı, "Yeniden tara" işlemi, form üretimi
ve runner (sonraki task'lar).
Nasıl bağlanır: script ASLA import edilmez; dosya metni ast ile okunur. Böylece
hatalı veya zararlı bir script yükleme sırasında uygulamayı etkileyemez.
Docstring'deki `---` arasındaki YAML bloğu ile run() imzası birleştirilir ve
sonuç bir ScriptSpec olarak döner. Sorunlar hata fırlatmaz, `error` alanına
Türkçe mesajla yazılır.
"""

import ast
import os
import re
from dataclasses import dataclass, field

import yaml

from app.core.field_spec import FieldSpec

ALLOWED_MODES = ["form", "live", "scheduled"]

ALLOWED_FIELD_TYPES = [
    "str", "text", "int", "float", "bool", "choice",
    "multichoice", "date", "datetime", "file", "password",
]

# Annotation adından alan tipine eşleme; listede olmayanlar str sayılır.
ANNOTATION_TYPES = {
    "str": "str",
    "int": "int",
    "float": "float",
    "bool": "bool",
    "list": "multichoice",
    "date": "date",
    "datetime": "datetime",
}

# Türkçe harflerin ASCII karşılıkları (büyük harfler dahil).
TURKISH_MAP = {
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
}


@dataclass
class ScriptSpec:
    """Bir script'in okunan tarifi: başlık, mod, roller ve form alanları."""

    script_id: str
    file_path: str
    description: str = ""
    title_tr: str = ""
    title_en: str = ""
    suggested_section: str = ""
    suggested_group: str = ""
    mode: str = "form"
    roles: list = field(default_factory=list)
    timeout: int = 60
    refresh: int = 30
    schedule: str = ""
    fields: list = field(default_factory=list)
    error: str = ""


def make_script_id(file_name: str) -> str:
    """Dosya adından güvenli bir script kimliği üretir.

    Parametre: file_name - örn. "Servis Yönet-1.py".
    Dönüş: yalnızca [a-z0-9_] içeren kimlik; boş kalırsa "script".
    """
    name = file_name
    if name.lower().endswith(".py"):
        name = name[:-3]
    # Küçük harfe çevirmeden önce Türkçe harfler değiştirilir; "İ".lower()
    # tek karakter vermez, bu yüzden sıra önemlidir.
    for turkish_char, ascii_char in TURKISH_MAP.items():
        name = name.replace(turkish_char, ascii_char)
    name = name.lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    if name == "":
        return "script"
    return name


def default_title(file_path: str) -> str:
    """Dosya adından başlık üretir: alt çizgiler boşluk, ilk harf büyük."""
    stem = os.path.splitext(os.path.basename(file_path))[0]
    text = stem.replace("_", " ").strip()
    if text == "":
        return "Script"
    return text[0].upper() + text[1:]


def split_docstring(docstring: str):
    """Docstring'i açıklama ve YAML metnine böler.

    Parametre: docstring - ast.get_docstring çıktısı.
    Dönüş: (açıklama, yaml_metni); `---` yoksa yaml_metni boş gelir.
    Kapanış `---` yoksa açılıştan sonrası YAML kabul edilir.
    """
    lines = docstring.split("\n")
    marker_indexes = []
    for index in range(len(lines)):
        if lines[index].strip() == "---":
            marker_indexes.append(index)
    if len(marker_indexes) == 0:
        return docstring.strip(), ""
    start = marker_indexes[0]
    description = "\n".join(lines[:start]).strip()
    if len(marker_indexes) >= 2:
        end = marker_indexes[1]
        yaml_text = "\n".join(lines[start + 1:end])
    else:
        yaml_text = "\n".join(lines[start + 1:])
    return description, yaml_text


def read_text_pair(value, fallback: str):
    """Düz metin veya {tr, en} değerinden (tr, en) çifti çıkarır.

    Parametreler: value - YAML'dan gelen değer; fallback - hiçbiri yoksa metin.
    Dönüş: (tr_metni, en_metni).
    """
    if isinstance(value, dict):
        text_tr = str(value.get("tr", "") or "")
        text_en = str(value.get("en", "") or "")
        # Biri eksikse diğeri kullanılır; ikisi de yoksa yedek metin.
        if text_tr == "":
            text_tr = text_en or fallback
        if text_en == "":
            text_en = text_tr or fallback
        return text_tr, text_en
    if value is None or str(value).strip() == "":
        return fallback, fallback
    return str(value), str(value)


def annotation_to_type(annotation) -> str:
    """Parametre tip ipucunu (ast düğümü) alan tipine çevirir."""
    if annotation is None:
        return "str"
    if isinstance(annotation, ast.Name):
        type_name = annotation.id
    elif isinstance(annotation, ast.Attribute):
        # datetime.date gibi yazımlarda son parça kullanılır.
        type_name = annotation.attr
    elif isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        # list[str] gibi yazımlarda köşeli parantez öncesi kullanılır.
        type_name = annotation.value.id
    else:
        return "str"
    return ANNOTATION_TYPES.get(type_name, "str")


def read_default(default_node):
    """Varsayılan değer düğümünü okur; okunamazsa None döner."""
    try:
        return ast.literal_eval(default_node)
    except (ValueError, TypeError, SyntaxError):
        return None


def fields_from_signature(run_node) -> list:
    """run() imzasındaki parametrelerden FieldSpec listesi üretir.

    *args ve **kwargs alan olmaz. Varsayılanı olmayan parametre zorunludur.
    """
    arguments = run_node.args
    positional = list(arguments.posonlyargs) + list(arguments.args)
    # defaults listesi, parametrelerin SON kısmına karşılık gelir.
    first_default_index = len(positional) - len(arguments.defaults)

    fields = []
    for index in range(len(positional)):
        arg = positional[index]
        has_default = index >= first_default_index
        default_value = None
        if has_default:
            default_value = read_default(arguments.defaults[index - first_default_index])
        fields.append(make_signature_field(arg, has_default, default_value))

    for index in range(len(arguments.kwonlyargs)):
        arg = arguments.kwonlyargs[index]
        default_node = arguments.kw_defaults[index]
        has_default = default_node is not None
        default_value = None
        if has_default:
            default_value = read_default(default_node)
        fields.append(make_signature_field(arg, has_default, default_value))
    return fields


def make_signature_field(arg, has_default: bool, default_value) -> FieldSpec:
    """Tek bir imza parametresinden FieldSpec oluşturur."""
    return FieldSpec(
        name=arg.arg,
        field_type=annotation_to_type(arg.annotation),
        label_tr=arg.arg,
        label_en=arg.arg,
        required=not has_default,
        default=default_value,
    )


def apply_yaml_input(field_spec: FieldSpec, config) -> str:
    """YAML'daki bir girdi tarifini FieldSpec üzerine uygular.

    Parametreler: field_spec - imzadan gelen alan; config - YAML değeri.
    Dönüş: hata mesajı; sorun yoksa boş metin.
    """
    if config is None:
        return ""
    if not isinstance(config, dict):
        return "Girdi '" + field_spec.name + "' bir sözlük olmalı"

    if "type" in config:
        field_type = str(config["type"])
        if field_type not in ALLOWED_FIELD_TYPES:
            return "Geçersiz alan tipi: " + field_type + " (girdi '" + field_spec.name + "')"
        field_spec.field_type = field_type
    if "label" in config:
        label_tr, label_en = read_text_pair(config["label"], field_spec.name)
        field_spec.label_tr = label_tr
        field_spec.label_en = label_en
    if "required" in config:
        # "false" gibi metinler bool() ile True olurdu; sadece gerçek bool kabul.
        if not isinstance(config["required"], bool):
            return "Girdi '" + field_spec.name + "' required true/false olmalı"
        field_spec.required = config["required"]
    if "default" in config:
        field_spec.default = config["default"]
    if "options" in config:
        if not isinstance(config["options"], list):
            return "Girdi '" + field_spec.name + "': options bir liste olmalı"
        field_spec.options = list(config["options"])
    if "min" in config:
        field_spec.min_value = config["min"]
    if "max" in config:
        field_spec.max_value = config["max"]
    if "help" in config:
        field_spec.help_text = str(config["help"])
    return ""


def is_positive_int(value) -> bool:
    """Değer pozitif bir tam sayı mı (bool tam sayı sayılmaz)."""
    if isinstance(value, bool):
        return False
    return isinstance(value, int) and value > 0


def apply_yaml_settings(spec: ScriptSpec, data: dict) -> str:
    """YAML'daki üst düzey ayarları (başlık, mod, roller...) spec'e yazar.

    Dönüş: hata mesajı; sorun yoksa boş metin.
    """
    if "title" in data:
        if isinstance(data["title"], list):
            return "title metin veya {tr, en} olmalı"
        title_tr, title_en = read_text_pair(data["title"], spec.title_tr)
        spec.title_tr = title_tr
        spec.title_en = title_en
    if "section" in data:
        if isinstance(data["section"], (list, dict)):
            return "section bir metin olmalı"
        spec.suggested_section = str(data["section"] or "")
    if "group" in data:
        if isinstance(data["group"], (list, dict)):
            return "group bir metin olmalı"
        spec.suggested_group = str(data["group"] or "")
    if "mode" in data:
        mode = str(data["mode"])
        if mode not in ALLOWED_MODES:
            return "Geçersiz mod: " + mode
        spec.mode = mode
    if "roles" in data:
        roles = data["roles"]
        if not isinstance(roles, list):
            return "roles bir liste olmalı"
        for role in roles:
            if not isinstance(role, str):
                return "roles yalnızca metin içermeli"
        spec.roles = list(roles)
    if "timeout" in data:
        if not is_positive_int(data["timeout"]):
            return "timeout pozitif bir tam sayı olmalı"
        spec.timeout = data["timeout"]
    if "refresh" in data:
        if not is_positive_int(data["refresh"]):
            return "refresh pozitif bir tam sayı olmalı"
        spec.refresh = data["refresh"]
    if "schedule" in data:
        spec.schedule = str(data["schedule"] or "")
    return ""


def apply_yaml_inputs(spec: ScriptSpec, inputs, has_var_keyword: bool) -> str:
    """YAML `inputs` bölümünü imzadan gelen alanlara ada göre uygular.

    Parametreler: spec - üzerine yazılacak spec; inputs - YAML değeri;
    has_var_keyword - run() **kwargs alıyor mu. Alıyorsa imzada olmayan
    girdiler YAML'dan yeni alan olarak eklenir, almıyorsa hata verilir.
    """
    if inputs is None:
        return ""
    if not isinstance(inputs, dict):
        return "inputs bir sözlük olmalı"
    for input_name, config in inputs.items():
        target = None
        for field_spec in spec.fields:
            if field_spec.name == str(input_name):
                target = field_spec
        if target is None and has_var_keyword:
            target = FieldSpec(
                name=str(input_name),
                field_type="str",
                label_tr=str(input_name),
                label_en=str(input_name),
                required=False,
            )
            spec.fields.append(target)
        if target is None:
            return "inputs içindeki '" + str(input_name) + "' run() imzasında yok"
        error = apply_yaml_input(target, config)
        if error != "":
            return error
    return ""


def find_run_function(tree):
    """Modül düzeyindeki run fonksiyonunu bulur; yoksa None döner."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run":
            return node
    return None


def parse_script_file(path: str) -> ScriptSpec:
    """Script dosyasını okuyup ScriptSpec üretir; asla hata fırlatmaz.

    Parametre: path - .py dosyasının yolu.
    Dönüş: ScriptSpec; sorun varsa `error` alanı Türkçe mesaj içerir.
    """
    file_name = os.path.basename(path)
    spec = ScriptSpec(script_id=make_script_id(file_name), file_path=path)
    title = default_title(path)
    spec.title_tr = title
    spec.title_en = title

    # Dosya UTF-8 olarak okunur; okunamazsa hata mesajı yazılır.
    try:
        with open(path, "r", encoding="utf-8") as script_file:
            source = script_file.read()
    except UnicodeDecodeError:
        spec.error = "Dosya UTF-8 olarak okunamadı"
        return spec
    except OSError as error:
        spec.error = "Dosya okunamadı: " + str(error)
        return spec

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        spec.error = "Satır " + str(error.lineno) + ": söz dizimi hatası: " + str(error.msg)
        return spec
    except ValueError as error:
        spec.error = "Dosya ayrıştırılamadı: " + str(error)
        return spec

    run_node = find_run_function(tree)
    if run_node is None:
        spec.error = "run() fonksiyonu bulunamadı"
        return spec
    spec.fields = fields_from_signature(run_node)

    docstring = ast.get_docstring(tree)
    if docstring is None:
        return spec
    description, yaml_text = split_docstring(docstring)
    spec.description = description
    if yaml_text.strip() == "":
        return spec

    try:
        data = yaml.safe_load(yaml_text)
    except Exception as error:
        # safe_load sadece YAMLError değil ValueError (geçersiz tarih),
        # RecursionError (aşırı iç içe yapı) gibi hatalar da fırlatabilir.
        spec.error = "YAML okunamadı: " + str(error)
        return spec
    if data is None:
        return spec
    if not isinstance(data, dict):
        spec.error = "YAML okunamadı: üst düzey bir sözlük olmalı"
        return spec

    error = apply_yaml_settings(spec, data)
    if error == "":
        has_var_keyword = run_node.args.kwarg is not None
        error = apply_yaml_inputs(spec, data.get("inputs"), has_var_keyword)
    spec.error = error
    return spec
