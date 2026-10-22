"""Sunucu için günlük özet raporu üretir.

Disk doluluğu, sistem yükü, işlemci sayısı ve Python sürümünü tablo satırları
olarak döndürür. Her satırda değerin "normal" ya da "uyarı" durumu yazar.
Zamanlanmış modda çalışır (her gün 08:00); sayfadan elle de çalıştırılabilir ve
geçmiş raporlar listelenir. Yalnızca Python standart kütüphanesini kullanır.
---
title: {tr: Günlük Özet, en: Daily Summary}
section: Report
mode: scheduled
roles: [admin, operator, viewer]
timeout: 30
schedule: "0 8 * * *"
inputs:
  disk_esigi: {type: int, label: {tr: Disk uyarı eşiği (%), en: Disk warning threshold (%)}, default: 80, min: 1, max: 100}
---
"""

import os
import platform
import shutil
from datetime import datetime


def make_row(item: str, value, is_warning: bool) -> dict:
    """Rapor tablosu için tek bir satır sözlüğü üretir."""
    if is_warning:
        status = "uyarı"
    else:
        status = "normal"
    return {"kalem": item, "deger": value, "durum": status}


def run(disk_esigi: int = 80):
    """Özet satırlarını (sözlük listesi) döndürür; liste sayfada tablo olarak görünür."""
    rows = []

    disk = shutil.disk_usage("/")
    used_percent = round(disk.used * 100 / disk.total, 1)
    rows.append(make_row("Disk doluluğu (%)", used_percent, used_percent >= disk_esigi))

    cpu_count = os.cpu_count() or 1
    # getloadavg yalnızca macOS/Linux'ta vardır; yoksa satır "bilinmiyor" yazar.
    if hasattr(os, "getloadavg"):
        load_1_minute = round(os.getloadavg()[0], 2)
        rows.append(make_row("Sistem yükü (1 dk)", load_1_minute, load_1_minute > cpu_count))
    else:
        rows.append(make_row("Sistem yükü (1 dk)", "bilinmiyor", False))

    rows.append(make_row("CPU sayısı", cpu_count, False))
    rows.append(make_row("Python sürümü", platform.python_version(), False))
    rows.append(make_row("Rapor zamanı", datetime.now().strftime("%Y-%m-%d %H:%M"), False))
    return rows
