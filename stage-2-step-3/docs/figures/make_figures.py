"""README figürlerini ``chart_data.json`` üzerinden yeniden üretir.

Her figür açık ve koyu tema olarak iki kez yazılır; README bunları
``<picture>`` + ``prefers-color-scheme`` ile eşler.

Renk seçimi el yordamıyla değil, doğrulanmış paletten yapılır (dataviz
yöntemi): kategorik yuvalar sabit sırayla, sıralı (ordinal) ölçekler tek
hue açıktan koyuya. Palet ``validate_palette.js`` ile geçirildi:
kategorik 3/4 yuva ve mavi ordinal rampa, iki temada da tüm kapıları geçti.

Çizim kuralları (dataviz references/marks-and-anatomy.md):
  * ince işaretler, geniş boşluk — kalın doygun bloklar yok
  * hairline, DÜZ (kesikli değil) ve geri planda ızgara
  * yığılmış segmentler arasında kenarlık değil 2px YÜZEY boşluğu
  * 2+ seri varsa legend her zaman var; doğrudan etiket seçici
  * legend figür seviyesinde, alt başlığın altında — çubukla çakışmaz

Çalıştırma:  python docs/figures/make_figures.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "chart_data.json").read_text(encoding="utf-8"))

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "ink": "#0b0b0b",
        "ink2": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "on_fill": "#ffffff",
        "cat": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"],
        "ord4": ["#86b6ef", "#5598e7", "#2a78d6", "#104281"],
        "ord3": ["#86b6ef", "#2a78d6", "#104281"],
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#ffffff",
        "ink2": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "on_fill": "#0b0b0b",
        "cat": ["#3987e5", "#d95926", "#199e70", "#c98500"],
        "ord4": ["#cde2fb", "#86b6ef", "#3987e5", "#184f95"],
        "ord3": ["#cde2fb", "#86b6ef", "#184f95"],
    },
}


def _tr(value, decimals=0):
    """Türkçe sayı biçimi: binlik nokta, ondalık virgül."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",").replace(" ", ".")


TR_MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
             "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
THOUSANDS = FuncFormatter(lambda v, _p: _tr(v))
MILLIONS = FuncFormatter(lambda v, _p: f"{_tr(v/1e6, 0)}M" if v else "0")


