"""
bandingkan_2_folder.py

Membandingkan statistik sharpness/blur antara DUA folder berisi gambar yang
BERBEDA satu sama lain (bukan pasangan file yang sama). Cocok untuk kasus
seperti: "batch foto A lebih tajam dari batch foto B?"

CATATAN PENTING (baca dulu):
- Ini membandingkan SEBARAN STATISTIK, bukan gambar per gambar. Karena isi
  kedua folder berbeda, sebagian perbedaan skor bisa jadi disebabkan oleh
  KONTEN gambar (tekstur, pencahayaan, objek), bukan murni karena blur.
- Uji statistik (Mann-Whitney U) memberi tahu apakah perbedaan skor SIGNIFIKAN
  secara statistik, TAPI signifikan secara statistik != signifikan secara
  visual/praktis. Selalu cek juga secara visual, terutama jika jumlah gambar
  di tiap folder kecil (<20).
- Metrik yang dipakai (variance of Laplacian, Tenengrad) adalah proksi relatif
  ketajaman, bukan pengukuran blur yang absolut/terkalibrasi.

Cara pakai:
    python bandingkan_2_folder.py /path/folder_A /path/folder_B
    python bandingkan_2_folder.py /path/folder_A /path/folder_B --recursive
    python bandingkan_2_folder.py /path/folder_A /path/folder_B --csv hasil.csv
    python bandingkan_2_folder.py /path/folder_A /path/folder_B --label "Sebelum" "Sesudah"
"""

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

try:
    from scipy.stats import mannwhitneyu
    ADA_SCIPY = True
except ImportError:
    ADA_SCIPY = False

EKSTENSI_VALID = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def hitung_variance_laplacian(gray: np.ndarray) -> float:
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def hitung_tenengrad(gray: np.ndarray) -> float:
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    return float(np.mean(gx**2 + gy**2))


def kumpulkan_file_gambar(folder: Path, rekursif: bool) -> list[Path]:
    pola = folder.rglob("*") if rekursif else folder.glob("*")
    return sorted(p for p in pola if p.is_file() and p.suffix.lower() in EKSTENSI_VALID)


def proses_folder(folder: Path, rekursif: bool, resize_max: int = 1200) -> list[dict]:
    hasil = []
    for path in kumpulkan_file_gambar(folder, rekursif):
        img = cv2.imread(str(path))
        if img is None:
            print(f"[GAGAL BACA] {path}")
            continue
        h, w = img.shape[:2]
        skala = min(1.0, resize_max / max(h, w))
        if skala < 1.0:
            img = cv2.resize(img, (int(w * skala), int(h * skala)))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hasil.append({
            "file": str(path),
            "laplacian_var": hitung_variance_laplacian(gray),
            "tenengrad": hitung_tenengrad(gray),
        })
    return hasil


def ringkas(skor: np.ndarray) -> dict:
    return {
        "n": len(skor),
        "mean": float(np.mean(skor)),
        "median": float(np.median(skor)),
        "std": float(np.std(skor)),
        "min": float(np.min(skor)),
        "p25": float(np.percentile(skor, 25)),
        "p75": float(np.percentile(skor, 75)),
        "max": float(np.max(skor)),
    }


def cetak_perbandingan(nama_metrik: str, ringkasan_a: dict, ringkasan_b: dict,
                        label_a: str, label_b: str, p_value: float | None):
    print(f"\n=== {nama_metrik} ===")
    print(f"{'':<10} {label_a:<18} {label_b:<18}")
    for k in ["n", "mean", "median", "std", "min", "p25", "p75", "max"]:
        va, vb = ringkasan_a[k], ringkasan_b[k]
        print(f"{k:<10} {va:<18.2f} {vb:<18.2f}")

    beda_median = ringkasan_b["median"] - ringkasan_a["median"]
    arah = label_b if beda_median > 0 else label_a
    persen = abs(beda_median) / (ringkasan_a["median"] + 1e-9) * 100
    print(f"-> Median '{arah}' lebih tinggi {abs(beda_median):.2f} poin (~{persen:.1f}%)")

    if p_value is not None:
        signif = "SIGNIFIKAN (p < 0.05)" if p_value < 0.05 else "tidak signifikan (p >= 0.05)"
        print(f"-> Uji Mann-Whitney U: p-value = {p_value:.4f} -> {signif}")
    else:
        print("-> scipy tidak terpasang, uji signifikansi statistik dilewati "
              "(install dengan: pip install scipy)")


