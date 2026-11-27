from datetime import datetime
from functools import cmp_to_key
import io
from zoneinfo import ZoneInfo

import pandas as pd
from weasyprint import HTML

from scorer import CFG, DOMAINS, STANDARDS, cmp_code_, ready_pct_

COMMITTEE_NAME_AR = "لجنة التقويم الخارجي الافتراضية"


def cls_css(p):
    return "ok" if p >= 90 else ("mid" if p >= 70 else "bad")


def esc(s):
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_pdf_bytes(stages):
    stamp = datetime.now(ZoneInfo("Asia/Riyadh")).strftime("%d-%m-%Y %H-%M")
    all_rows = [r for s in stages for r in s["rows"]]
    tot_ind = len(all_rows)
    tot_files = sum(s["summary"]["files"] for s in stages)
    tot_pct = (sum(r["pct"] for r in all_rows) / tot_ind) if tot_ind else 0.0
    tot_ready = sum(1 for r in all_rows if r["judg"] == "جاهز للزيارة")
    tot_ready_pct = (tot_ready * 100.0 / tot_ind) if tot_ind else 0.0
    tot_orphan = sum(s["summary"]["orphan"] for s in stages)
    tot_impact = sum(1 for r in all_rows if r["impact"])
    tot_ocr = sum(s["summary"].get("ocrScanned", 0) for s in stages)
    tot_unread = sum(s["summary"].get("unreadFiles", 0) for s in stages)

    css = """
    @page { size: A4; margin: 12mm; }
    body { font-family: 'DejaVu Sans', Arial, Tahoma, sans-serif; color: #14281F; font-size: 9pt; line-height: 1.5; }
    h1 { color: #0E3B28; font-size: 20pt; text-align: center; margin: 28mm 0 4mm; }
    h2 { color: #0E3B28; font-size: 14pt; border-bottom: 1.2pt solid #0E3B28; padding-bottom: 2mm; margin-top: 3mm; }
    h3 { color: #0E3B28; font-size: 11pt; border-right: 3pt solid #B99653; padding-right: 3mm; margin: 4mm 0 2mm; }
    table { width: 100%; border-collapse: collapse; font-size: 7.8pt; margin-top: 2mm; }
    th { background: #0E3B28; color: #fff; padding: 1.6mm; }
    td { border: 0.6pt solid #D7E0D9; padding: 1.3mm; vertical-align: top; }
    .c { text-align: center; }
    .ok { color: #0E3B28; font-weight: 700; }
    .mid { color: #8A6D2F; font-weight: 700; }
    .bad { color: #B3261E; font-weight: 700; }
    .kpi { display: inline-block; width: 23%; border: 0.8pt solid #D7E0D9; border-top: 2.5pt solid #0E3B28; padding: 2.5mm; margin: 1mm; text-align: center; }
    .kpi b { display: block; font-size: 14pt; color: #0E3B28; }
    .note { background: #FBF8F1; border-right: 2.5pt solid #B99653; padding: 2.5mm 3.5mm; margin: 2.5mm 0; font-size: 8.5pt; }
    ul { margin: 0; padding-right: 4mm; }
    li { margin: 0.5mm 0; }
    .pb { page-break-before: always; }
    .small { font-size: 7.5pt; color: #5B6B61; }
    """

    html = [
        f'<html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>{css}</style></head><body>',
        f'<h1>{esc(COMMITTEE_NAME_AR)}<br><span style="font-size:14pt;color:#0E3B28">تقرير الإنجاز وجاهزية الزيارة</span><br>'
        f'<span style="font-size:12pt;color:#5B6B61">المراحل السبع · حد الشواهد: {CFG["MIN_EV"]}</span></h1>',
        '<div style="text-align:center;margin-top:8mm">',
        f'<div class="kpi"><b>{tot_ind}</b>مؤشراً مفحوصاً</div>',
        f'<div class="kpi"><b>{tot_pct:.0f}%</b>نسبة الإنجاز</div>',
        f'<div class="kpi"><b>{tot_ready_pct:.1f}%</b>نسبة الجاهزية ({tot_ready} من {tot_ind})</div>',
        f'<div class="kpi"><b>{tot_files}</b>ملفاً (OCR: {tot_ocr} / غير مقروء: {tot_unread})</div>',
        "</div>",
        f'<p style="text-align:center;margin-top:10mm" class="small">صدر في {esc(stamp)} · قراءة فقط: لم يُحذف ولم يُنقل ولم يُعدَّل أي ملف</p>',
        '<div class="pb"><h2>أولاً: ملخص المراحل السبع</h2><table>',
        "<tr><th>المرحلة</th><th>مؤشرات</th><th>ملفات</th><th>OCR</th><th>غير مقروء</th><th>الإنجاز</th><th>الجاهزية</th><th>جاهزة</th><th>فجوات</th><th>بلا أدلة</th><th>تحتاج أداة</th><th>بشاهد أثر</th><th>خارج المؤشرات</th></tr>",
    ]

    for s in stages:
        m = s["summary"]
        rp = ready_pct_(m)
        html.append(
            f'<tr><td>{esc(m["name"])}</td><td class="c">{m["indicators"]}</td><td class="c">{m["files"]}</td>'
            f'<td class="c">{m.get("ocrScanned", 0)}</td><td class="c">{m.get("unreadFiles", 0)}</td>'
            f'<td class="c {cls_css(m["pct"])}">{m["pct"]:.1f}%</td>'
            f'<td class="c {cls_css(rp)}"><b>{rp:.1f}%</b></td>'
            f'<td class="c">{m["ready"]}</td><td class="c">{m["gap"]}</td><td class="c">{m["noev"]}</td>'
            f'<td class="c">{m["needtool"]}</td><td class="c">{m["impact"]}</td><td class="c">{m["orphan"]}</td></tr>'
        )

    html.append(
        f'<tr style="font-weight:700;background:#EAF0EA"><td>الإجمالي</td><td class="c">{tot_ind}</td>'
        f'<td class="c">{tot_files}</td><td class="c">{tot_ocr}</td><td class="c">{tot_unread}</td>'
        f'<td class="c">{tot_pct:.1f}%</td><td class="c"><b>{tot_ready_pct:.1f}%</b></td><td class="c">{tot_ready}</td>'
        f'<td class="c">{sum(s["summary"]["gap"] for s in stages)}</td>'
        f'<td class="c">{sum(s["summary"]["noev"] for s in stages)}</td>'
        f'<td class="c">{sum(s["summary"]["needtool"] for s in stages)}</td>'
        f'<td class="c">{tot_impact}</td><td class="c">{tot_orphan}</td></tr></table>'
    )

    freq = {}
    for r in all_rows:
        if r["judg"] == "جاهز للزيارة":
            continue
        item = freq.setdefault(r["code"], {"code": r["code"], "title": r["title"], "stages": 0, "low": 0})
        item["stages"] += 1
        if r["pct"] < 60:
            item["low"] += 1

    top = sorted(
        freq.values(),
        key=cmp_to_key(
            lambda a, b: (b["stages"] - a["stages"]) or (a["low"] - b["low"]) or cmp_code_(a["code"], b["code"])
        ),
    )[:12]

    html.append("<h3>المؤشرات الأكثر تكراراً في الفجوات عبر المراحل</h3><table><tr><th>الرمز</th><th>المؤشر</th><th>عدد المراحل المتعثرة فيه</th></tr>")
    for t in top:
        html.append(f'<tr><td>{esc(t["code"])}</td><td>{esc(t["title"])}</td><td class="c">{t["stages"]}</td></tr>')
    html.append("</table></div>")

    for s in stages:
        m = s["summary"]
        html.append(
            f'<div class="pb"><h2>{esc(m["name"])}</h2>'
            f'<div class="note"><b>الإنجاز {m["pct"]:.1f}%</b> · {m["indicators"]} مؤشراً · {m["folders"]} مجلد مؤشر · '
            f'{m["files"]} ملفاً (مقروء داخلياً: {m.get("textExtracted", 0)} / عبر OCR: {m.get("ocrScanned", 0)} / غير مقروء: {m.get("unreadFiles", 0)}) · '
            f'جاهزة {m["ready"]} · فجوات {m["gap"]} · بلا أدلة {m["noev"]} · تحتاج أداة {m["needtool"]} · بشاهد أثر {m["impact"]} من {m["indicators"]}.</div>'
        )
        if m.get("orphan"):
            html.append(f'<div class="note"><b>{m["orphan"]} ملفاً خارج مجلدات المؤشرات.</b><ul>')
            for g in m.get("orphanGroups", [])[:8]:
                html.append(f'<li>{esc(g["folder"])} — {g["count"]} ملفاً: تُنقل إلى مجلد المؤشر المناسب</li>')
            html.append("</ul></div>")

        for d in ["1", "2", "3", "4"]:
            rr = [r for r in s["rows"] if r["dom"] == d]
            if not rr:
                continue
            p = sum(r["pct"] for r in rr) / len(rr)
            rdy = sum(1 for r in rr if r["judg"] == "جاهز للزيارة")
            html.append(
                f'<h3>المجال {d}: {esc(DOMAINS[d])} — {p:.0f}% · جاهز {rdy} من {len(rr)}</h3>'
                '<table><tr><th style="width:9%">الرمز</th><th style="width:28%">المؤشر</th><th style="width:6%">ملفات</th>'
                '<th style="width:6%">فريد</th><th style="width:7%">الإنجاز</th><th style="width:12%">الحكم</th><th>الاقتراحات للتحسين</th></tr>'
            )
            for r in rr:
                sug_html = (
                    "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in r["suggestions"]) + "</ul>"
                    if r["suggestions"]
                    else "—"
                )
                html.append(
                    f'<tr><td>{esc(r["code"])}</td><td>{esc(r["title"])}</td><td class="c">{r["total"]}</td>'
                    f'<td class="c">{r["uniq"]}</td><td class="c {cls_css(r["pct"])}">{round(r["pct"])}%</td>'
                    f'<td class="c">{esc(r["judg"])}</td><td>{sug_html}</td></tr>'
                )
            html.append("</table>")
        html.append("</div>")

    html.append(
        f'<div class="pb"><h2>منهجية الحساب — {esc(COMMITTEE_NAME_AR)}</h2>'
        "<table><tr><th>العنصر</th><th>الوزن</th><th>شرط التحقق</th></tr>"
        f'<tr><td>كفاية الشواهد</td><td class="c">50%</td><td>{CFG["MIN_EV"]} شواهد غير مكررة على الأقل</td></tr>'
        '<tr><td>ممارسة فعلية موثقة</td><td class="c">25%</td><td>صور أو فيديو أو محضر تنفيذ أو كشف أو سجل (في الاسم أو النص/الصورة)</td></tr>'
        '<tr><td>أثر مقيس</td><td class="c">25%</td><td>قياس قبلي/بعدي أو تحليل نتائج أو مقارنة أو مؤشر أداء (في الاسم أو المحتوى الداخلي/OCR)</td></tr>'
        '<tr><td>أداة غير الوثائق</td><td class="c">سقف 75%</td><td>إذا تطلّبها المؤشر ولم تُرفع استبانة أو مقابلة أو ملاحظة</td></tr></table>'
        '<div class="note"><b>حدّ التقرير:</b> يجمع الفحص بين اسم الملف والنص المستخرج من المستندات والصور عبر OCR؛ وتظل المراجعة النهائية لعينة من الشواهد ضرورية قبل الاستشهاد بالأرقام أمام الزائر.</div>'
        "</div></body></html>"
    )

    return HTML(string="".join(html)).write_pdf()


def build_excel_bytes(stages):
    rows = []
    for st in stages:
        st_name = st["summary"]["name"]
        for r in st["rows"]:
            rows.append({
                "المرحلة": st_name,
                "المجال": DOMAINS.get(r["dom"], r["dom"]),
                "المعيار": STANDARDS.get(r["std"], r["std"]),
                "الرمز": r["code"],
                "المؤشر": r["title"],
                "عدد الملفات": r["total"],
                "فريد": r["uniq"],
                "مكرر": r["dup"],
                "ملفات غير مقروءة": r.get("unreadFiles", 0),
                "ممارسة": "نعم" if r["practice"] else "لا",
                "أثر مقيس": "نعم" if r["impact"] else "لا",
                "أداة": "نعم" if r["tool"] else ("لا" if r["needs"] else "—"),
                "الإنجاز %": round(r["pct"]),
                "الحكم": r["judg"],
                "عدد المجلدات": r["nfold"],
                "رابط المجلد": r["url"],
                "الاقتراحات": " | ".join(r["suggestions"]),
            })
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="المؤشرات")
    return buf.getvalue()
