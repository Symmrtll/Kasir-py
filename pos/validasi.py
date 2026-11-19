"""Validasi dan normalisasi input pengguna.

Fungsi di sini murni: menerima nilai mentah, mengembalikan nilai valid,
atau melempar ValueError. Tidak ada input()/print() di modul ini.
"""

from __future__ import annotations

from .katalog import normalisasi_kode

__all__ = [
    "validasi_kode",
    "validasi_qty",
    "validasi_uang_bayar",
    "validasi_pembayaran",
]


def validasi_kode(kode: str) -> str:
    """Normalisasi kode barang dan tolak nilai kosong."""
    hasil = normalisasi_kode(kode)
    if not hasil:
        raise ValueError("Kode barang tidak boleh kosong.")
    return hasil


def _ke_bulat(teks: object, nama: str) -> int:
    """Ubah teks menjadi int; tangkap ValueError agar pesannya ramah."""
    try:
        return int(str(teks).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{nama} harus berupa bilangan bulat.") from None


def validasi_qty(teks: object) -> int:
    """Ubah input menjadi jumlah barang bulat yang lebih dari 0."""
    qty = _ke_bulat(teks, "Jumlah")
    if qty <= 0:
        raise ValueError("Jumlah harus lebih dari 0.")
    return qty


def validasi_uang_bayar(teks: object) -> int:
    """Ubah input menjadi uang bayar bulat yang tidak negatif."""
    uang = _ke_bulat(teks, "Uang bayar")
    if uang < 0:
        raise ValueError("Uang bayar tidak boleh negatif.")
    return uang


def validasi_pembayaran(uang_bayar: int, total: int) -> int:
    """Pastikan uang mencukupi lalu kembalikan kembalian (int Rupiah)."""
    if uang_bayar < 0:
        raise ValueError("Uang bayar tidak boleh negatif.")
    if uang_bayar < total:
        raise ValueError(
            f"Uang bayar kurang Rp{total - uang_bayar} (total Rp{total})."
        )
    return uang_bayar - total