def _frame(ax, t, *, xgrid=False, ygrid=True):
    ax.set_facecolor(t["surface"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(t["axis"])
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=t["muted"], labelsize=9, length=0)
    if ygrid:
        ax.yaxis.grid(True, color=t["grid"], linewidth=0.8)
    if xgrid:
        ax.xaxis.grid(True, color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def _title(fig, t, title, subtitle=None):
    fig.text(0.014, 0.965, title, ha="left", va="top",
             fontsize=13.5, color=t["ink"], fontweight="bold")
    if subtitle:
        fig.text(0.014, 0.895, subtitle, ha="left", va="top",
                 fontsize=9.5, color=t["ink2"], linespacing=1.45)


def _legend_row(fig, t, entries, *, y=0.80, ncols=None):
    """Legend'ı figür seviyesinde, alt başlığın altına yatay dizer.

    Eksen içine koymak uzun etiketlerde çubuklarla çakışıyor; burada
    çakışma yapısal olarak imkânsız.
    """
    handles = [Patch(facecolor=color, edgecolor="none", label=label)
               for label, color in entries]
    legend = fig.legend(handles=handles, loc="upper left",
                        bbox_to_anchor=(0.012, y), frameon=False,
                        fontsize=9, ncols=ncols or len(entries),
                        handlelength=0.9, handleheight=0.9,
                        columnspacing=1.5, handletextpad=0.5)
    for text in legend.get_texts():
        text.set_color(t["ink2"])
    return legend


def _save(fig, name, theme):
    out = HERE / f"{name}-{theme}.png"
    fig.savefig(out, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


def _new(theme, figsize):
    t = THEMES[theme]
    return plt.figure(figsize=figsize, facecolor=t["surface"]), t


# --------------------------------------------------------------------------
# F1 — Maliyet merdiveni (yığılmış yatay çubuk)
# --------------------------------------------------------------------------
def fig_cost_cascade(theme):
    fig, t = _new(theme, (9.0, 4.9))
    ax = fig.add_axes([0.19, 0.12, 0.72, 0.58])
    _frame(ax, t, xgrid=True, ygrid=False)

    stages = ["Stage 0", "Stage 1", "Stage 2", "Stage 3"]
    labels = ["Stage 0\ntemel plan", "Stage 1\naynı-hat onarım",
              "Stage 2\nmilk-run ≤4 durak",
              "Stage 3\nrota-ortası yük alma"]
    vehicle = [DATA["stages"][s]["vehicle_cost"] for s in stages]
    sla = [DATA["stages"][s]["sla_penalty"] for s in stages]
    y = list(range(len(stages)))
    span = max(v + s for v, s in zip(vehicle, sla))
    gap = span * 0.005

    ax.barh(y, vehicle, height=0.34, color=t["cat"][0])
    ax.barh(y, sla, height=0.34, left=[v + gap for v in vehicle],
            color=t["cat"][1])

    for i, (v, s) in enumerate(zip(vehicle, sla)):
        ax.text(v + s + gap + span * 0.02, i, f"{_tr((v+s)/1e6, 2)}M TL",
                va="center", ha="left", fontsize=11, color=t["ink"],
                fontweight="bold")
        ax.text(v / 2, i, _tr(v / 1e6, 2) + "M", va="center", ha="center",
                fontsize=8.5, color=t["on_fill"])

    ax.set_yticks(y, labels, fontsize=9.5, color=t["ink2"])
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(MultipleLocator(5e6))
    ax.xaxis.set_major_formatter(MILLIONS)
    ax.set_xlim(0, span * 1.22)
    ax.set_xlabel("TL", color=t["muted"], fontsize=9)

    _legend_row(fig, t, [("Araç maliyeti", t["cat"][0]),
                         ("SLA cezası", t["cat"][1])], y=0.79)
    saving = vehicle[0] + sla[0] - (vehicle[-1] + sla[-1])
    _title(fig, t, "Toplam maliyet aşama aşama düşüyor",
           f"Stage 0 → Stage 3: −{_tr(saving/1e6, 2)}M TL "
           f"(−%{_tr(100*saving/(vehicle[0]+sla[0]), 1)}) · her aşamada 0 ihlal")
    return _save(fig, "01-maliyet-merdiveni", theme)


# --------------------------------------------------------------------------
# F2 — Geçmiş günlük hacim (zaman serisi + olay işaretçisi)
# --------------------------------------------------------------------------
def fig_history_daily(theme):
    fig, t = _new(theme, (9.0, 4.2))
    ax = fig.add_axes([0.115, 0.13, 0.86, 0.60])
    _frame(ax, t)

    days = [dt.date.fromisoformat(d) for d in DATA["history_daily"]["days"]]
    desi = DATA["history_daily"]["desi"]
    month_ends = {dt.date.fromisoformat(d)
                  for d in DATA["history_daily"]["month_end_days"]}

    ax.plot(days, desi, color=t["cat"][0], linewidth=1.6)
    me_x = [d for d in days if d in month_ends]
    me_y = [v for d, v in zip(days, desi) if d in month_ends]
    ax.scatter(me_x, me_y, s=58, color=t["cat"][1], zorder=5,
               edgecolors=t["surface"], linewidths=2)

    lowest_y, lowest_x = min(zip(me_y, me_x))
    ax.annotate(f"{_tr(lowest_y)} desi", xy=(lowest_x, lowest_y),
                xytext=(10, 42), textcoords="offset points", fontsize=9,
                color=t["ink"],
                arrowprops=dict(arrowstyle="-", color=t["axis"], linewidth=0.8))

    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_ylim(0, max(desi) * 1.10)
    ax.set_ylabel("günlük toplam desi", color=t["muted"], fontsize=9)
    month_starts = [d for d in days if d.day == 1]
    ax.set_xticks(month_starts,
                  [TR_MONTHS[d.month - 1] for d in month_starts],
                  fontsize=9, color=t["muted"])

    _legend_row(fig, t, [("Gerçekleşen günlük desi", t["cat"][0]),
                         ("Ayın son günü", t["cat"][1])], y=0.82)
    _title(fig, t, "Ay sonu çöküşü rastlantı değil — her ay tekrarlıyor",
           "1 Ocak – 28 Haziran 2026 gerçekleşen hacim · ayın son günü normal "
           "bir günün ~%2'sine iniyor")
    return _save(fig, "02-gecmis-gunluk-hacim", theme)


# --------------------------------------------------------------------------
# F3 — Bizim tahmin vs "sıradan bir gün" ortalaması (gruplu çubuk)
# --------------------------------------------------------------------------
def fig_forecast_vs_dow(theme):
    fig, t = _new(theme, (9.0, 4.4))
    ax = fig.add_axes([0.105, 0.16, 0.87, 0.56])
    _frame(ax, t)

    fv = DATA["forecast_vs_dow"]
    x = list(range(len(fv["labels"])))
    w = 0.30
    ax.bar([i - w / 2 - 0.012 for i in x], fv["forecast"], width=w,
           color=t["cat"][0])
    ax.bar([i + w / 2 + 0.012 for i in x], fv["dow_mean"], width=w,
           color=t["cat"][1])

    # Seçici doğrudan etiket: hikâyeyi taşıyan tek gün (30 Haziran).
    i = 1
    ax.annotate(f"{_tr(fv['forecast'][i])} desi\nortalamanın %2'si",
                xy=(i - w / 2 - 0.012, fv["forecast"][i]),
                xytext=(-58, 150), textcoords="offset points", fontsize=9,
                color=t["ink"], ha="center", linespacing=1.4,
                arrowprops=dict(arrowstyle="-", color=t["axis"],
                                linewidth=0.8,
                                connectionstyle="angle,angleA=0,angleB=90,rad=4"))

    ax.set_xticks(x, ["29 Haz\nPzt", "30 Haz\nSal", "1 Tem\nÇar", "2 Tem\nPer",
                      "3 Tem\nCum", "4 Tem\nCmt", "5 Tem\nPaz"],
                  fontsize=9, color=t["ink2"])
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_ylabel("desi", color=t["muted"], fontsize=9)
    ax.set_ylim(0, max(fv["dow_mean"]) * 1.12)

    _legend_row(fig, t, [("Bizim tahminimiz", t["cat"][0]),
                         ("Aynı haftagünü geçmiş ortalaması", t["cat"][1])],
                y=0.80)
    _title(fig, t, "Tahminin farkı 30 Haziran'da ortaya çıkıyor",
           "Düz bir haftagünü ortalaması ay sonunu göremez; takvim katmanı "
           "hacmi ×0,0198 ile bastırıyor")
    return _save(fig, "03-tahmin-vs-ortalama", theme)


# --------------------------------------------------------------------------
# F4 — Takvim rol çarpanları (tek seri, 1,0 referans)
# --------------------------------------------------------------------------
def fig_calendar_multipliers(theme):
    fig, t = _new(theme, (7.4, 3.9))
    ax = fig.add_axes([0.115, 0.20, 0.855, 0.53])
    _frame(ax, t)

    keys = ["day_before_month_end", "month_end",
            "first_day_after_month_end", "normal"]
    labels = ["Ay sonundan\bir önceki gün", "Ayın\bson günü",
              "Ayın\bilk günü", "Normal\bgün"]
    labels = ["Ay sonu −1", "Ayın son günü", "Ayın ilk günü", "Normal gün"]
    values = [DATA["calendar_multipliers"][k] for k in keys]

    ax.bar(range(len(values)), values, width=0.36, color=t["cat"][0])
    ax.axhline(1.0, color=t["axis"], linewidth=0.8)
    # Referans yazısı sola alınır; sağda "Normal gün" etiketiyle çakışıyordu.
    ax.text(-0.42, 1.045, "değişim yok (×1,00)", fontsize=8.5,
            color=t["muted"], ha="left")

    for i, v in enumerate(values):
        ax.text(i, v + 0.05, "×" + _tr(v, 4), ha="center", fontsize=10,
                color=t["ink"], fontweight="bold")

    ax.set_xticks(range(len(values)), labels, fontsize=9.5, color=t["ink2"])
    ax.set_ylim(0, 1.48)
    ax.set_ylabel("taban tahmine uygulanan çarpan", color=t["muted"],
                  fontsize=9)

    _title(fig, t, "Takvim katmanı: geçmişten ölçülen üç çarpan",
           "Her biri geçmiş ay sonlarındaki 5 oranın medyanı · sızıntısız: "
           "yalnız hedef tarihten önceki veri")
    return _save(fig, "04-takvim-carpanlari", theme)


# --------------------------------------------------------------------------
# F5 — Frozen backtest WMAPE (gruplu çubuk, iki pencere)
# --------------------------------------------------------------------------
def fig_backtest(theme):
    fig, t = _new(theme, (8.4, 4.3))
    ax = fig.add_axes([0.115, 0.15, 0.855, 0.55])
    _frame(ax, t)

    windows = list(DATA["backtest"].keys())
    models = [("naive", "Naive — geçen hafta"),
              ("dow_median", "DOW medyanı"),
              ("ours", "Bizim model — DOW × takvim")]
    x = list(range(len(windows)))
    w = 0.22
    for j, (key, _label) in enumerate(models):
        vals = [DATA["backtest"][win][key] for win in windows]
        pos = [i + (j - 1) * (w + 0.015) for i in x]
        ax.bar(pos, vals, width=w, color=t["cat"][j])
        for p, v in zip(pos, vals):
            ax.text(p, v + 0.016, _tr(v, 4), ha="center", fontsize=8.5,
                    color=t["ink"])

    ax.set_xticks(x, [w_.replace("\n", " · ") for w_ in windows],
                  fontsize=9.5, color=t["ink2"])
    ax.set_ylabel("WMAPE — düşük olan iyi", color=t["muted"], fontsize=9)
    ax.set_ylim(0, max(max(DATA["backtest"][w_].values())
                       for w_ in windows) * 1.20)

    _legend_row(fig, t, [(label, t["cat"][j])
                         for j, (_k, label) in enumerate(models)],
                y=0.81, ncols=3)
    _title(fig, t, "Takvim katmanı ay sonu haftasında farkı açıyor",
           "Tek atışlık (frozen) backtest: eğitim hedef tarihten önce "
           "kesiliyor, ufuk içinde yeniden eğitim yok")
    return _save(fig, "05-backtest-wmape", theme)


# --------------------------------------------------------------------------
# F6 — Veri temizleme: iki seviyenin bileşimi (%100 yığılmış çubuk)
# Ölçekler çok farklı (103.462 hücre vs 4.046 satır) olduğu için mutlak
# uzunluk yerine PAY gösterilir; mutlak sayılar etiket olarak durur.
# --------------------------------------------------------------------------
def fig_cleaning(theme):
    fig, t = _new(theme, (9.0, 3.9))
    ax = fig.add_axes([0.30, 0.24, 0.66, 0.44])
    _frame(ax, t, xgrid=True, ygrid=False)

    c = DATA["cleaning"]
    fv = DATA["forecast_vs_dow"]
    rows = [
        ("Eğitim geçmişi\n" + _tr(c["history_grid_rows"]) + " grid hücresi",
         c["training_grid_rows"], c["excluded_grid_rows"],
         "eğitimde kullanılan", "dışlanan tarihler"),
        ("Tahmin dosyası\n" + _tr(fv["rows"]) + " satır",
         fv["rows"] - fv["zero_rows"], fv["zero_rows"],
         "optimizasyona giden", "desi = 0 satır"),
    ]

    for i, (_label, keep, drop, _k, _d) in enumerate(rows):
        total = keep + drop
        keep_pct, drop_pct = 100 * keep / total, 100 * drop / total
        ax.barh([i], [keep_pct], height=0.30, color=t["cat"][0])
        ax.barh([i], [drop_pct], left=keep_pct + 0.5, height=0.30,
                color=t["cat"][1] if i == 0 else t["cat"][2])
        ax.text(keep_pct / 2, i, _tr(keep), va="center", ha="center",
                fontsize=9.5, color=t["on_fill"], fontweight="bold")
        ax.text(min(keep_pct + drop_pct + 3.5, 104), i,
                f"{_tr(drop)}  (%{_tr(drop_pct, 1)})", va="center", ha="left",
                fontsize=9, color=t["ink"])

    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=9.5,
                  color=t["ink2"])
    ax.invert_yaxis()
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 25, 50, 75, 100],
                  ["0", "%25", "%50", "%75", "%100"])
    ax.set_xlabel("satırların payı", color=t["muted"], fontsize=9)

    _legend_row(fig, t, [("Kullanılan", t["cat"][0]),
                         ("Eğitimden dışlanan 23 tarih", t["cat"][1]),
                         ("Tahmini 0 olan satır", t["cat"][2])],
                y=0.80, ncols=3)
    _title(fig, t, "Veri temizleme: ne eleniyor, ne kalıyor",
           f"{_tr(c['raw_rows'])} ham talep satırı · {c['history_days']} gün · "
           f"{c['od_in_history']} aktif OD çifti · {c['transfer_centres']} "
           "transfer merkezi\nDışlama YALNIZ eğitim verisine uygulanır; "
           "hedef günler asla elenmez. Sıfırlar Excel'de kalır, plana geçmez.")
    return _save(fig, "06-veri-temizleme", theme)


