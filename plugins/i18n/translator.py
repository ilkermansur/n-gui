"""translator.py - çeviri servisi (Translator sınıfı).

Kim kullanır: i18n eklentisi bu sınıfı "i18n" servisi olarak kaydeder;
app/core/text.py içindeki t() ve layout.py (dil düğmesi) bu servisi çağırır.
Nasıl bağlanır: JSON dosyalarındaki çeviriler belleğe yüklenir. Aktif dil
Translator nesnesinde DEĞİL, her kullanıcının oturumunda
(app.storage.user["language"]) saklanır; böylece her kullanıcı kendi dilini görür.
"""

import json
import os

from nicegui import app

# Neden sabit: bir anahtar seçili dilde yoksa her zaman İngilizceye bakılır.
FALLBACK_LANGUAGE = "en"


class Translator:
    """Çevirileri tutar ve anahtarları aktif dile çevirir."""

    def __init__(self, default_language: str) -> None:
        """Boş çeviri tablosuyla başlar.

        Parametre: default_language - oturumda dil yoksa kullanılacak dil ("tr").
        Dönüş: yok.
        """
        self.default_language = default_language
        # Yapı: {"tr": {"anahtar": "metin"}, "en": {...}}
        self.entries: dict[str, dict[str, str]] = {}

    def add_translations(self, language: str, entries: dict) -> None:
        """Bir dile çeviri ekler; aynı anahtar varsa üzerine yazar.

        Parametreler: language - dil kodu; entries - {anahtar: metin} sözlüğü.
        Dönüş: yok.
        """
        if language not in self.entries:
            self.entries[language] = {}
        self.entries[language].update(entries)

    def load_folder(self, folder: str) -> None:
        """Klasördeki tr.json ve en.json dosyalarını yükler.

        Parametre: folder - JSON dosyalarının bulunduğu klasör.
        Dönüş: yok. Dosya yoksa o dil sessizce atlanır.
        """
        for language in ("tr", "en"):
            file_path = os.path.join(folder, language + ".json")
            if not os.path.isfile(file_path):
                continue
            with open(file_path, encoding="utf-8") as json_file:
                entries = json.load(json_file)
            self.add_translations(language, entries)

    def translate(self, key: str, language: str, **values) -> str:
        """Anahtarı verilen dile çevirir.

        Parametreler: key - çeviri anahtarı; language - dil kodu;
        values - metindeki {yer_tutucu} değerleri.
        Dönüş: çevrilmiş metin. Sıra: istenen dil, sonra en, sonra anahtarın kendisi.
        """
        text = self.entries.get(language, {}).get(key)
        if text is None:
            text = self.entries.get(FALLBACK_LANGUAGE, {}).get(key)
        if text is None:
            return key

        # Neden try: eksik yer tutucu değeri sayfayı çökertmemeli, ham metin yeter.
        try:
            return text.format(**values)
        except (KeyError, IndexError, ValueError):
            return text

    def get_language(self) -> str:
        """Aktif kullanıcının dilini döndürür.

        Dönüş: oturumdaki dil; oturum yoksa ya da dil seçilmemişse varsayılan dil.
        """
        # Neden try: istek bağlamı dışında (testler, başlangıç) app.storage.user RuntimeError verir.
        try:
            language = app.storage.user.get("language")
        except RuntimeError:
            return self.default_language
        if not language:
            return self.default_language
        return language

    def set_language(self, language: str) -> None:
        """Aktif kullanıcının dilini oturuma yazar.

        Parametre: language - dil kodu. Dönüş: yok. İstek bağlamı dışında hiçbir şey yapmaz.
        """
        try:
            app.storage.user["language"] = language
        except RuntimeError:
            return

    def t(self, key: str, **values) -> str:
        """Anahtarı aktif dile çevirir (app/core/text.py içindeki t() bunu çağırır).

        Parametreler: key - çeviri anahtarı; values - yer tutucu değerleri.
        Dönüş: çevrilmiş metin.
        """
        return self.translate(key, self.get_language(), **values)

    def pick(self, text_tr: str, text_en: str) -> str:
        """Aktif dile göre iki metinden birini seçer.

        Parametreler: text_tr - Türkçe metin; text_en - İngilizce metin.
        Dönüş: seçilen metin; seçilen boşsa diğeri.
        """
        if self.get_language() == "tr":
            chosen, other = text_tr, text_en
        else:
            chosen, other = text_en, text_tr
        if chosen:
            return chosen
        return other
