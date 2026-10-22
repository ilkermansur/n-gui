"""Cihazdaki servisi yeniden başlatır.
---
title: {tr: Servis Yeniden Başlat, en: Restart Service}
section: Operation
group: Ürün A
mode: form
roles: [operator, admin]
timeout: 60
refresh: 30
schedule: "0 8 * * 1"
inputs:
  host: {type: str, label: Sunucu, required: true}
  port: {type: int, default: 22, min: 1, max: 65535}
  mode: {type: choice, options: [soft, hard]}
  start: {type: date}
---
"""


def run(host: str, port: int = 22, mode: str = "soft", start=None):
    return {"status": "ok"}
