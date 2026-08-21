#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sunum/dokumanlar/md/*.md  ->  sunum/dokumanlar/*.docx  (toplu dönüştürme + denetim)"""
import pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from md2docx import convert  # noqa: E402

DOCS = pathlib.Path(r"C:/Users/darkb/Desktop/hb-final/sunum/dokumanlar")
MD = DOCS / "md"

TITLES = {
    "00-sunum-konusma-notlari":        ("00 - Sunum Konusma Notlari",           "Slayt slayt konuşma metni ve süre planı"),
    "01-algoritma-teknik-rapor":       ("01 - Algoritma ve Teknik Rapor",       "Uçtan uca algoritma, model ve ölçülmüş sonuçlar"),
    "02-juri-soru-cevap-kitabi":       ("02 - Juri Soru-Cevap Hazirlik Kitabi", "Beklenen jüri soruları ve kanıtlı cevaplar"),
    "03-teknik-gereksinim-uyum-matrisi": ("03 - Teknik Gereksinim Uyum Matrisi", "Jüri ne istedi, biz ne yaptık, kanıt"),
    "04-sunum-konusma-metni":          ("04 - Sunum Akisi ve Konusma Metni",    "Slayt akışı ve genişletilmiş konuşma metni"),
}


def lint(path: pathlib.Path):
    """Dönüştürmeden önce markdown'ı denetle; docx'e taşınmayacak şeyleri yakala."""
    problems, lines = [], path.read_text(encoding="utf-8").split("\n")
    h1 = [i for i, l in enumerate(lines) if l.startswith("# ")]
    if len(h1) != 1:
        problems.append(f"{len(h1)} adet '# ' başlığı var (tam 1 olmalı)")
    in_code = False
    for i, l in enumerate(lines, 1):
        if l.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.search(r"!\[|\]\(http|<[a-zA-Z/]", l):
            problems.append(f"satır {i}: resim/link/HTML kullanılmış")
        if re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", l):
            problems.append(f"satır {i}: emoji var")
    # tablo tutarlılığı
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and \
           re.fullmatch(r"\|[\s:|-]+\|", lines[i + 1].strip() or "x"):
            width = lines[i].count("|")
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                if abs(lines[j].count("|") - width) > 0:
                    problems.append(f"satır {j+1}: tablo hücre sayısı başlıkla uyuşmuyor")
                j += 1
            i = j
        else:
            i += 1
    return problems


def main():
    if not MD.exists():
        print("md klasörü yok"); return 1
    files = sorted(MD.glob("*.md"))
    if not files:
        print("md dosyası yok"); return 1
    ok = True
    for md in files:
        key = md.stem
        name, subtitle = TITLES.get(key, (key, "Jüri dökümanı"))
        problems = lint(md)
        words = len(md.read_text(encoding="utf-8").split())
        rows = [
            ("Yarışma", "TEKNOFEST 2026 · Hepsiburada"),
            ("Kategori", "Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu"),
            ("Aşama", "Final — Backtest"),
            ("Takım", "Büke"),
            ("Belge", subtitle),
        ]
        dest = DOCS / f"{name}.docx"
        title = convert(md, dest, subtitle, rows)
        flag = "OK " if not problems else "!! "
        print(f"{flag}{dest.name:<44} {words:>6} kelime   « {title}")
        for p in problems[:8]:
            print(f"     - {p}")
            ok = False
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