def main():
    parser = argparse.ArgumentParser(description="Bandingkan sharpness/blur dua folder gambar")
    parser.add_argument("folder_a", type=str, help="Folder pertama")
    parser.add_argument("folder_b", type=str, help="Folder kedua")
    parser.add_argument("--label", nargs=2, default=None, metavar=("LABEL_A", "LABEL_B"),
                         help="Nama label untuk masing-masing folder (default: nama folder)")
    parser.add_argument("--recursive", action="store_true", help="Telusuri subfolder juga")
    parser.add_argument("--csv", type=str, default=None, help="Simpan data mentah gabungan ke CSV")
    parser.add_argument("--top", type=int, default=5,
                         help="Jumlah gambar paling blur yang ditampilkan per folder (default: 5)")
    args = parser.parse_args()

    folder_a, folder_b = Path(args.folder_a), Path(args.folder_b)
    for f in (folder_a, folder_b):
        if not f.is_dir():
            print(f"Error: folder tidak ditemukan -> {f}")
            sys.exit(1)

    label_a, label_b = args.label if args.label else (folder_a.name, folder_b.name)

    print(f"Memproses folder '{label_a}' ({folder_a}) ...")
    data_a = proses_folder(folder_a, args.recursive)
    print(f"Memproses folder '{label_b}' ({folder_b}) ...")
    data_b = proses_folder(folder_b, args.recursive)

    if not data_a or not data_b:
        print("Salah satu folder tidak punya gambar valid. Berhenti.")
        sys.exit(1)

    if min(len(data_a), len(data_b)) < 20:
        print("\n[PERHATIAN] Salah satu/kedua folder punya <20 gambar. Kesimpulan "
              "statistik dengan sampel sekecil ini kurang bisa diandalkan — "
              "anggap hasil di bawah sebagai indikasi awal, bukan kesimpulan final.")

    lap_a = np.array([d["laplacian_var"] for d in data_a])
    lap_b = np.array([d["laplacian_var"] for d in data_b])
    ten_a = np.array([d["tenengrad"] for d in data_a])
    ten_b = np.array([d["tenengrad"] for d in data_b])

    p_lap = p_ten = None
    if ADA_SCIPY:
        try:
            p_lap = mannwhitneyu(lap_a, lap_b, alternative="two-sided").pvalue
            p_ten = mannwhitneyu(ten_a, ten_b, alternative="two-sided").pvalue
        except ValueError:
            pass

    cetak_perbandingan("VARIANCE OF LAPLACIAN (metrik utama)",
                        ringkas(lap_a), ringkas(lap_b), label_a, label_b, p_lap)
    cetak_perbandingan("TENENGRAD (metrik pembanding)",
                        ringkas(ten_a), ringkas(ten_b), label_a, label_b, p_ten)

    # Tampilkan gambar paling blur di masing-masing folder sebagai konteks visual
    for label, data in [(label_a, data_a), (label_b, data_b)]:
        print(f"\n{args.top} gambar paling blur di '{label}':")
        for d in sorted(data, key=lambda x: x["laplacian_var"])[:args.top]:
            print(f"  laplacian_var={d['laplacian_var']:.2f}  {d['file']}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["folder", "file", "laplacian_var", "tenengrad"])
            writer.writeheader()
            for label, data in [(label_a, data_a), (label_b, data_b)]:
                for d in data:
                    writer.writerow({"folder": label, **d})
        print(f"\nData mentah disimpan ke: {args.csv}")


if __name__ == "__main__":
    main()