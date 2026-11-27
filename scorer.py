from functools import cmp_to_key
import re
import unicodedata

CFG = {
    "OUTPUT_FOLDER_ID": "1KxODDele62TscOuw8w0jXo21a2JTA1gj",
    "SCHOOL_EMAIL": "sahmaschool0@gmail.com",
    "MIN_EV": 6,
    "ROOTS": [
        {"key": "R1", "name": "ابتدائية سهما الأهلية", "code": "S-174744", "id": "1KqHlrWDCWhkjAT5FHABwAdyIfWcrxtyV", "kg": False},
        {"key": "R2", "name": "ابتدائية الدبلومة الأمريكية", "code": "S-174779", "id": "18g_qW9YaZpJf1yTVvWSzVUKaMaLtkOBt", "kg": False},
        {"key": "R3", "name": "متوسطة سهما الأهلية", "code": "S-174780", "id": "1I3YcgWNdnX7bRdba7stm7aagNL87gU6m", "kg": False},
        {"key": "R4", "name": "متوسطة الدبلومة الأمريكية", "code": "", "id": "12DFfGqR7GJHefB1JJajMGlq2Dj321uTr", "kg": False},
        {"key": "R5", "name": "ثانوية سهما الأهلية", "code": "", "id": "1-0zlKB4f0wppDu7EPjuvuWRMTTHmCDQM", "kg": False},
        {"key": "R6", "name": "روضة سهما الأهلية", "code": "", "id": "1w01kM0Yx4OyyxgxysIgCuHOjIIeH4rgQ", "kg": True},
        {"key": "R7", "name": "روضة الدبلومة الأمريكية", "code": "", "id": "17BJhENYDSA20vmk8wdihBCMueGiog-RW", "kg": True},
    ],
}

