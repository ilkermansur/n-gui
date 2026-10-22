"""builder.py - FieldSpec listesinden NiceGUI formu çizen kod.

Kim kullanır: "forms" servisi (build_form); ileride script motoru ve sayfalar.
Nasıl bağlanır: her alan tipi için ayrı bir create_<tip>_widget(field) fonksiyonu
vardır; build_form bunları if/elif zinciriyle seçer, iki sütunlu bir grid'e koyar
ve FormHandle döndürür. FormHandle.submit() değerleri validation.py ile doğrular
ve hataları her alanın altında gösterir.
"""

import os
import re
import uuid

from nicegui import ui

from app.core.field_spec import FieldSpec
from plugins.forms.validation import get_field_label, validate_by_field

UPLOAD_FOLDER = os.path.join("data", "uploads")
# Neden geniş alanlar: uzun içerikli kutular iki sütunu birden kaplasın.
WIDE_TYPES = ["text", "multichoice", "file"]


def sanitize_file_name(original_name: str) -> str:
    """Yüklenen dosyanın adını güvenli hale getirir (yol ve garip karakterleri atar).

    Parametre: original_name - tarayıcının bildirdiği ad. Dönüş: güvenli ad.
    """
    # Neden basename: "../../x" gibi adlarla klasör dışına yazılmasın.
    base_name = os.path.basename(original_name.replace("\\", "/"))
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
    if safe_name.strip("._") == "":
        safe_name = "file"
    return safe_name


def create_str_widget(field: FieldSpec):
    """Tek satırlık metin kutusu çizer. Parametre: field. Dönüş: widget."""
    value = field.default if field.default is not None else ""
    return ui.input(label=get_field_label(field), value=value).props("outlined").classes("w-full")


def create_text_widget(field: FieldSpec):
    """Çok satırlı metin kutusu çizer. Parametre: field. Dönüş: widget."""
    value = field.default if field.default is not None else ""
    return ui.textarea(label=get_field_label(field), value=value).props("outlined").classes("w-full")


def create_password_widget(field: FieldSpec):
    """Parola kutusu çizer. Parametre: field. Dönüş: widget."""
    value = field.default if field.default is not None else ""
    return ui.input(label=get_field_label(field), value=value, password=True).props("outlined").classes("w-full")


def create_number_widget(field: FieldSpec):
    """int ve float için sayı kutusu çizer. Parametre: field. Dönüş: widget."""
    widget = ui.number(label=get_field_label(field), value=field.default)
    return widget.props("outlined").classes("w-full")


def create_bool_widget(field: FieldSpec):
    """Aç/kapa anahtarı çizer. Parametre: field. Dönüş: widget."""
    return ui.switch(text=get_field_label(field), value=bool(field.default))


def create_choice_widget(field: FieldSpec):
    """Tek seçimli liste çizer. Parametre: field. Dönüş: widget."""
    widget = ui.select(options=field.options, label=get_field_label(field), value=field.default)
    return widget.props("outlined").classes("w-full")


def create_multichoice_widget(field: FieldSpec):
    """Çok seçimli liste çizer. Parametre: field. Dönüş: widget."""
    if isinstance(field.default, list):
        value = field.default
    else:
        value = []
    widget = ui.select(options=field.options, label=get_field_label(field), value=value, multiple=True)
    return widget.props("outlined use-chips").classes("w-full")


def create_date_widget(field: FieldSpec):
    """Tarih kutusu çizer (type=date). Parametre: field. Dönüş: widget."""
    value = field.default if field.default is not None else ""
    widget = ui.input(label=get_field_label(field), value=value)
    return widget.props("outlined type=date stack-label").classes("w-full")


def create_datetime_widget(field: FieldSpec):
    """Tarih-saat kutusu çizer (type=datetime-local). Parametre: field. Dönüş: widget."""
    value = field.default if field.default is not None else ""
    widget = ui.input(label=get_field_label(field), value=value)
    return widget.props("outlined type=datetime-local stack-label").classes("w-full")


