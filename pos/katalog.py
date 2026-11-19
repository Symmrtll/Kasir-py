"""Katalog produk: pencarian berdasarkan kode, cek stok, dan pengurangan stok."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

__all__ = [
    "Produk",
    "Katalog",
    "ProdukTidakDitemukanError",
    "StokTidakCukupError",
    "normalisasi_kode",
    "DEFAULT_PATH",
    "DEFAULT_DATA_PATH",
]

#: Data benih (stok awal), tidak pernah ditulis oleh aplikasi.
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "produk_awal.json"
#: File kerja yang menyimpan stok terkini antar sesi aplikasi.
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "produk.json"


def normalisasi_kode(kode: str) -> str:
    """Kembalikan kode barang dalam bentuk bersih dan huruf kapital."""
    return kode.strip().upper()


class ProdukTidakDitemukanError(LookupError):
    """Dilempar saat kode barang tidak ada di katalog."""


class StokTidakCukupError(ValueError):
    """Dilempar saat jumlah yang diminta melebihi stok tersedia."""


@dataclass
class Produk:
    """Satu barang dagangan; stok bersifat mutable dan diubah saat checkout."""

    kode: str
    nama: str
    harga: int
    stok: int

    def __post_init__(self) -> None:
        self.kode = normalisasi_kode(self.kode)
        self.harga = int(self.harga)
        self.stok = int(self.stok)


class Katalog:
    """Kumpulan produk yang diindeks memakai kode ternormalisasi."""

    def __init__(
        self,
        produk: Iterable[Mapping[str, object]] | None = None,
        path: str | Path | None = None,
    ) -> None:
        """Muat dari daftar dict, atau dari file kerja/seed bila tidak diberikan.

        Prioritas sumber saat ``produk`` tidak diberikan: file kerja (``path``
        atau ``DEFAULT_DATA_PATH``) jika ada, otherwise ``produk_awal.json``.
        """
        self._sumber_path: Path | None = DEFAULT_PATH
        self._path: Path | None = None

        if produk is not None:
            self._sumber_path = None
            self._path = Path(path) if path is not None else None
            self._isi_dari(produk)
            return

        self._path = Path(path) if path is not None else DEFAULT_DATA_PATH
        sumber = self._path if self._path.exists() else DEFAULT_PATH
        self._isi_dari(json.loads(sumber.read_text(encoding="utf-8")))

    def _isi_dari(self, sumber: Iterable[Mapping[str, object]]) -> None:
        """Isi ulang indeks katalog dari iterable berisi dict produk."""
        self._produk: dict[str, Produk] = {}
        for item in sumber:
            p = Produk(
                kode=str(item["kode"]),
                nama=str(item["nama"]),
                harga=int(item["harga"]),
                stok=int(item["stok"]),
            )
            self._produk[p.kode] = p

    def cari(self, kode: str) -> Produk | None:
        """Cari produk berdasarkan kode; None jika tidak ditemukan."""
        return self._produk.get(normalisasi_kode(kode))

    def wajib_cari(self, kode: str) -> Produk:
        """Seperti ``cari``, tetapi melempar error jika tidak ditemukan."""
        produk = self.cari(kode)
        if produk is None:
            raise ProdukTidakDitemukanError(
                f"Kode '{normalisasi_kode(kode)}' tidak ditemukan."
            )
        return produk

    def semua(self) -> list[Produk]:
        """Kembalikan daftar seluruh produk (urutan sesuai sumber data)."""
        return list(self._produk.values())

    def cek_stok(self, kode: str, qty: int) -> bool:
        """True jika produk ada dan stoknya mencukupi untuk ``qty``."""
        produk = self.cari(kode)
        return produk is not None and qty <= produk.stok

    def kurangi_stok(self, kode: str, qty: int) -> None:
        """Kurangi stok setelah validasi; tidak mengubah apa pun jika gagal."""
        if qty <= 0:
            raise ValueError("Jumlah pengurangan stok harus lebih dari 0.")
        produk = self.wajib_cari(kode)
        if qty > produk.stok:
            raise StokTidakCukupError(
                f"Stok {produk.nama} hanya {produk.stok}, diminta {qty}."
            )
        produk.stok -= qty

    def ke_dict(self) -> list[dict[str, object]]:
        """Kembalikan katalog sebagai daftar dict siap diserialisasi JSON."""
        return [
            {
                "kode": p.kode,
                "nama": p.nama,
                "harga": p.harga,
                "stok": p.stok,
            }
            for p in self._produk.values()
        ]

    def simpan(self, path: str | Path | None = None) -> Path:
        """Tulis stok terkini ke file kerja dan kembalikan path tujuannya."""
        tujuan = Path(path) if path is not None else self._path
        if tujuan is None:
            raise RuntimeError("Katalog tidak memiliki file tujuan untuk disimpan.")
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        tujuan.write_text(
            json.dumps(self.ke_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return tujuan

    def reset(self, sumber: str | Path | None = None) -> None:
        """Kembalikan stok ke data awal lalu simpan ke file kerja."""
        asal = Path(sumber) if sumber is not None else (self._sumber_path or DEFAULT_PATH)
        self._isi_dari(json.loads(asal.read_text(encoding="utf-8")))
        self.simpan()
