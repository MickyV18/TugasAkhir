"""
gabung_gambar.py
Menyatukan 3 gambar secara vertikal (dari atas ke bawah) dengan jeda antar gambar.

Cara pakai:
    python gabung_gambar.py gambar1.jpg gambar2.jpg gambar3.jpg

Opsi tambahan:
    --gap       Jeda antar gambar dalam pixel (default: 20)
    --color     Warna jeda dalam format R,G,B (default: 255,255,255 = putih)
    --output    Nama file hasil (default: hasil_gabungan.png)
    --resize    Lebarkan semua gambar ke lebar yang sama (default: aktif)

Contoh:
    python gabung_gambar.py a.jpg b.png c.webp --gap 30 --color 0,0,0 --output hasil.png
"""

import argparse
import sys
from pathlib import Path
from PIL import Image


def gabung_gambar(
    paths: list[str],
    gap: int = 20,
    gap_color: tuple[int, int, int] = (255, 255, 255),
    output: str = "hasil_gabungan.png",
    resize_to_same_width: bool = True,
) -> None:
    """Gabungkan beberapa gambar secara vertikal dengan jeda antar gambar."""

    # --- Buka semua gambar ---
    gambar_list = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            print(f"[ERROR] File tidak ditemukan: {path}")
            sys.exit(1)
        img = Image.open(p).convert("RGBA")
        gambar_list.append(img)
        print(f"  ✔ Dibuka  : {path}  ({img.width} x {img.height} px)")

    # --- Samakan lebar (opsional) ---
    if resize_to_same_width:
        target_width = max(img.width for img in gambar_list)
        resized = []
        for img in gambar_list:
            if img.width != target_width:
                ratio = target_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((target_width, new_height), Image.LANCZOS)
            resized.append(img)
        gambar_list = resized
    else:
        target_width = max(img.width for img in gambar_list)

    n = len(gambar_list)
    total_height = sum(img.height for img in gambar_list) + gap * (n - 1)

    # --- Buat kanvas kosong ---
    # Deteksi apakah perlu mode RGBA (ada transparansi) atau RGB
    has_alpha = any(img.mode == "RGBA" for img in gambar_list)
    mode = "RGBA" if has_alpha else "RGB"
    bg_color = gap_color if mode == "RGB" else (*gap_color, 255)

    kanvas = Image.new(mode, (target_width, total_height), bg_color)

    # --- Tempel gambar satu per satu ---
    y_offset = 0
    for i, img in enumerate(gambar_list):
        # Pusatkan secara horizontal jika lebar berbeda
        x_offset = (target_width - img.width) // 2

        if mode == "RGBA":
            kanvas.paste(img, (x_offset, y_offset), mask=img.split()[3])
        else:
            kanvas.paste(img.convert("RGB"), (x_offset, y_offset))

        print(f"  ✔ Ditempel: gambar ke-{i + 1} di y={y_offset}")
        y_offset += img.height + (gap if i < n - 1 else 0)

    # --- Simpan hasil ---
    output_path = Path(output)
    # Simpan sebagai PNG agar tidak ada kompresi lossy; ubah ke RGB jika JPEG
    if output_path.suffix.lower() in (".jpg", ".jpeg"):
        kanvas = kanvas.convert("RGB")

    kanvas.save(output_path)
    print(f"\n✅ Berhasil! Hasil disimpan di: {output_path.resolve()}")
    print(f"   Ukuran akhir: {kanvas.width} x {kanvas.height} px")


def parse_color(value: str) -> tuple[int, int, int]:
    parts = value.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Format warna harus R,G,B  contoh: 255,255,255")
    r, g, b = (int(v.strip()) for v in parts)
    return (r, g, b)


def main():
    parser = argparse.ArgumentParser(
        description="Gabungkan 3 (atau lebih) gambar secara vertikal dengan jeda antar gambar.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("gambar", nargs="+", help="Path gambar-gambar yang ingin digabung (minimal 2)")
    parser.add_argument("--gap", type=int, default=20, help="Jeda antar gambar dalam pixel (default: 20)")
    parser.add_argument(
        "--color",
        type=parse_color,
        default="255,255,255",
        metavar="R,G,B",
        help="Warna jeda (default: 255,255,255 = putih)",
    )
    parser.add_argument("--output", default="hasil_gabungan.png", help="Nama file output (default: hasil_gabungan.png)")
    parser.add_argument(
        "--no-resize",
        action="store_true",
        help="Jangan samakan lebar gambar (gunakan lebar asli masing-masing)",
    )

    args = parser.parse_args()

    if len(args.gambar) < 2:
        print("[ERROR] Minimal 2 gambar diperlukan.")
        sys.exit(1)

    print(f"\n🖼  Menggabungkan {len(args.gambar)} gambar...")
    print(f"   Gap       : {args.gap} px")
    print(f"   Warna gap : RGB{args.color}")
    print(f"   Output    : {args.output}\n")

    gabung_gambar(
        paths=args.gambar,
        gap=args.gap,
        gap_color=args.color,
        output=args.output,
        resize_to_same_width=not args.no_resize,
    )


if __name__ == "__main__":
    # Pastikan Pillow sudah terinstall
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("[ERROR] Library 'Pillow' belum terinstall.")
        print("        Jalankan: pip install Pillow")
        sys.exit(1)

    main()