MASTER = {
    "domains": {
        "1": "الإدارة المدرسية",
        "2": "التعليم والتعلم",
        "3": "نواتج التعلم",
        "4": "البيئة المدرسية",
    },
    "standards": {
        "1-1": "التخطيط",
        "1-2": "قيادة العملية التعليمية",
        "1-3": "المجتمع المدرسي",
        "1-4": "التطوير المؤسسي",
        "1-5": "حقوق المتعلم وحمايته",
        "2-1": "بناء خبرات التعلم",
        "2-2": "تقويم التعلم",
        "3-1": "التحصيل التعليمي",
        "3-2": "التطور الشخصي والصحي والاجتماعي",
        "4-1": "المبنى المدرسي",
        "4-2": "الأمن والسلامة",
    },
    "indicators": {
        "1-1-1-1": "تضع المدرسة خطة تشغيلية شاملة وفق أهداف تطويرية محددة.",
        "1-1-1-2": "تتابع المدرسة تنفيذ خطتها التشغيلية وتطورها بما يضمن تحقيق أهدافها.",
        "1-2-1-1": "تعزز المدرسة القيم الإسلامية، والهوية الوطنية.",
        "1-2-1-2": "تطبق المدرسة قيم مهنة التعليم وأخلاقياتها، وتتابع الالتزام بها.",
        "1-2-1-3": "تطبق المدرسة إجراءات محددة؛ لدعم الانضباط المدرسي، وتتابع الالتزام بها.",
        "1-2-1-4": "تنفذ المدرسة برامج وأنشطة تربوية داعمة للسلوك الإيجابي لدى المتعلمين، ومنهم ذوو الإعاقة والموهوبون، وتتابعها.",
        "1-2-1-5": "تنفذ المدرسة برامج وأنشطة إثرائية؛ لتطوير مواهب المتعلمين، وتهيئهم للمستقبل، وتتابعها.",
        "1-3-1-1": "تعزز المدرسة بناء العلاقات الإيجابية والتعاون في المجتمع المدرسي.",
        "1-3-1-2": "تعزز المدرسة مشاركة الأسرة في تعلم أبنائهم، والتحضير لمستقبلهم.",
        "1-3-1-3": "تعزز المدرسة الشراكة المجتمعية؛ لدعم التعلم والتأثير الإيجابي في المجتمع.",
        "1-4-1-1": "توفر المدرسة كادرًا تعليميًا مكتملًا ومؤهلًا بما يتسق مع المهام الموكلة له.",
        "1-4-1-2": "توفر المدرسة كادرًا إداريًا مكتملًا ومؤهلًا بما يتسق مع المهام الموكلة له.",
        "1-4-1-3": "تظهر المدرسة الملاءة والاستدامة المالية.",
        "1-4-1-4": "تدعم المدرسة منسوبيها للحصول على الرخصة المهنية، وتتابعها.",
        "1-4-1-5": "تدعم المدرسة التطوير المهني لمنسوبيها وفقًا لنتائج التقويم وتحليل احتياجاتهم.",
        "1-4-1-6": "تطبق المدرسة التقويم الذاتي المبني على المعايير المعتمدة من الهيئة بشكل مستمر.",
        "1-4-1-7": "تنفذ المدرسة خطة التحسين بناءً على نتائج التقويم المدرسي، وتتابعها.",
        "1-5-1-1": "تلتزم المدرسة بالمحافظة على حقوق المتعلمين، وحمايتهم.",
        "1-5-1-2": "توفر المدرسة مناخًا آمنًا للتعلم والنمو نفسيًا واجتماعيًا.",
        "2-1-1-1": "توفر المدرسة فرصًا متكافئة للتعلم تلبي احتياجات المتعلمين، ومنهم ذوو الإعاقة والموهوبون.",
        "2-1-1-2": "تدعم المدرسة تنفيذ المناهج بما يحقق نواتج التعلم المستهدفة.",
        "2-1-1-3": "تنوع المدرسة في استراتيجيات التعليم والتعلم؛ لتلبية احتياجات المتعلمين، ودعم تعلمهم.",
        "2-1-1-4": "تفعل المدرسة التقنية الرقمية؛ لدعم تعلم المتعلمين وتلبية احتياجاتهم.",
        "2-1-1-5": "تنفذ المدرسة أنشطة تعلم تطبيقية ترتبط بحياة المتعلمين.",
        "2-1-1-6": "تنمي المدرسة المهارات القرائية والعددية الأساسية لدى المتعلمين.",
        "2-1-1-7": "تنمي المدرسة مهارات التفكير والبحث والابتكار لدى المتعلمين.",
        "2-1-1-8": "تنمي المدرسة المهارات العاطفية والاجتماعية لدى المتعلمين.",
        "2-1-1-9": "تعزز المدرسة دافعية المتعلمين للتعلم، والاستمتاع به.",
        "2-2-1-1": "تطبق المدرسة أساليب وأدوات تقويم متنوعة؛ للكشف عن مستويات أداء المتعلمين المختلفة.",
        "2-2-1-2": "تطبق المدرسة أساليب وأدوات متنوعة؛ لتقويم نواتج التعلم المستهدفة في مناهج التعليم.",
        "2-2-1-3": "تحلل المدرسة نتائج التقويم، وتوظفها في تحسين عمليات التعليم والتعلم والتقويم.",
        "2-2-1-4": "تقدم المدرسة التغذية الراجعة للمتعلمين وأولياء أمورهم، وتتابع تقدمهم بشكل مستمر.",
        "3-1-1-1": "يحقق المتعلمون نتائج مرتفعة في مجال القراءة وفقًا للاختبارات الوطنية.",
        "3-1-1-2": "يحقق المتعلمون نتائج مرتفعة في مجال الرياضيات وفقًا للاختبارات الوطنية.",
        "3-1-1-3": "يحقق المتعلمون نتائج مرتفعة في مجال العلوم وفقًا للاختبارات الوطنية.",
        "3-1-1-4": "يحقق المتعلمون تقدمًا في مجال القراءة قياسًا على مستوى أداء المدرسة السابق في الاختبارات الوطنية.",
        "3-1-1-5": "يحقق المتعلمون تقدمًا في مجال الرياضيات قياسًا على مستوى أداء المدرسة السابق في الاختبارات الوطنية.",
        "3-1-1-6": "يحقق المتعلمون تقدمًا في مجال العلوم قياسًا على مستوى أداء المدرسة السابق في الاختبارات الوطنية.",
        "3-2-1-1": "يظهر المتعلمون الاعتزاز بالقيم والهوية الوطنية.",
        "3-2-1-2": "يظهر المتعلمون اتجاهات إيجابية نحو ذواتهم والآخرين.",
        "3-2-1-3": "يظهر المتعلمون التزامًا بالممارسات الصحية السليمة.",
        "3-2-1-4": "يشارك المتعلمون في الأنشطة المجتمعية والأعمال التطوعية.",
        "3-2-1-5": "يلتزم المتعلمون بقواعد السلوك والانضباط المدرسي.",
        "3-2-1-6": "يظهر المتعلمون الاستقلالية، والقدرة على التعلم الذاتي.",
        "3-2-1-7": "يظهر المتعلمون اعتزازًا بثقافتهم واحترامًا للتنوع الثقافي في المجتمع.",
        "4-1-1-1": "توفر المدرسة مبنى تعليميًا يستوفي المواصفات والاشتراطات المعتمدة من حيث النوع والخدمات المساندة.",
        "4-1-1-2": "تنظيم مبنى المدرسة ملائم لعدد المتعلمين وخصائص المرحلة العمرية، ومنهم ذوو الإعاقة.",
        "4-1-1-3": "تتوافر فصول ومعامل ملائمة للعملية التعليمية تلبي احتياجات المتعلمين، ومنهم ذوو الإعاقة.",
        "4-1-1-4": "تلبي المرافق والتجهيزات والخدمات المساندة احتياجات المتعلمين، ومنهم ذوو الإعاقة.",
        "4-2-1-1": "تتوافر في مبنى المدرسة ومرافقها جميع متطلبات الأمن والسلامة.",
        "4-2-1-2": "تتابع المدرسة صيانة المبنى وجميع مرافقه وتجهيزاته بشكل دوري.",
        "4-2-1-3": "تتابع المدرسة نظافة المبنى المدرسي وجميع مرافقه بشكل مستمر.",
    },
}

