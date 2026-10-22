# N-GUI

Modüler NiceGUI web kabuğu: küçük bir çekirdek (`app/core`) ve eklenti klasörleri (`plugins/<ad>/`).

## Kurulum

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Çalıştırma

Ayarlar `config.toml` dosyasındadır (başlık, port, veritabanı, devre dışı eklentiler).
Uygulama giriş noktası sonraki görevlerde eklenecektir.

## Test

```bash
.venv/bin/pytest
```
