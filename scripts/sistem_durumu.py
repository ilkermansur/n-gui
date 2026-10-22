"""Sunucunun anlık durumunu gösterir: işlemci sayısı, disk doluluğu ve saat.

Bu script "canlı" modda çalışır: sayfa açık kaldıkça her `refresh` saniyede bir
yeniden çalıştırılır ve kartlar güncellenir. Yalnızca Python standart
kütüphanesini kullanır; girdi almaz.
---
title: {tr: Sistem Durumu, en: System Status}
section: Dashboard
mode: live
roles: [admin, operator, viewer]
timeout: 10
refresh: 15
---
"""

import os
import shutil
from datetime import datetime


def run():
    """Durum bilgisini sözlük olarak döndürür (her anahtar bir kart olur)."""
    # Kök dizinin bulunduğu diskin kullanımı (bayt cinsinden).
    disk = shutil.disk_usage("/")
    used_percent = round(disk.used * 100 / disk.total, 1)
    free_gb = round(disk.free / (1024 ** 3), 1)
    return {
        "CPU sayısı": os.cpu_count(),
        "Disk doluluğu (%)": used_percent,
        "Boş disk (GB)": free_gb,
        "Saat": datetime.now().strftime("%H:%M:%S"),
    }
