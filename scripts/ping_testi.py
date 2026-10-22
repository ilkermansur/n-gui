"""Bir sunucuya ping atarak ağ erişimini test eder.

Verilen adrese `ping -c <adet>` komutu gönderilir (macOS ve Linux). Sonuçta
sunucu adı, testin başarılı olup olmadığı, paket kaybı ve ortalama süre kart
olarak döner; ping'in tam çıktısı "Çıktı" bölümünde görünür. Yalnızca Python standart kütüphanesini kullanır.
---
title: {tr: Ping Testi, en: Ping Test}
section: Operation
group: Ağ
mode: form
roles: [operator, admin]
timeout: 30
inputs:
  host: {type: str, label: {tr: Sunucu adresi, en: Host}, required: true, help: "Örnek: 8.8.8.8 veya example.com"}
  count: {type: int, label: {tr: Paket sayısı, en: Packet count}, default: 3, min: 1, max: 10}
---
"""

import subprocess


def run(host: str, count: int = 3):
    """host adresine count adet ping gönderir ve sonucu sözlük olarak döndürür."""
    # Neden kontrol: "-" ile başlayan bir metin adres değil ping seçeneği sayılırdı.
    if host.strip() == "" or host.startswith("-"):
        raise ValueError("Geçersiz sunucu adresi: " + host)
    # Neden liste ile: komut kabuk (shell) üzerinden çalışmaz; adres alanına
    # yazılan "; rm ..." gibi metinler komut olarak yorumlanamaz.
    command = ["ping", "-c", str(count), host]
    try:
        # Her paket için yaklaşık 1 saniye + pay; takılırsa kısa sürede vazgeçilir.
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=count * 2 + 5
        )
    except subprocess.TimeoutExpired:
        print("Ping zaman aşımına uğradı")
        return {"Sunucu": host, "Başarılı": False, "Paket kaybı": "-", "Ortalama (ms)": "-"}
    except FileNotFoundError:
        print("ping komutu bulunamadı")
        return {"Sunucu": host, "Başarılı": False, "Paket kaybı": "-", "Ortalama (ms)": "-"}

    output_text = (completed.stdout + completed.stderr).strip()
    # Tam çıktı script çıktısı olarak sayfadaki "Çıktı" bölümünde görünür.
    print(output_text)

    return {
        "Sunucu": host,
        "Başarılı": completed.returncode == 0,
        "Paket kaybı": find_packet_loss(output_text),
        "Ortalama (ms)": find_average_ms(output_text),
    }


def find_packet_loss(output_text: str) -> str:
    """Ping çıktısındaki paket kaybı yüzdesini bulur (örn. "0.0%"); yoksa "-"."""
    for line in output_text.splitlines():
        if "packet loss" in line:
            for part in line.split(","):
                if "packet loss" in part:
                    return part.replace("packet loss", "").strip()
    return "-"


def find_average_ms(output_text: str) -> str:
    """Ping çıktısındaki ortalama gidiş-dönüş süresini (ms) bulur; yoksa "-".

    Satır örneği: "round-trip min/avg/max/stddev = 0.09/0.11/0.13/0.02 ms"
    (Linux'ta "rtt min/avg/max/mdev = ..."). İkinci sayı ortalamadır.
    """
    for line in output_text.splitlines():
        if "min/avg/max" in line and "=" in line:
            numbers = line.split("=")[1].strip().split(" ")[0].split("/")
            if len(numbers) >= 2:
                return numbers[1]
    return "-"
