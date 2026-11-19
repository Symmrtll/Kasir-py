"""Manajemen keranjang, perhitungan total, dan penyelesaian transaksi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .katalog import Katalog, StokTidakCukupError, normalisasi_kode
from .validasi import validasi_pembayaran as cek_pembayaran

__all__ = [
    "ItemKeranjang",
    "Keranjang",
    "Transaksi",
    "ItemTransaksi",
    "TransaksiSelesai",
    "KeranjangKosongError",
    "ItemTidakAdaError",
    "PembayaranError",
    "TransaksiSelesaiError",
]


class KeranjangKosongError(ValueError):
    """Dilempar saat transaksi diselesaikan tanpa item."""


class ItemTidakAdaError(LookupError):
    """Dilempar saat kode yang dihapus tidak ada di keranjang."""


class PembayaranError(ValueError):
    """Dilempar saat uang bayar kurang atau tidak valid."""


class TransaksiSelesaiError(RuntimeError):
    """Dilempar saat keranjang diubah setelah transaksi selesai."""


@dataclass
class ItemKeranjang:
    """Item keranjang; nama & harga disalin dari katalog saat ditambahkan."""

    kode: str
    nama: str
    harga_satuan: int
    qty: int

    @property
    def subtotal(self) -> int:
        """Subtotal item dalam Rupiah bulat."""
        return self.harga_satuan * self.qty


class Keranjang:
    """Kumpulan item dengan penggabungan duplikat dan pengecekan stok."""

    def __init__(self, katalog: Katalog) -> None:
        self._katalog = katalog
        self._item: dict[str, ItemKeranjang] = {}

    def tambah(self, kode: str, qty: int) -> ItemKeranjang:
        """Tambah item; gabungkan kode sama bila total qty masih sesuai stok."""
        if qty <= 0:
            raise ValueError("Jumlah harus lebih dari 0.")
        produk = self._katalog.wajib_cari(kode)
        kode_normal = produk.kode
        sudah = self._item.get(kode_normal)
        total_qty = qty + (sudah.qty if sudah is not None else 0)

        if total_qty > produk.stok:
            raise StokTidakCukupError(
                f"Stok {produk.nama} hanya {produk.stok}, diminta {total_qty}."
            )

        if sudah is None:
            item = ItemKeranjang(
                kode=kode_normal,
                nama=produk.nama,
                harga_satuan=produk.harga,
                qty=qty,
            )
            self._item[kode_normal] = item
            return item

        sudah.qty = total_qty
        return sudah

    def hapus(self, kode: str) -> ItemKeranjang:
        """Hapus satu kode dari keranjang; kembalikan item yang dihapus."""
        kode_normal = normalisasi_kode(kode)
        item = self._item.pop(kode_normal, None)
        if item is None:
            raise ItemTidakAdaError(
                f"Kode '{kode_normal}' tidak ada di keranjang."
            )
        return item

    def semua(self) -> list[ItemKeranjang]:
        """Kembalikan salinan nilai item sesuai urutan penambahan."""
        return [
            ItemKeranjang(
                kode=i.kode,
                nama=i.nama,
                harga_satuan=i.harga_satuan,
                qty=i.qty,
            )
            for i in self._item.values()
        ]

    @property
    def subtotal(self) -> int:
        """Jumlah seluruh subtotal item."""
        return sum(i.subtotal for i in self._item.values())

    @property
    def kosong(self) -> bool:
        """True jika keranjang tidak berisi item."""
        return not self._item

    def kosongkan(self) -> None:
        """Hapus seluruh item dari keranjang."""
        self._item.clear()


@dataclass(frozen=True)
class ItemTransaksi:
    """Snapshot permanen satu item saat transaksi selesai."""

    kode: str
    nama: str
    harga_satuan: int
    qty: int
    subtotal: int


@dataclass(frozen=True)
class TransaksiSelesai:
    """Snapshot transaksi untuk struk dan riwayat."""

    waktu: str
    items: tuple[ItemTransaksi, ...]
    subtotal: int
    total: int
    uang_bayar: int
    kembalian: int

    @property
    def jumlah_item(self) -> int:
        """Total quantity seluruh barang yang dibeli."""
        return sum(i.qty for i in self.items)


class Transaksi:
    """Satu sesi belanja: tambah item, bayar, lalu selesaikan."""

    def __init__(self, katalog: Katalog) -> None:
        self._katalog = katalog
        self.keranjang = Keranjang(katalog)
        self.selesai: bool = False

    def tambah_item(self, kode: str, qty: int) -> ItemKeranjang:
        """Tambah barang ke keranjang (belum mengubah stok katalog)."""
        if self.selesai:
            raise TransaksiSelesaiError("Transaksi ini sudah selesai.")
        return self.keranjang.tambah(kode, qty)

    def hapus_item(self, kode: str) -> ItemKeranjang:
        """Hapus barang dari keranjang (stok katalog tidak berubah)."""
        if self.selesai:
            raise TransaksiSelesaiError("Transaksi ini sudah selesai.")
        return self.keranjang.hapus(kode)

    @property
    def subtotal(self) -> int:
        """Subtotal keranjang sebelum pembayaran."""
        return self.keranjang.subtotal

    @property
    def total(self) -> int:
        """Total yang harus dibayar (saat ini sama dengan subtotal)."""
        return self.subtotal

    def validasi_pembayaran(self, uang_bayar: int) -> int:
        """Cek uang bayar dan kembalikan kembalian tanpa efek samping."""
        if self.keranjang.kosong:
            raise KeranjangKosongError("Keranjang masih kosong.")
        try:
            return cek_pembayaran(uang_bayar, self.total)
        except ValueError as exc:
            raise PembayaranError(str(exc)) from exc

    def selesaikan(self, uang_bayar: int) -> TransaksiSelesai:
        """Validasi dulu, baru kurangi stok dan hasilkan snapshot transaksi."""
        if self.selesai:
            raise TransaksiSelesaiError("Transaksi ini sudah selesai.")
        kembalian = self.validasi_pembayaran(uang_bayar)

        # Snapshot dibuat lebih dulu dari nilai salinan, sehingga perubahan
        # nama/harga katalog di kemudian hari tidak memengaruhi riwayat.
        snapshot_item = tuple(
            ItemTransaksi(
                kode=i.kode,
                nama=i.nama,
                harga_satuan=i.harga_satuan,
                qty=i.qty,
                subtotal=i.subtotal,
            )
            for i in self.keranjang.semua()
        )
        subtotal = sum(i.subtotal for i in snapshot_item)
        total = subtotal

        # Cek seluruh stok lebih dulu agar pengurangan bersifat all-or-nothing.
        for item in snapshot_item:
            if not self._katalog.cek_stok(item.kode, item.qty):
                sisa = self._katalog.wajib_cari(item.kode).stok
                raise StokTidakCukupError(
                    f"Stok {item.nama} berubah, tersisa {sisa}."
                )

        for item in snapshot_item:
            self._katalog.kurangi_stok(item.kode, item.qty)

        hasil = TransaksiSelesai(
            waktu=datetime.now().isoformat(timespec="seconds"),
            items=snapshot_item,
            subtotal=subtotal,
            total=total,
            uang_bayar=uang_bayar,
            kembalian=kembalian,
        )
        self.keranjang.kosongkan()
        self.selesai = True
        return hasil