INDICATORS = MASTER["indicators"]
DOMAINS = MASTER["domains"]
STANDARDS = MASTER["standards"]


def range_(prefix, a, b):
    return [f"{prefix}{i}" for i in range(a, b + 1)]


KG_CODES = (
    ["1-1-1-1", "1-1-1-2"]
    + range_("1-2-1-", 1, 5)
    + range_("1-3-1-", 1, 3)
    + range_("1-4-1-", 1, 4)
    + range_("2-1-1-", 1, 11)
    + range_("2-2-1-", 1, 3)
    + range_("3-1-1-", 1, 6)
    + range_("4-1-1-", 1, 3)
    + range_("4-2-1-", 1, 3)
)

KW_PRACTICE = [
    "صور", "صوره", "فيديو", "تنفيذ", "محضر", "جوله", "ورشه",
    "لقاء", "فعاليه", "مشاركه", "نشاط", "تطبيق", "كشف", "سجل",
]
KW_IMPACT = [
    "اثر", "نتائج", "تحليل", "قياس", "قبلي", "بعدي",
    "مقارنه", "تحسن", "حصاد", "تقرير ختامي", "مؤشر الاداء",
]
KW_TOOL = [
    "استبانه", "استبيان", "مقابله", "ملاحظه",
    "زياره صفيه", "تقويم اداء", "اختبار", "عينه",
]
NEEDS_TOOL = [
    "1-2-1-2", "1-3-1-1", "1-5-1-2", "2-1-1-2",
    "2-2-1-1", "2-2-1-2", "3-2-1-1", "3-2-1-2",
]

TOOL_SUGGEST = {
    "1-2-1-2": "استبانة لعينة من الكادر التعليمي عن الالتزام بقيم المهنة، قبل البرنامج وبعده، مع جدول مقارنة",
    "1-3-1-1": "استبانة لأولياء الأمور عن العلاقات الإيجابية والتعاون، وتُرفع نتائجها كجدول مقارنة",
    "1-5-1-2": "استبانة الأمن النفسي للمتعلمين قبل برنامج الدعم وبعده، مع تحليل النتائج",
    "2-1-1-2": "بطاقة ملاحظة صفية لتنفيذ المنهج بمعايير محددة، وتُطبَّق على عينة من الحصص",
    "2-2-1-1": "اختبار تشخيصي قبلي وبعدي مع جدول تحليل النتائج لكل مستوى",
    "2-2-1-2": "أدوات تقويم متنوعة: مهام أداء ومعيار تصحيح (Rubric) لقياس نواتج التعلم",
    "3-2-1-1": "استبانة اعتزاز بالقيم والهوية الوطنية، قبلية وبعدية",
    "3-2-1-2": "مقياس الاتجاهات نحو الذات والآخرين، استبانة قبلية وبعدية",
}


def norm_(s):
    x = unicodedata.normalize("NFKC", str(s or "")).lower()
    x = re.sub(r"[\u064b-\u065f\u0670\u200e\u200f]", "", x)
    x = re.sub(r"[أإآ]", "ا", x).replace("ى", "ي").replace("ة", "ه")
    x = re.sub(r"^\[مكرر[^\]]*\]\s*", "", x)
    x = re.sub(r"\.[a-z0-9]{1,5}$", "", x)
    return re.sub(r"[\s_\-–—]+", " ", x).strip()


def hit_any_(text, kws):
    n = norm_(text)
    return any(k in n for k in kws)


