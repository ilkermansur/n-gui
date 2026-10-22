"""events.py - eklentilerin birbirini tanımadan haberleşmesi için olay yolu.

Kim kullanır: kernel ve eklentiler (subscribe / publish).
Nasıl bağlanır: kernel tek bir EventBus oluşturur; eklentiler olay adına
abone olur, başka bir yer aynı adla publish yapınca handler'lar çağrılır.
"""

import logging

logger = logging.getLogger(__name__)


class EventBus:
    """Olay adına göre handler listesi tutan basit yayın-abone sınıfı."""

    def __init__(self) -> None:
        """Boş bir handler sözlüğü oluşturur. Parametre ve dönüş yok."""
        self.handlers: dict[str, list] = {}

    def subscribe(self, event_name: str, handler) -> None:
        """Bir olaya handler ekler.

        Parametreler: event_name - olay adı; handler - data sözlüğü alan fonksiyon.
        Dönüş: yok.
        """
        if event_name not in self.handlers:
            self.handlers[event_name] = []
        self.handlers[event_name].append(handler)

    def publish(self, event_name: str, data: dict) -> None:
        """Olaya abone tüm handler'ları abone olma sırasıyla çağırır.

        Parametreler: event_name - olay adı; data - handler'lara verilen sözlük.
        Dönüş: yok. Bir handler hata verirse loglanır, diğerleri çalışmaya devam eder.
        """
        for handler in self.handlers.get(event_name, []):
            # Neden: tek bir bozuk handler bütün olay zincirini durdurmamalı.
            try:
                handler(data)
            except Exception:
                logger.exception("Olay handler'ı hata verdi: %s", event_name)