class FileFieldState:
    """Bir dosya alanının yükleme durumunu tutar.

    Neden sınıf: upload olayı yalnızca olay nesnesini verir; hangi alana ait
    olduğunu bilmek için her alanın kendi nesnesi ve kendi handler metodu olur.
    """

    def __init__(self) -> None:
        self.saved_path = ""

    async def on_upload(self, event) -> None:
        """Yüklenen dosyayı data/uploads altına kaydeder ve yolunu saklar.

        Parametre: event - NiceGUI upload olayı (event.file). Dönüş: yok.
        """
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_name = uuid.uuid4().hex + "_" + sanitize_file_name(event.file.name)
        target_path = os.path.join(UPLOAD_FOLDER, file_name)
        # Neden önce temizlenir: kayıt başarısızsa eski yol sessizce kalmasın.
        self.saved_path = ""
        try:
            await event.file.save(target_path)
        except OSError as error:
            ui.notify(str(error), type="negative")
            return
        self.saved_path = target_path


def create_file_widget(field: FieldSpec, state: FileFieldState):
    """Dosya yükleme kutusu çizer.

    Parametreler: field - alan tarifi; state - yüklenen yolu tutacak nesne.
    Dönüş: widget.
    """
    widget = ui.upload(label=get_field_label(field), on_upload=state.on_upload, auto_upload=True)
    return widget.props("outlined flat bordered").classes("w-full")


class FormHandle:
    """Çizilmiş bir formun değerlerini okuma ve gönderme işlerini yapar."""

    def __init__(self, fields: list[FieldSpec]) -> None:
        self.fields = fields
        self.widgets = {}
        self.file_states = {}
        self.error_labels = {}

    def get_raw_values(self) -> dict:
        """Widget'lardaki güncel ham değerleri okur.

        Dönüş: {alan adı: ham değer}; dosya alanında kaydedilen yol ("" ise yüklenmemiş).
        """
        raw_values = {}
        for field in self.fields:
            if field.field_type == "file":
                raw_values[field.name] = self.file_states[field.name].saved_path
            else:
                raw_values[field.name] = self.widgets[field.name].value
        return raw_values

    def clear_errors(self) -> None:
        """Alanların altındaki eski hata mesajlarını siler. Dönüş: yok."""
        for label in self.error_labels.values():
            label.set_text("")
            label.set_visibility(False)

    def submit(self) -> tuple[dict, list[str]]:
        """Değerleri çevirir/doğrular ve hataları ilgili alanın altında gösterir.

        Dönüş: (çevrilmiş değerler, hata mesajları listesi).
        """
        self.clear_errors()
        values, errors_by_field = validate_by_field(self.fields, self.get_raw_values())
        for field_name, message in errors_by_field.items():
            label = self.error_labels[field_name]
            label.set_text(message)
            label.set_visibility(True)
        return values, list(errors_by_field.values())


def create_widget(field: FieldSpec, handle: FormHandle):
    """Alan tipine göre doğru create_<tip>_widget fonksiyonunu çağırır.

    Parametreler: field - alan tarifi; handle - dosya durumlarını saklayacak form.
    Dönüş: widget. Bilinmeyen tip metin kutusu olur.
    """
    field_type = field.field_type
    if field_type == "text":
        return create_text_widget(field)
    elif field_type == "password":
        return create_password_widget(field)
    elif field_type == "int" or field_type == "float":
        return create_number_widget(field)
    elif field_type == "bool":
        return create_bool_widget(field)
    elif field_type == "choice":
        return create_choice_widget(field)
    elif field_type == "multichoice":
        return create_multichoice_widget(field)
    elif field_type == "date":
        return create_date_widget(field)
    elif field_type == "datetime":
        return create_datetime_widget(field)
    elif field_type == "file":
        state = FileFieldState()
        handle.file_states[field.name] = state
        return create_file_widget(field, state)
    return create_str_widget(field)


def build_form(fields: list[FieldSpec]) -> FormHandle:
    """Çağrıldığı yerdeki NiceGUI bağlamına iki sütunlu bir form çizer.

    Parametre: fields - alan tarifleri. Dönüş: FormHandle.
    """
    handle = FormHandle(fields)
    with ui.grid(columns=2).classes("w-full gap-4"):
        for field in fields:
            if field.field_type in WIDE_TYPES:
                column_classes = "col-span-2 gap-0"
            else:
                column_classes = "gap-0"
            with ui.column().classes(column_classes + " w-full"):
                handle.widgets[field.name] = create_widget(field, handle)
                if field.help_text:
                    ui.label(field.help_text).classes("text-caption text-grey-7")
                error_label = ui.label("").classes("text-caption text-negative")
                error_label.set_visibility(False)
                handle.error_labels[field.name] = error_label
    return handle
