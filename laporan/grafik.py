"""Geometri grafik Laporan sebagai SVG yang dirender server (tanpa pustaka JS/CDN; hover = <title> bawaan browser).

Warna (palet tervalidasi, mode terang): status pekerjaan per unit memakai hijau=selesai tepat waktu,
biru=masih berjalan, kuning=selesai terlambat, merah=terlambat & belum selesai — urutan ini lolos uji buta warna
(CVD ΔE terburuk 19.8). Kuning < 3:1 terhadap latar, jadi setiap grafik WAJIB punya legenda + tabel angka di bawahnya.
Tren memakai dua seri kategorikal (biru, oranye). Teks selalu memakai warna teks, bukan warna seri.
"""
import math

HIJAU, BIRU, KUNING, MERAH, ORANYE = "#0ca30c", "#2a78d6", "#eda100", "#d03b3b", "#eb6834"
BULAN = "Jan Feb Mar Apr Mei Jun Jul Agu Sep Okt Nov Des".split()


def _tgl(d):
    return f"{d.day:02d} {BULAN[d.month - 1]}"


SEGMEN = [("tepat", "Selesai tepat waktu", HIJAU), ("berjalan", "Masih berjalan", BIRU),
          ("telat_selesai", "Selesai terlambat", KUNING), ("telat_buka", "Terlambat, belum selesai", MERAH)]


def _maks_rapi(n):
    """Batas atas sumbu & garis bantu BILANGAN BULAT (jumlah tugas tidak pernah pecahan), langkah 1/2/5×10^k."""
    langkah = 1
    while math.ceil(max(n, 1) / langkah) > 5:
        langkah = next(k * 10 ** e for e in range(6) for k in (1, 2, 5) if k * 10 ** e > langkah)
    atas = langkah * math.ceil(max(n, 1) / langkah)
    return atas, list(range(0, atas + 1, langkah))


def per_unit(baris, maks_baris=12):
    """Batang bertumpuk mendatar per unit (unit terbanyak tugasnya di atas)."""
    data = []
    for r in sorted((r for r in baris if r["total"] - r["dibatalkan"] > 0), key=lambda r: (-r["total"], r["kode"]))[:maks_baris]:
        nilai = {"tepat": r["selesai"] - r["selesai_terlambat"], "berjalan": r["terbuka"] - r["terlambat_terbuka"],
                 "telat_selesai": r["selesai_terlambat"], "telat_buka": r["terlambat_terbuka"]}
        data.append((r, nilai, sum(nilai.values())))
    if not data:
        return None
    atas, garis = _maks_rapi(max(t for _, _, t in data))
    kiri, kanan, tinggi_baris, tebal = 120, 940, 28, 16                # viewBox 1000: skala ±1 di kartu lebar
    lebar = kanan - kiri
    rows = []
    for i, (r, nilai, total) in enumerate(data):
        y, x, seg = 24 + i * tinggi_baris, kiri, []
        for kunci, label, warna in SEGMEN:
            n = nilai[kunci]
            if not n:
                continue
            w = lebar * n / atas
            seg.append({"x": round(x, 1), "w": round(max(w - 2, 1), 1), "warna": warna,     # celah 2px antar-segmen
                        "judul": f"{r['kode']} — {label}: {n}"})
            x += w
        rows.append({"y": y, "kode": r["kode"], "nama": r["nama"], "total": total, "seg": seg,
                     "x_total": round(x + 6, 1), "ty": y + tebal / 2 + 4, "tebal": tebal})
    tinggi = 24 + len(rows) * tinggi_baris + 8
    return {"rows": rows, "tinggi": tinggi, "kiri": kiri, "legenda": [(l, w) for _, l, w in SEGMEN],
            "garis": [{"x": round(kiri + lebar * g / atas, 1), "label": g} for g in garis],
            "dipotong": len(baris) > maks_baris, "jumlah_unit": len(baris)}


def tren(minggu):
    """Garis 'tugas baru' vs 'tugas selesai' per minggu. `minggu` = [{"mulai": date, "dibuat": n, "selesai": n}]."""
    if len(minggu) < 2:
        return None
    kiri, kanan, atas_y, bawah_y = 40, 560, 16, 176
    atas, garis = _maks_rapi(max(max(m["dibuat"], m["selesai"]) for m in minggu))
    langkah = (kanan - kiri) / (len(minggu) - 1)

    def y(n):
        return round(bawah_y - (bawah_y - atas_y) * n / atas, 1)

    seri = []
    for kunci, label, warna in (("dibuat", "Tugas baru", BIRU), ("selesai", "Tugas selesai", ORANYE)):
        titik = [{"x": round(kiri + i * langkah, 1), "y": y(m[kunci]), "n": m[kunci],
                  "judul": f"Minggu {_tgl(m['mulai'])}: {label.lower()} {m[kunci]}"} for i, m in enumerate(minggu)]
        seri.append({"label": label, "warna": warna, "titik": titik,
                     "poly": " ".join(f"{t['x']},{t['y']}" for t in titik), "akhir": titik[-1]})
    # label ujung tidak boleh bertumpuk: geser yang bawah bila jaraknya < 14px
    a, b = seri[0]["akhir"], seri[1]["akhir"]
    ya, yb = a["y"] + 4, b["y"] + 4
    if abs(ya - yb) < 14:
        ya, yb = (ya - 7, yb + 7) if ya <= yb else (ya + 7, yb - 7)
    seri[0]["label_y"], seri[1]["label_y"] = ya, yb
    tiap = max(1, math.ceil(len(minggu) / 8))                      # maks ±8 label sumbu-x
    return {"seri": seri, "kiri": kiri, "kanan": kanan, "bawah": bawah_y,
            "garis": [{"y": y(g), "label": g} for g in garis],
            "sumbu_x": [{"x": round(kiri + i * langkah, 1), "label": _tgl(m["mulai"])}
                        for i, m in enumerate(minggu) if i % tiap == 0 or i == len(minggu) - 1]}


def status(per_status, label):
    """Batang mendatar satu warna: jumlah tugas per status (besaran, bukan identitas)."""
    baris = [(label[k], n) for k, n in per_status if n]
    if not baris:
        return None
    maks = max(n for _, n in baris)
    return [{"label": lbl, "n": n, "pct": round(100 * n / maks)} for lbl, n in baris]
