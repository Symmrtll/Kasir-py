"""Pemformatan struk belanja dan penyimpanan riwayat transaksi."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .transaksi import ItemTransaksi, TransaksiSelesai

__all__ = ["format_struk", "RiwayatTransaksi", "DEFAULT_RIWAYAT_PATH"]

DEFAULT_RIWAYAT_PATH = Path(__file__).resolve().parent.parent / "data" / "riwayat.json"


def format_struk(transaksi: TransaksiSelesai) -> str:
    """Buat teks struk dari snapshot transaksi yang sudah selesai."""
    garis = "-" * 40
    baris = [
        garis,
        "          TOKO SERBA ADA",
        "           STRUK BELANJA",
        garis,
        f"Waktu   : {transaksi.waktu}",
        garis,
    ]
    for item in transaksi.items:
        baris.append(f"{item.nama} ({item.kode})")
        baris.append(f"  {item.qty} x Rp{item.harga_satuan} = Rp{item.subtotal}")
    baris.extend(
        [
            garis,
            f"Jumlah item   : {transaksi.jumlah_item}",
            f"Subtotal      : Rp{transaksi.subtotal}",
            f"Total         : Rp{transaksi.total}",
            f"Uang bayar    : Rp{transaksi.uang_bayar}",
            f"Kembalian     : Rp{transaksi.kembalian}",
            garis,
            "Terima kasih telah berbelanja!",
            garis,
        ]
    )
    return "\n".join(baris)


class RiwayatTransaksi:
    """Riwayat di memori dengan opsi simpan/muat ke file JSON."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_RIWAYAT_PATH
        self._data: list[TransaksiSelesai] = []
        self._muat()

    def _muat(self) -> None:
        """Muat riwayat lama bila file sudah ada."""
        if not self.path.exists():
            return
        for item in json.loads(self.path.read_text(encoding="utf-8")):
            items = tuple(ItemTransaksi(**i) for i in item.pop("items"))
            self._data.append(TransaksiSelesai(items=items, **item))

    def tambah(self, transaksi: TransaksiSelesai) -> None:
        """Tambahkan transaksi selesai ke riwayat (belum ditulis ke disk)."""
        self._data.append(transaksi)

    def semua(self) -> list[TransaksiSelesai]:
        """Kembalikan salinan daftar riwayat."""
        return list(self._data)

    def simpan(self) -> None:
        """Tulis seluruh riwayat ke file JSON UTF-8."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(trx) for trx in self._data]
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def catat(self, transaksi: TransaksiSelesai) -> None:
        """Tambah transaksi sekaligus simpan riwayat ke disk."""
        self.tambah(transaksi)
        self.simpan()