# --------------------------------------------------------------------------
# F7 — Spot araç doluluk dağılımı (ECDF), aşama aşama
# --------------------------------------------------------------------------
def fig_fill_ecdf(theme):
    height_in, axes_height = 4.4, 0.55
    y_span = 103
    fig, t = _new(theme, (8.6, height_in))
    ax = fig.add_axes([0.105, 0.155, 0.865, axes_height])
    _frame(ax, t)

    stages = ["Stage 0", "Stage 1", "Stage 2", "Stage 3"]
    names = ["Stage 0 · temel plan", "Stage 1 · onarım",
             "Stage 2 · milk-run", "Stage 3 · yük alma"]
    for i, stage in enumerate(stages):
        fills = sorted(DATA["stages"][stage]["spot_fills"])
        ys = [(k + 1) / len(fills) * 100 for k in range(len(fills))]
        ax.step([f * 100 for f in fills], ys, where="post",
                color=t["ord4"][i], linewidth=1.8, zorder=3 + i)

    ax.axvline(30, color=t["axis"], linewidth=0.8)
    ax.text(31.5, 97, "%30 doluluk eşiği", fontsize=8.5, color=t["muted"],
            va="top")
    shares = [100 * DATA["stages"][s]["spot_below_30"]
              / DATA["stages"][s]["spot_routes"] for s in stages]

    # The last two stages sit a couple of points apart on the threshold line,
    # so the labels are pushed apart to a readable minimum gap. The dots stay
    # on their true values; only the text moves.
    points_per_unit = height_in * axes_height * 72 / y_span
    min_gap, floor = 8.0, 5.0
    label_y = [0.0] * len(shares)
    lowest = floor
    for index in sorted(range(len(shares)), key=lambda k: shares[k]):
        lowest = max(shares[index], lowest)
        label_y[index] = lowest
        lowest += min_gap

    for i, (share, text_y) in enumerate(zip(shares, label_y)):
        ax.scatter([30], [share], s=50, color=t["ord4"][i], zorder=7,
                   edgecolors=t["surface"], linewidths=2)
        ax.annotate(f"%{share:.0f}", xy=(30, share),
                    xytext=(-10, (text_y - share) * points_per_unit),
                    textcoords="offset points", fontsize=9.5, ha="right",
                    va="center", color=t["ink"], fontweight="bold",
                    zorder=9)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, y_span)
    ax.xaxis.set_major_locator(MultipleLocator(20))
    ax.set_xlabel("fiziksel Spot aracın doluluk oranı (%)", color=t["muted"],
                  fontsize=9)
    ax.set_ylabel("araçların kümülatif payı (%)", color=t["muted"], fontsize=9)

    _legend_row(fig, t, [(name, t["ord4"][i]) for i, name in enumerate(names)],
                y=0.81, ncols=4)
    _title(fig, t, "Yarı boş araç kalmıyor: doluluk dağılımı sağa kayıyor",
           "Eğri ne kadar sağdaysa o kadar iyi · %30 altındaki araç payı "
           f"%{shares[0]:.0f} → %{shares[-1]:.0f}")
    return _save(fig, "07-doluluk-dagilimi", theme)


