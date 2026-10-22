"""text.py - çeviri yardımcısı t().

Kim kullanır: arayüz kodu ve eklentiler (metin göstermek için).
Nasıl bağlanır: kernel'de "i18n" servisi varsa çeviriyi ona yaptırır;
yoksa (örneğin testlerde) anahtarın kendisini döndürür.
"""

from app.core import kernel as kernel_module


def t(key: str, **values) -> str:
    """Anahtarın çevirisini döndürür.

    Parametreler: key - çeviri anahtarı; values - metindeki yer tutucu değerleri.
    Dönüş: çevrilmiş metin; kernel ya da i18n servisi yoksa key.
    """
    # Neden doğrudan alan okunur: get_kernel() hazır değilken hata fırlatır.
    kernel = kernel_module.current_kernel
    if kernel is None:
        return key
    i18n = kernel.get_service("i18n")
    if i18n is None:
        return key
    return i18n.t(key, **values)
