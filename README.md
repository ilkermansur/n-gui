# N-GUI

Moduler NiceGUI web kabugu: kucuk bir cekirdek (`app/core`) ve eklenti klasorleri (`plugins/<ad>/`).

## Kurulum

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Calistirma

Ayarlar `config.toml` dosyasindadir (baslik, port, veritabani, devre disi eklentiler).
Uygulama giris noktasi sonraki gorevlerde eklenecektir.

## Test

```bash
.venv/bin/pytest
```