# --------------------------------------------------------------------------
# F8 — Fiziksel araç sayısı ve zincir uzunluğu bileşimi
# --------------------------------------------------------------------------
def fig_vehicles(theme):
    fig, t = _new(theme, (8.6, 4.4))
    ax = fig.add_axes([0.105, 0.135, 0.865, 0.56])
    _frame(ax, t)

    stages = ["Stage 0", "Stage 1", "Stage 2", "Stage 3"]
    sizes = ["1", "2", "3", "4"]
    names = ["tek bacak (direkt)", "2 duraklı zincir", "3 duraklı zincir",
             "4 duraklı zincir"]
    totals = [DATA["stages"][s]["routes"] for s in stages]
    gap = max(totals) * 0.006
    bottoms = [0.0] * len(stages)
    three_center = None

    for j, size in enumerate(sizes):
        vals = [DATA["stages"][s]["chain_size_counts"].get(size, 0)
                for s in stages]
        if not any(vals):
            continue
        ax.bar(range(len(stages)), vals, width=0.30, bottom=bottoms,
               color=t["ord4"][j])
        for i, v in enumerate(vals):
            if v >= 70:
                ax.text(i, bottoms[i] + v / 2, str(v), ha="center",
                        va="center", fontsize=9,
                        color=t["on_fill"] if j == 3 else t["ink"])
        if size == "3" and vals[-1]:
            three_center = (bottoms[-1] + vals[-1] / 2, vals[-1])
        bottoms = [b + v + (gap if v else 0) for b, v in zip(bottoms, vals)]

    for i, total in enumerate(totals):
        ax.text(i, bottoms[i] + max(totals) * 0.035, f"{_tr(total)} araç",
                ha="center", fontsize=11, color=t["ink"], fontweight="bold")
    # 3 duraklı dilim ince kaldığı için tek doğrudan etiketle dışarıda gösterilir
    if three_center is not None:
        height, count = three_center
        ax.annotate(f"{count} × 3 durak", xy=(len(stages) - 0.84, height),
                    xytext=(24, 6), textcoords="offset points", fontsize=8.5,
                    color=t["ink2"],
                    arrowprops=dict(arrowstyle="-", color=t["axis"],
                                    linewidth=0.8))

    ax.set_xticks(range(len(stages)), stages, fontsize=10, color=t["ink2"])
    ax.set_ylim(0, max(totals) * 1.16)
    ax.set_xlim(-0.6, len(stages) - 0.25)
    ax.set_ylabel("fiziksel araç sayısı", color=t["muted"], fontsize=9)

    _legend_row(fig, t, [(name, t["ord4"][j]) for j, name in enumerate(names)],
                y=0.82, ncols=4)
    _title(fig, t,
           f"{_tr(totals[0])} araç → {_tr(totals[-1])} araç, aynı yükü taşıyarak",
           "Bir zincir k kaynağı TEK fiziksel araca indirir; Stage 3 ayrıca "
           "bir ara durakta\nyeni yük alarak "
           f"{DATA['pickup_metrics']['donor_vehicles_removed']} aracı daha "
           "gereksiz kılar (Jüri S6, S11.1)")
    return _save(fig, "08-arac-sayisi-zincir", theme)


