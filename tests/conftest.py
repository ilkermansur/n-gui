"""conftest.py - bütün testler için ortak pytest ayarı.

Kim kullanır: pytest (kendiliğinden yüklenir).
Nasıl bağlanır: "e2e" işaretli testler tarayıcı ve çalışan bir uygulama ister; bu yüzden
yalnızca NGUI_E2E=1 ortam değişkeni verildiğinde çalışır, aksi halde atlanır.
"""

import os

import pytest


def pytest_collection_modifyitems(config, items) -> None:
    """NGUI_E2E=1 değilse "e2e" işaretli testleri atlanmış olarak işaretler."""
    if os.environ.get("NGUI_E2E") == "1":
        return
    skip_marker = pytest.mark.skip(reason="uçtan uca testler için NGUI_E2E=1 verin")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_marker)
