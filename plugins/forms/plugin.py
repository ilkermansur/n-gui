"""plugin.py - forms eklentisi: alan şemasından form üretimi.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: "forms" servisini kaydeder; servis build_form ile form çizer,
convert_and_validate ile UI'sız doğrulama yapar. Script motoru bu servisi kullanır.
"""

from app.core.plugin import Plugin
from plugins.forms.builder import FormHandle, build_form, discard_uploaded_file
from plugins.forms.validation import convert_and_validate


class FormsService:
    """Diğer eklentilere sunulan form servisi."""

    def build_form(self, fields: list) -> FormHandle:
        """Geçerli NiceGUI bağlamına form çizer. Parametre: fields. Dönüş: FormHandle."""
        return build_form(fields)

    def convert_and_validate(self, fields: list, raw_values: dict) -> tuple[dict, list[str]]:
        """UI'sız doğrulama. Parametreler: fields, raw_values. Dönüş: (değerler, hatalar)."""
        return convert_and_validate(fields, raw_values)

    def discard_uploaded_file(self, path: str) -> bool:
        """Dosya alanına yüklenmiş dosyayı siler (yalnızca data/uploads içindekileri).

        Kim kullanır: script motoru, çalıştırma bittikten sonra. Dönüş: silindiyse True.
        """
        return discard_uploaded_file(path)


class FormsPlugin(Plugin):
    """Form üretim eklentisi."""

    plugin_id = "forms"
    name = "forms"
    version = "1.0"
    # Neden boş: i18n yoksa etiketler label_tr'ye, mesajlar anahtara düşer.
    requires = []

    def setup(self, kernel) -> None:
        """Servisi kaydeder. Parametre: kernel - çekirdek. Dönüş: yok."""
        kernel.register_service("forms", FormsService())