# --------------------------------------------------------------------------
# F9 — Araç türü karması, aşama aşama (gruplu çubuk)
# --------------------------------------------------------------------------
def fig_vehicle_mix(theme):
    fig, t = _new(theme, (8.6, 4.3))
    ax = fig.add_axes([0.105, 0.135, 0.865, 0.56])
    _frame(ax, t)

    stages = ["Stage 0", "Stage 1", "Stage 2", "Stage 3"]
    types = ["Kamyonet", "Hafif Kamyon", "Kamyon", "Tır"]
    x = list(range(len(stages)))
    w = 0.18
    for j, vtype in enumerate(types):
        vals = [DATA["stages"][s]["vehicle_mix"].get(vtype, 0) for s in stages]
        pos = [i + (j - 1.5) * (w + 0.015) for i in x]
        ax.bar(pos, vals, width=w, color=t["cat"][j])
        for p, v in zip(pos, vals):
            ax.text(p, v + 26, str(v), ha="center", fontsize=8.5,
                    color=t["ink"])

    ax.set_xticks(x, stages, fontsize=10, color=t["ink2"])
    ax.set_ylabel("fiziksel araç sayısı", color=t["muted"], fontsize=9)
    ax.set_ylim(0, 1080)
    ax.yaxis.set_major_locator(MultipleLocator(250))

    _legend_row(fig, t, [(vtype, t["cat"][j])
                         for j, vtype in enumerate(types)], y=0.81, ncols=4)
    first_van = DATA["stages"][stages[0]]["vehicle_mix"].get("Kamyonet", 0)
    last_van = DATA["stages"][stages[-1]]["vehicle_mix"].get("Kamyonet", 0)
    _title(fig, t, "Karma küçük araçtan büyüğe kayıyor",
           f"{_tr(first_van)} Kamyonet → {_tr(last_van)}: küçük yükler "
           "birleşip daha az sayıda ama daha dolu Kamyon'a biniyor")
    return _save(fig, "09-arac-turu-karmasi", theme)


FIGURES = (fig_cost_cascade, fig_history_daily, fig_forecast_vs_dow,
           fig_calendar_multipliers, fig_backtest, fig_cleaning,
           fig_fill_ecdf, fig_vehicles, fig_vehicle_mix)


def main() -> None:
    written = []
    for builder in FIGURES:
        for theme in ("light", "dark"):
            written.append(builder(theme))
    for path in written:
        print(f"  {path.name}  ({path.stat().st_size/1024:.0f} KB)")
    print(f"{len(written)} figür yazıldı -> {HERE}")


if __name__ == "__main__":
    main()
