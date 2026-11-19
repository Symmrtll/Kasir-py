"""Antarmuka CLI aplikasi kasir.

File ini adalah satu-satunya tempat pemakaian input()/print().
Semua keputusan bisnis didelegasikan ke package ``pos``.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from pos.katalog import Katalog, ProdukTidakDitemukanError, StokTidakCukupError
from pos.struk import RiwayatTransaksi, format_struk
from pos.transaksi import ItemTidakAdaError, PembayaranError, Transaksi
from pos.validasi import validasi_kode, validasi_qty, validasi_uang_bayar

T = TypeVar("T")


def minta(prompt: str, validator: Callable[[str], T]) -> T:
    """Minta input, validasi, dan ulangi sampai nilai valid diperoleh."""
    while True:
        try:
            return validator(input(prompt))
        except ValueError as exc:
            print(f"Input tidak valid: {exc}")


def tampilkan_katalog(katalog: Katalog) -> None:
    """Cetak daftar produk beserta harga dan stoknya."""
    print("\n=== KATALOG PRODUK ===")
    print(f"{'Kode':<7}{'Nama':<22}{'Harga':>10}{'Stok':>7}")
    print("-" * 46)
    for p in katalog.semua():
        print(f"{p.kode:<7}{p.nama:<22}{'Rp' + str(p.harga):>10}{p.stok:>7}")


def tampilkan_keranjang(transaksi: Transaksi) -> None:
    """Cetak isi keranjang dan total sementara."""
    print("\n--- Keranjang ---")
    if transaksi.keranjang.kosong:
        print("(kosong)")
        return
    for i in transaksi.keranjang.semua():
        print(f"{i.kode} {i.nama}: {i.qty} x Rp{i.harga_satuan} = Rp{i.subtotal}")
    print(f"TOTAL: Rp{transaksi.total}")


def tampilkan_riwayat(riwayat: RiwayatTransaksi) -> None:
    """Cetak ringkasan seluruh transaksi yang sudah tersimpan."""
    print("\n=== RIWAYAT TRANSAKSI ===")
    semua = riwayat.semua()
    if not semua:
        print("(belum ada transaksi)")
        return
    for no, trx in enumerate(semua, 1):
        print(f"\n#{no} {trx.waktu} - total Rp{trx.total}, bayar Rp{trx.uang_bayar}")
        for i in trx.items:
            print(f"  {i.kode} {i.nama}: {i.qty} x Rp{i.harga_satuan} = Rp{i.subtotal}")


def jalankan_transaksi(katalog: Katalog, riwayat: RiwayatTransaksi) -> None:
    """Jalankan satu sesi transaksi sampai selesai, dibatalkan, atau gagal."""
    trx = Transaksi(katalog)
    print("\n=== TRANSAKSI BARU ===")
    print("Ketik 'S' selesai / 'H' hapus item / 'B' batal.")
    try:
        while True:
            tampilkan_keranjang(trx)
            mentah = input("\nKode barang: ").strip()
            perintah = mentah.upper()

            if perintah == "B":
                print("Transaksi dibatalkan. Stok tidak berubah.")
                return

            if perintah == "H":
                try:
                    kode_hapus = minta("Hapus kode barang: ", validasi_kode)
                    item_hapus = trx.hapus_item(kode_hapus)
                except (ItemTidakAdaError, ValueError) as exc:
                    print(f"Gagal menghapus: {exc}")
                else:
                    print(f"Dihapus dari keranjang: {item_hapus.nama}")
                continue

            if perintah == "S":
                if trx.keranjang.kosong:
                    print("Keranjang masih kosong. Tambahkan barang dulu.")
                    continue
                uang = minta("Uang bayar: Rp", validasi_uang_bayar)
                try:
                    hasil = trx.selesaikan(uang)
                except (PembayaranError, StokTidakCukupError) as exc:
                    print(f"Transaksi gagal: {exc}")
                    print("Stok belum berubah. Bayar lagi atau ketik 'B'.")
                    continue

                print()
                print(format_struk(hasil))
                try:
                    riwayat.catat(hasil)
                    katalog.simpan()
                except OSError as exc:
                    print(f"Peringatan: gagal menyimpan data: {exc}")
                return

            try:
                kode = validasi_kode(mentah)
                qty = minta("Jumlah: ", validasi_qty)
                item = trx.tambah_item(kode, qty)
                print(f"Ditambahkan: {item.nama} ({item.qty} {item.kode})")
            except (ValueError, ProdukTidakDitemukanError) as exc:
                print(f"Gagal menambah: {exc}")
    except (EOFError, KeyboardInterrupt):
        print("\nTransaksi dibatalkan. Stok tidak berubah.")


def main() -> None:
    """Loop menu utama aplikasi kasir."""
    katalog = Katalog()
    riwayat = RiwayatTransaksi()

    while True:
        print("\n===== MENU KASIR =====")
        print("1. Transaksi baru")
        print("2. Lihat katalog")
        print("3. Lihat riwayat transaksi")
        print("4. Reset stok ke data awal")
        print("0. Keluar")
        try:
            pilihan = input("Pilih menu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTerima kasih. Sampai jumpa!")
            break

        if pilihan == "1":
            jalankan_transaksi(katalog, riwayat)
        elif pilihan == "2":
            tampilkan_katalog(katalog)
        elif pilihan == "3":
            tampilkan_riwayat(riwayat)
        elif pilihan == "4":
            try:
                jawab = input("Reset stok dari produk_awal.json? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                continue
            if jawab == "y":
                try:
                    katalog.reset()
                except OSError as exc:
                    print(f"Gagal reset: {exc}")
                else:
                    print("Stok berhasil dikembalikan ke data awal.")
            else:
                print("Reset dibatalkan.")
        elif pilihan == "0":
            print("Terima kasih. Sampai jumpa!")
            break
        else:
            print("Pilihan tidak dikenal.")


if __name__ == "__main__":
    main()