def has_quantitative_impact_(text):
    n = norm_(text)
    has_pct = bool(re.search(r"\d+(?:[.,]\d+)?\s*%", n))
    has_comp = any(w in n for w in ["قبلي", "بعدي", "مقارنه", "تحسن", "نسبه", "نتائج", "تحليل", "قياس"])
    return has_pct or (has_comp and bool(re.search(r"\d+", n)))


def code_of_(name):
    m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})", str(name or ""))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}" if m else None


def cmp_code_(a, b):
    x = [int(v) for v in a.split("-")]
    y = [int(v) for v in b.split("-")]
    for i in range(4):
        if x[i] != y[i]:
            return x[i] - y[i]
    return 0


def ready_pct_(m):
    return (m["ready"] * 100.0 / m["indicators"]) if m["indicators"] else 0.0


def with_ready_(m):
    o = dict(m)
    o["readyPct"] = ready_pct_(m)
    return o


def suggest_(r):
    s = []
    if not r["inFramework"]:
        return ["هذا الرمز خارج الإطار المعتمد للمرحلة — يُراجع تصنيف المجلد"]
    if r["judg"] == "جاهز للزيارة":
        return [f"جاهز ({r['uniq']} شواهد): يُحدَّث تاريخ آخر شاهد قبل الزيارة، دون إضافة ملفات مكررة"]
    if r["nfold"] == 0:
        s.append(f"لا يوجد مجلد لهذا المؤشر في المرحلة: يُنشأ مجلد يبدأ برمزه ثم تُرفع {CFG['MIN_EV']} شواهد مختلفة على الأقل")
    if r["uniq"] < CFG["MIN_EV"]:
        s.append(f"ينقص {CFG['MIN_EV'] - r['uniq']} شاهد (المطلوب {CFG['MIN_EV']}): تُرفع شواهد مختلفة تثبت التنفيذ والأثر، لا نسخاً مكررة")
    if r["needs"] and not r["tool"]:
        s.append("أداة قياس: " + (TOOL_SUGGEST.get(r["code"]) or "استبانة أو بطاقة ملاحظة قبل التنفيذ وبعده لعينة من المستفيدين"))
    if not r["practice"]:
        s.append("دليل ممارسة موثق: صورة الفعالية أو الجلسة مع لوحة تحمل التاريخ، أو محضر تنفيذ موقّع، أو نص يوضح التنفيذ")
    if not r["impact"]:
        s.append("شاهد أثر: مقارنة رقمية قبلية وبعدية أو تحليل نتائج مقيس داخل الملف أو الصورة")
    if r["unreadFiles"] > 0:
        s.append(f"{r['unreadFiles']} ملف لم يُستخرج منه نص واضح (ممسوح أو صورة بلا نص أو كبير): يُراجع وضوح الكتابة فيه")
    if r["nfold"] > 1:
        s.append("تُوحَّد مجلدات المؤشر المتكررة في مجلد واحد")
    if r["dup"] > 0:
        s.append(f"{r['dup']} ملف مكرر: تُبقى نسخة واحدة وتُنقل البقية إلى مجلد المراجعة")
    return s


def score_row_(r):
    fs = r["files"]
    seen = {}
    uniq = 0
    dup = 0
    unread = 0
    for f in fs:
        txt_sig = norm_(f.get("extractedText", ""))[:180]
        k = f"{norm_(f.get('title'))}|{f.get('fileSize', '0')}|{txt_sig}"
        if k in seen:
            dup += 1
        else:
            seen[k] = 1
            uniq += 1
        if f.get("readStatus") in {"no_text", "weak_ocr", "skipped_large", "download_error", "parse_error"}:
            unread += 1

    combined_texts = [
        f"{f.get('title', '')}\n{f.get('extractedText', '')}"
        for f in fs
    ]
    mimes = [f.get("mimeType", "") for f in fs]

    practice = any(hit_any_(t, KW_PRACTICE) for t in combined_texts) or any(
        re.match(r"^(image|video)/", m or "") for m in mimes
    )
    impact = any(hit_any_(t, KW_IMPACT) or has_quantitative_impact_(t) for t in combined_texts)
    tool = any(hit_any_(t, KW_TOOL) for t in combined_texts)
    needs = r["code"] in NEEDS_TOOL

    pct = (
        min(1.0, uniq / CFG["MIN_EV"]) * 50.0
        + (25.0 if practice else 0.0)
        + (25.0 if impact else 0.0)
    )
    if needs and not tool:
        pct = min(pct, 75.0)

    if uniq < CFG["MIN_EV"]:
        judg = "لا تتوفر أدلة كافية"
    elif needs and not tool:
        judg = "يحتاج أداة قياس"
    elif pct >= 90.0:
        judg = "جاهز للزيارة"
    else:
        judg = "فجوة تستدعي التحسين"

    parts = r["code"].split("-")
    row = {
        "code": r["code"],
        "dom": parts[0],
        "std": "-".join(parts[:2]),
        "title": INDICATORS.get(r["code"], "مؤشر خارج قائمة الإطار المعتمد"),
        "inFramework": r["code"] in INDICATORS,
        "total": len(fs),
        "uniq": uniq,
        "dup": dup,
        "unreadFiles": unread,
        "practice": practice,
        "impact": impact,
        "tool": tool,
        "needs": needs,
        "nfold": r["nfold"],
        "pct": pct,
        "judg": judg,
        "schoolFiles": sum(1 for f in fs if f.get("owner") == CFG["SCHOOL_EMAIL"]),
        "url": r["urls"][0] if r["urls"] else "",
        "folderTitles": r["titles"],
    }
    row["suggestions"] = suggest_(row)
    return row


