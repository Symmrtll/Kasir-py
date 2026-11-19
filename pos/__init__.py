"""Package logika bisnis aplikasi kasir (POS).

Modul di dalam package ini sengaja tidak memanggil input()/print().
Seluruh interaksi dengan pengguna berada di ``main.py``.
"""

from . import katalog, struk, transaksi, validasi

__version__ = "0.2.0"

__all__ = [
    "katalog",
    "transaksi",
    "struk",
    "validasi",
]
