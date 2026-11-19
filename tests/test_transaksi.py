"""Unit test logika inti: keranjang, stok, total, dan pembayaran."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Agar file ini juga bisa dijalankan langsung: python tests/test_transaksi.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pos.katalog import Katalog, ProdukTidakDitemukanError, StokTidakCukupError  # noqa: E402
from pos.struk import RiwayatTransaksi, format_struk  # noqa: E402
from pos.transaksi import (  # noqa: E402
    ItemTidakAdaError,
    KeranjangKosongError,
    PembayaranError,
    Transaksi,
)
from pos.validasi import (  # noqa: E402
    validasi_kode,
    validasi_pembayaran,
    validasi_qty,
    validasi_uang_bayar,
)

PRODUK_AWAL = [
    {"kode": "a01", "nama": "Kopi Hitam", "harga": 5000, "stok": 5},
    {"kode": "B02", "nama": "Air Mineral", "harga": 3000, "stok": 2},
]


class TransaksiTest(unittest.TestCase):
    """Pengujian untuk alur keranjang hingga penyelesaian transaksi."""

    def setUp(self) -> None:
        self.katalog = Katalog(PRODUK_AWAL)
        self.trx = Transaksi(self.katalog)

    def test_normalisasi_kode_barang(self) -> None:
        self.assertEqual(validasi_kode("  a01 "), "A01")
        with self.assertRaises(ValueError):
            validasi_kode("   ")

    def test_validasi_qty_menolak_nilai_invalid(self) -> None:
        for nilai in ["0", "-1", "abc", ""]:
            with self.subTest(nilai=nilai), self.assertRaises(ValueError):
                validasi_qty(nilai)
        self.assertEqual(validasi_qty(" 3 "), 3)

    def test_validasi_uang_dan_pembayaran(self) -> None:
        self.assertEqual(validasi_uang_bayar("10000"), 10000)
        with self.assertRaises(ValueError):
            validasi_uang_bayar("-1")
        with self.assertRaises(ValueError):
            validasi_pembayaran(4000, 5000)
        self.assertEqual(validasi_pembayaran(7000, 5000), 2000)

    def test_tambah_item_dan_total_bilangan_bulat(self) -> None:
        self.trx.tambah_item("a01", 2)
        self.assertEqual(self.trx.subtotal, 10000)
        self.assertEqual(self.trx.total, 10000)
        self.assertIsInstance(self.trx.total, int)

    def test_gabung_item_duplikat(self) -> None:
        self.trx.tambah_item("A01", 2)
        self.trx.tambah_item(" a01 ", 3)
        items = self.trx.keranjang.semua()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].qty, 5)
        self.assertEqual(self.trx.total, 25000)

    def test_gabung_melebihi_stok_tidak_mengubah_keranjang(self) -> None:
        self.trx.tambah_item("B02", 1)
        with self.assertRaises(StokTidakCukupError):
            self.trx.tambah_item("B02", 2)
        self.assertEqual(self.trx.keranjang.semua()[0].qty, 1)
        self.assertEqual(self.katalog.cari("B02").stok, 2)

    def test_produk_tidak_ditemukan(self) -> None:
        with self.assertRaises(ProdukTidakDitemukanError):
            self.trx.tambah_item("XXX", 1)

    def test_hapus_item_dari_keranjang(self) -> None:
        self.trx.tambah_item("A01", 2)
        self.trx.tambah_item("B02", 1)
        dihapus = self.trx.hapus_item(" a01 ")
        self.assertEqual(dihapus.nama, "Kopi Hitam")
        self.assertEqual(self.trx.total, 3000)
        # Menghapus dari keranjang tidak boleh menyentuh stok katalog.
        self.assertEqual(self.katalog.cari("A01").stok, 5)

    def test_hapus_item_yang_tidak_ada(self) -> None:
        with self.assertRaises(ItemTidakAdaError):
            self.trx.hapus_item("A01")

    def test_bayar_kurang_tidak_mengurangi_stok(self) -> None:
        self.trx.tambah_item("A01", 2)
        with self.assertRaises(PembayaranError):
            self.trx.selesaikan(9999)
        self.assertEqual(self.katalog.cari("A01").stok, 5)
        self.assertFalse(self.trx.selesai)
        self.assertEqual(len(self.trx.keranjang.semua()), 1)

    def test_selesaikan_mengurangi_stok_dan_menyimpan_snapshot(self) -> None:
        self.trx.tambah_item("A01", 2)
        hasil = self.trx.selesaikan(20000)

        self.assertEqual(hasil.kembalian, 10000)
        self.assertEqual(self.katalog.cari("A01").stok, 3)
        self.assertEqual(hasil.items[0].nama, "Kopi Hitam")
        self.assertEqual(hasil.items[0].harga_satuan, 5000)
        self.assertEqual(hasil.total, 10000)
        self.assertEqual(hasil.jumlah_item, 2)

        # Ubah katalog setelah transaksi: riwayat tidak boleh ikut berubah.
        produk = self.katalog.cari("A01")
        produk.nama = "Kopi Mahal"
        produk.harga = 99999
        self.assertEqual(hasil.items[0].nama, "Kopi Hitam")
        self.assertEqual(hasil.items[0].harga_satuan, 5000)
        self.assertEqual(hasil.total, 10000)

    def test_keranjang_kosong_tidak_bisa_dibayar(self) -> None:
        with self.assertRaises(KeranjangKosongError):
            self.trx.selesaikan(10000)

    def test_simpan_dan_muat_katalog(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "produk.json"
            katalog = Katalog(PRODUK_AWAL)
            katalog.kurangi_stok("A01", 2)
            katalog.simpan(path)

            self.assertTrue(path.exists())
            dimuat = Katalog(path=path)
            self.assertEqual(dimuat.cari("A01").stok, 3)
            self.assertEqual(dimuat.cari("A01").harga, 5000)

    def test_reset_katalog_dari_data_awal(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            awal = Path(folder) / "awal.json"
            awal.write_text(
                json.dumps(
                    [{"kode": "A01", "nama": "Kopi Hitam", "harga": 5000, "stok": 5}]
                ),
                encoding="utf-8",
            )
            kerja = Path(folder) / "produk.json"
            katalog = Katalog(path=kerja)  # memuat stok awal asli (50)
            katalog.kurangi_stok("A01", 1)
            self.assertEqual(katalog.cari("A01").stok, 49)

            katalog.reset(sumber=awal)
            self.assertEqual(katalog.cari("A01").stok, 5)
            self.assertEqual(Katalog(path=kerja).cari("A01").stok, 5)

    def test_struk_dan_penyimpanan_riwayat(self) -> None:
        self.trx.tambah_item("A01", 1)
        hasil = self.trx.selesaikan(5000)
        teks = format_struk(hasil)
        self.assertIn("Kopi Hitam", teks)
        self.assertIn("Jumlah item", teks)
        self.assertIn("Kembalian", teks)

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "riwayat.json"
            riwayat = RiwayatTransaksi(path)
            riwayat.catat(hasil)
            self.assertTrue(path.exists())

            dimuat_ulang = RiwayatTransaksi(path)
            self.assertEqual(len(dimuat_ulang.semua()), 1)
            self.assertEqual(dimuat_ulang.semua()[0].total, 5000)
            self.assertEqual(dimuat_ulang.semua()[0].items[0].nama, "Kopi Hitam")


if __name__ == "__main__":
    unittest.main()
