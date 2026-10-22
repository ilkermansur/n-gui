"""field_spec.py - form alanlarını tarif eden ortak veri tipi.

Kim kullanır: script yükleyici ve form çizen arayüz kodu.
Nasıl bağlanır: bir script'in her parametresi bir FieldSpec olarak tanımlanır;
arayüz bu tarife bakarak uygun giriş kutusunu çizer.
"""

from dataclasses import dataclass, field


@dataclass
class FieldSpec:
    """Tek bir form alanının tarifi."""

    name: str
    field_type: str = "str"
    label_tr: str = ""
    label_en: str = ""
    required: bool = False
    default: object = None
    options: list = field(default_factory=list)
    min_value: object = None
    max_value: object = None
    help_text: str = ""
