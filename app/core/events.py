"""events.py - eklentilerin birbirini tanimadan haberlesmesi icin olay yolu.

Kim kullanir: kernel ve eklentiler (subscribe / publish).
Nasil baglanir: kernel tek bir EventBus olusturur; eklentiler olay adina
abone olur, baska bir yer ayni adla publish yapinca handler'lar cagrilir.
"""

import logging

logger = logging.getLogger(__name__)


class EventBus:
    """Olay adina gore handler listesi tutan basit yayin-abone sinifi."""

    def __init__(self) -> None:
        """Bos bir handler sozlugu olusturur. Parametre ve donus yok."""
        self.handlers: dict[str, list] = {}

    def subscribe(self, event_name: str, handler) -> None:
        """Bir olaya handler ekler.

        Parametreler: event_name - olay adi; handler - data sozlugu alan fonksiyon.
        Donus: yok.
        """
        if event_name not in self.handlers:
            self.handlers[event_name] = []
        self.handlers[event_name].append(handler)

    def publish(self, event_name: str, data: dict) -> None:
        """Olaya abone tum handler'lari abone olma sirasiyla cagirir.

        Parametreler: event_name - olay adi; data - handler'lara verilen sozluk.
        Donus: yok. Bir handler hata verirse loglanir, digerleri calismaya devam eder.
        """
        for handler in self.handlers.get(event_name, []):
            # Neden: tek bir bozuk handler butun olay zincirini durdurmamali.
            try:
                handler(data)
            except Exception:
                logger.exception("Olay handler'i hata verdi: %s", event_name)
