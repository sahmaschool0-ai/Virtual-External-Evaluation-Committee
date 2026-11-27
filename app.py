import json
import os
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from reporter import build_excel_bytes, build_pdf_bytes
from scanner import build_drive_service, scan_root
from scorer import CFG, DOMAINS, compute_stage, with_ready_

APP_TITLE_AR = "لجنة التقويم الخارجي الافتراضية"
APP_SUBTITLE_AR = (
    f"المراحل السبع · حد الشواهد: {CFG['MIN_EV']} · قراءة فقط وفحص المحتوى والصور (OCR): "
    "لا يُحذف ولا يُنقل ولا يُعدَّل أي ملف"
)

st.set_page_config(page_title=APP_TITLE_AR, layout="wide")

st.markdown(
    """
    <style>
    .stApp { direction: rtl; font-family: Tahoma, Arial, sans-serif; }
    .banner { background: #0E3B28; color: #fff; padding: 14px 18px; border-radius: 10px; margin-bottom: 14px; }
    .banner small { opacity: 0.88; display: block; margin-top: 4px; }
    .note { border-right: 4px solid #B99653; background: #FBF8F1; color: #14281F; padding: 10px 14px; border-radius: 8px; margin: 10px 0; }
    .foot { text-align: center; color: #5B6B61; font-size: 13px; margin-top: 28px; padding-top: 12px; border-top: 1px solid #D7E0D9; }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_cache_dir():
    d = os.path.join(tempfile.gettempdir(), "sahma_stages_cache")
    os.makedirs(d, exist_ok=True)
    return d


def stage_cache_path(key):
    return os.path.join(get_cache_dir(), f"stage-{key}.json")


def stage_partial_path(key):
    return os.path.join(get_cache_dir(), f"partial-{key}.json")


def load_cached_stages():
    loaded = {}
    for root in CFG["ROOTS"]:
        p = stage_cache_path(root["key"])
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    loaded[root["key"]] = json.load(fh)
            except Exception:
                pass
    return loaded


def load_partial_scan(key):
    p = stage_partial_path(key)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return None


def save_partial_scan(key, folders, files, scanned_ids):
    with open(stage_partial_path(key), "w", encoding="utf-8") as fh:
        json.dump(
            {
                "folders": folders,
                "files": files,
                "scanned_ids": list(scanned_ids),
                "updated_at": datetime.now(ZoneInfo("Asia/Riyadh")).strftime("%Y/%m/%d %H:%M"),
            },
            fh,
            ensure_ascii=False,
        )


def save_stage_cache(key, data):
    with open(stage_cache_path(key), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    # حذف الملف الجزئي بعد اكتمال المرحلة بالكامل
    pp = stage_partial_path(key)
    if os.path.exists(pp):
        os.remove(pp)


def clear_stage_cache(selected_keys=None):
    for root in CFG["ROOTS"]:
        if selected_keys and root["key"] not in selected_keys:
            continue
        for fn in (stage_cache_path(root["key"]), stage_partial_path(root["key"])):
            if os.path.exists(fn):
                os.remove(fn)


def get_service_account_info():
    if "gcp_service_account" in st.secrets:
        val = st.secrets["gcp_service_account"]
        if isinstance(val, str):
            return json.loads(val)
        return dict(val)
    return None


st.markdown(
    f'<div class="banner"><h2 style="margin:0;color:#fff;">{APP_TITLE_AR}</h2>'
    f"<small>{APP_SUBTITLE_AR}</small></div>",
    unsafe_allow_html=True,
)

sa_info = get_service_account_info()
with st.expander("إعدادات الفحص والمصادقة (اختياري إذا لم تُضبط في Secrets)"):
    inspect_contents = st.checkbox("فحص الكتابة داخل الملفات والصور (PDF / Word / Excel / OCR للصور)", value=True)
    step_mode = st.radio(
        "نمط التشغيل:",
        ["فحص مرحلي ذكي (يحفظ كل مؤشر/دفعة تلقائياً ويكمل الباقي)", "فحص مرحلة واحدة فقط في كل ضغطة زر"],
        index=0,
    )
    uploaded_sa = st.file_uploader("رفع ملف JSON لحساب الخدمة (Service Account) في حال عدم إضافته في Secrets", type=["json"])
    if uploaded_sa is not None:
        sa_info = json.load(uploaded_sa)

stages_map = load_cached_stages()

b1, b2, b3 = st.columns([2, 1, 1])
with b1:
    run_clicked = st.button("تشغيل / إكمال الفحص وبناء التقرير", type="primary", use_container_width=True)
with b2:
    refresh_clicked = st.button("تحديث الحالة", use_container_width=True)
with b3:
    reset_clicked = st.button("مسح نتائج الفحص المحفوظة", use_container_width=True)

if reset_clicked:
    clear_stage_cache()
    stages_map = {}
    st.info("تم مسح جميع نتائج الفحص المحفوظة مؤقتاً.")

if run_clicked:
    if not sa_info:
        st.error("يلزم توفير بيانات Service Account في st.secrets تحت مفتاح [gcp_service_account] أو رفع ملف JSON أعلاه للاتصال بـ Google Drive.")
    else:
        drive_svc = build_drive_service(sa_info)
        prog = st.progress(0.0)
        status_box = st.empty()
        total_roots = len(CFG["ROOTS"])
        partial_stop = False

        for idx, root in enumerate(CFG["ROOTS"]):
            prog.progress(idx / total_roots)
            if root["key"] in stages_map:
                continue

            # تحميل أي تقدم جزئي محفوظ مسبقاً لهذه المرحلة
            prev_partial = load_partial_scan(root["key"])
            prev_count = len(prev_partial["scanned_ids"]) if prev_partial else 0
            extra_msg = f" (استكمال من {prev_count} عنصر مفحوص مسبقاً)" if prev_count else ""

            status_box.info(
                f"جارٍ فحص المرحلة وقراءة المؤشرات والملفات: {root['name']} ({idx + 1}/{total_roots}){extra_msg}..."
            )

            # نمرر دالة حفظ فورية (checkpoint) وتقليص الميزانية الزمنية للدفعة إلى 90 ثانية لضمان الحفظ قبل المهلة
            def checkpoint_cb(folders, files, scanned_ids, _k=root["key"], _r=root):
                save_partial_scan(_k, folders, files, scanned_ids)

            try:
                scanned = scan_root(
                    drive_svc,
                    root,
                    budget_seconds=90,
                    inspect_contents=inspect_contents,
                    resume_state=prev_partial,
                    on_checkpoint=checkpoint_cb,
                )
            except TypeError:
                # توافق احتياطي في حال لم يُحدَّث scanner.py بعد
                scanned = scan_root(drive_svc, root, budget_seconds=90, inspect_contents=inspect_contents)

            if scanned is None or scanned.get("partial"):
                if scanned and scanned.get("partial"):
                    save_partial_scan(
                        root["key"],
                        scanned["folders"],
                        scanned["files"],
                        scanned.get("scanned_ids", []),
                    )
                    # حساب وعرض المؤشرات المفحوصة حتى اللحظة داخل المرحلة!
                    temp_stage = compute_stage(root, scanned["folders"], scanned["files"])
                    done_inds = sum(1 for r in temp_stage["rows"] if r["total"] > 0)
                    tot_inds = len(temp_stage["rows"])
                    st.warning(
                        f"توقّف مؤقت لحفظ التقدم في: {root['name']} — تم حفظ ({done_inds} من {tot_inds} مؤشراً). "
                        "اضغطي «تشغيل / إكمال الفحص وبناء التقرير» لإكمال بقية المؤشرات."
                    )
                else:
                    st.warning(
                        f"توقّف مؤقت أثناء فحص: {root['name']}. اضغطي «تشغيل / إكمال الفحص وبناء التقرير» لإكمال الباقي."
                    )
                partial_stop = True
                break

            stage_res = compute_stage(root, scanned["folders"], scanned["files"])
            save_stage_cache(root["key"], stage_res)
            stages_map[root["key"]] = stage_res

            if step_mode.startswith("فحص مرحلة واحدة"):
                st.success(f"تم إكمال وحفظ المرحلة: {root['name']}. اضغطي الزر مرة أخرى لفحص المرحلة التالية.")
                partial_stop = True
                break

        prog.progress(1.0)
        status_box.empty()
        if not partial_stop:
            st.success("اكتمل فحص المراحل السبع وتحديث النتائج.")

if refresh_clicked:
    stages_map = load_cached_stages()

ordered_stages = [stages_map[r["key"]] for r in CFG["ROOTS"] if r["key"] in stages_map]

# بناء عرض شامل يشمل المراحل المكتملة + المراحل قيد الفحص الجزئي
display_stages = []
for r in CFG["ROOTS"]:
    if r["key"] in stages_map:
        display_stages.append(stages_map[r["key"]])
    else:
        p_scan = load_partial_scan(r["key"])
        if p_scan:
            st_temp = compute_stage(r, p_scan["folders"], p_scan["files"])
            st_temp["is_partial"] = True
            display_stages.append(st_temp)

if display_stages:
    all_rows = [r for s in display_stages for r in s["rows"]]
    tot_ind = len(all_rows)
    tot_ready = sum(1 for r in all_rows if r["judg"] == "جاهز للزيارة")
    tot_ready_pct = (tot_ready * 100.0 / tot_ind) if tot_ind else 0.0
    st.markdown(
        f'<div class="note"><b>نسبة الجاهزية الإجمالية (للمفحوص حتى الآن):</b> '
        f'<span style="font-size:18px;font-weight:700;color:#0E3B28;">{tot_ready_pct:.1f}%</span> '
        f"({tot_ready} من {tot_ind} مؤشراً · {len(ordered_stages)} مراحل مكتملة من {len(CFG['ROOTS'])})</div>",
        unsafe_allow_html=True,
    )

cols = st.columns(4)
for idx, root in enumerate(CFG["ROOTS"]):
    with cols[idx % 4]:
        p_scan = load_partial_scan(root["key"])
        if root["key"] not in stages_map and not p_scan:
            st.markdown(f"**{root['name']}**")
            st.caption("لم يُفحص بعد")
        elif root["key"] not in stages_map and p_scan:
            temp_s = compute_stage(root, p_scan["folders"], p_scan["files"])
            m = with_ready_(temp_s["summary"])
            done_inds = sum(1 for r in temp_s["rows"] if r["total"] > 0)
            st.markdown(f"**{m['name']}** ⏳ *(قيد الاستكمال)*")
            st.metric("نسبة الإنجاز المؤقتة", f"{m['pct']:.1f}%", f"مؤشرات مفحوصة: {done_inds}/{m['indicators']}")
            st.caption(f"محفوظ حتى: {p_scan.get('updated_at', '—')} · ملفات {m['files']}")
        else:
            m = with_ready_(stages_map[root["key"]]["summary"])
            st.markdown(f"**{m['name']}** ✅")
            st.metric("نسبة الإنجاز", f"{m['pct']:.1f}%", f"الجاهزية {m['readyPct']:.1f}%")
            st.caption(
                f"{m['indicators']} مؤشراً · جاهز {m['ready']} · فجوات {m['gap']} · تحتاج أداة {m['needtool']}\n"
                f"ملفات {m['files']} (OCR: {m.get('ocrScanned', 0)}) · خارج المؤشرات {m['orphan']}"
            )

if len(ordered_stages) == len(CFG["ROOTS"]):
    st.divider()
    st.subheader("تصدير التقرير النهائي")
    stamp = datetime.now(ZoneInfo("Asia/Riyadh")).strftime("%Y-%m-%d_%H-%M")
    d1, d2 = st.columns(2)
    with d1:
        pdf_bytes = build_pdf_bytes(ordered_stages)
        st.download_button(
            "تحميل التقرير PDF",
            data=pdf_bytes,
            file_name=f"لجنة_التقويم_الخارجي_الافتراضية_{stamp}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with d2:
        xlsx_bytes = build_excel_bytes(ordered_stages)
        st.download_button(
            "تحميل جدول التفاصيل (Excel)",
            data=xlsx_bytes,
            file_name=f"تفاصيل_المؤشرات_{stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

if display_stages:
    st.divider()
    st.subheader("تفاصيل المؤشرات حسب المرحلة (تشمل المحفوظ جزئياً)")
    selected_name = st.selectbox("اختر المرحلة لعرض المؤشرات", [s["summary"]["name"] for s in display_stages])
    current_stage = next(s for s in display_stages if s["summary"]["name"] == selected_name)

    f1, f2, f3 = st.columns(3)
    with f1:
        dom_filter = st.selectbox("المجال", ["الكل"] + [f"{k} · {v}" for k, v in DOMAINS.items()])
    with f2:
        judg_filter = st.selectbox(
            "الحكم",
            ["الكل", "جاهز للزيارة", "فجوة تستدعي التحسين", "يحتاج أداة قياس", "لا تتوفر أدلة كافية"],
        )
    with f3:
        q_filter = st.text_input("بحث بالرمز أو اسم المؤشر")

    filtered = []
    for r in current_stage["rows"]:
        if dom_filter != "الكل" and not dom_filter.startswith(r["dom"] + " "):
            continue
        if judg_filter != "الكل" and r["judg"] != judg_filter:
            continue
        if q_filter.strip() and (q_filter.strip() not in r["code"] and q_filter.strip() not in r["title"]):
            continue
        filtered.append({
            "المجال": f"{r['dom']} · {DOMAINS.get(r['dom'], '')}",
            "الرمز": r["code"],
            "المؤشر": r["title"],
            "ملفات": f"{r['total']} / {r['uniq']}",
            "الإنجاز %": round(r["pct"], 1),
            "الحكم": r["judg"],
            "الاقتراحات": " • ".join(r["suggestions"]) if r["suggestions"] else "—",
        })

    st.dataframe(pd.DataFrame(filtered), use_container_width=True, hide_index=True)

st.markdown(
    '<div class="foot">جميع الحقوق محفوظة ©️ منصات سهما التعليمية • نظام جودة الأثر والتضمين</div>',
    unsafe_allow_html=True,
)