def owner_folder_(pid, fmap, ind_folder):
    depth = 0
    while pid and depth < 15:
        if pid in ind_folder:
            return pid
        p = fmap.get(pid)
        if not p:
            return None
        pid = p.get("parentId")
        depth += 1
    return None


def compute_stage(stage, folders, files):
    fmap = {f["id"]: f for f in folders}
    ind_folder = {}
    for f in folders:
        c = code_of_(f.get("title"))
        if c:
            ind_folder[f["id"]] = c

    by_code = {}

    def ensure(c):
        if c not in by_code:
            by_code[c] = {"code": c, "titles": [], "urls": [], "nfold": 0, "files": []}
        return by_code[c]

    for fid, c in ind_folder.items():
        rec = ensure(c)
        rec["titles"].append(fmap[fid].get("title", ""))
        rec["urls"].append(fmap[fid].get("viewUrl", ""))
        rec["nfold"] += 1

    orphans = []
    for f in files:
        o = owner_folder_(f.get("parentId"), fmap, ind_folder)
        if o:
            ensure(ind_folder[o])["files"].append(f)
        else:
            orphans.append(f)

    expected = KG_CODES if stage.get("kg") else list(INDICATORS.keys())
    for c in expected:
        ensure(c)

    rows = [score_row_(by_code[c]) for c in by_code]
    rows.sort(key=cmp_to_key(lambda a, b: cmp_code_(a["code"], b["code"])))

    orphan_map = {}
    for f in orphans:
        p = fmap.get(f.get("parentId"))
        k = p["title"] if p else "جذر المرحلة"
        orphan_map[k] = orphan_map.get(k, 0) + 1

    orphan_groups = [
        {"folder": k, "count": v}
        for k, v in sorted(orphan_map.items(), key=lambda x: x[1], reverse=True)
    ]

    n = len(rows) or 1
    ocr_scanned = sum(1 for f in files if f.get("contentSource") == "ocr")
    text_extracted = sum(1 for f in files if f.get("contentSource") in {"text", "ocr"})
    unread_total = sum(
        1 for f in files
        if f.get("readStatus") in {"no_text", "weak_ocr", "skipped_large", "download_error", "parse_error"}
    )

    summary = {
        "key": stage["key"],
        "name": stage["name"],
        "kg": stage.get("kg", False),
        "minEv": CFG["MIN_EV"],
        "indicators": len(rows),
        "folders": len(ind_folder),
        "files": len(files),
        "textExtracted": text_extracted,
        "ocrScanned": ocr_scanned,
        "unreadFiles": unread_total,
        "orphan": len(orphans),
        "orphanGroups": orphan_groups,
        "pct": sum(r["pct"] for r in rows) / n,
        "ready": sum(1 for r in rows if r["judg"] == "جاهز للزيارة"),
        "gap": sum(1 for r in rows if r["judg"] == "فجوة تستدعي التحسين"),
        "noev": sum(1 for r in rows if r["judg"] == "لا تتوفر أدلة كافية"),
        "needtool": sum(1 for r in rows if r["judg"] == "يحتاج أداة قياس"),
        "impact": sum(1 for r in rows if r["impact"]),
        "practice": sum(1 for r in rows if r["practice"]),
        "dup": sum(r["dup"] for r in rows),
        "outside": sum(1 for r in rows if not r["inFramework"]),
    }
    return {"summary": summary, "rows": rows}
