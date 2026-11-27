import csv
import io
import os
import re
import tempfile
import time

from docx import Document
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from openpyxl import load_workbook
from PIL import Image, ImageOps
import pypdfium2 as pdfium
import pytesseract

IMAGE_MIMES = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp", "image/tiff",
}


def build_drive_service(service_account_info):
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_children(service, parent_id):
    out = []
    page_token = None
    query = f"'{parent_id}' in parents and trashed = false"
    while True:
        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id,name,mimeType,size,parents,owners(emailAddress),createdTime,webViewLink)",
                pageSize=1000,
                pageToken=page_token,
            )
            .execute()
        )
        out.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return out


def download_file_bytes(service, file_id, mime_type):
    if mime_type == "application/vnd.google-apps.document":
        req = service.files().export_media(fileId=file_id, mimeType="text/plain")
    elif mime_type == "application/vnd.google-apps.spreadsheet":
        req = service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    elif mime_type == "application/vnd.google-apps.presentation":
        req = service.files().export_media(fileId=file_id, mimeType="text/plain")
    elif mime_type.startswith("application/vnd.google-apps."):
        return b"", "unsupported"
    else:
        req = service.files().get_media(fileId=file_id)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue(), "ok"


def clean_ocr_text(raw_text):
    txt = re.sub(r"[^\w\u0600-\u06FF\s.,%:/\-|()]", " ", str(raw_text or ""))
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    return txt.strip()


def ocr_image_bytes(data_bytes, tmp_dir):
    img_path = os.path.join(tmp_dir, "ocr_tmp.png")
    with Image.open(io.BytesIO(data_bytes)) as im:
        im = ImageOps.exif_transpose(im).convert("L")
        im = ImageOps.autocontrast(im)
        w, h = im.size
        if max(w, h) < 1400:
            im = im.resize((w * 2, h * 2))
        im.save(img_path)
    try:
        txt = pytesseract.image_to_string(Image.open(img_path), lang="ara+eng", config="--psm 6")
    except Exception:
        txt = pytesseract.image_to_string(Image.open(img_path))
    cleaned = clean_ocr_text(txt)
    if len(re.findall(r"[\w\u0600-\u06FF]", cleaned)) < 4:
        return "", "weak_ocr"
    return cleaned, "ocr"


def extract_pdf_text_and_ocr(data_bytes, tmp_dir, max_pages=15):
    pdf = pdfium.PdfDocument(data_bytes)
    texts = []
    used_ocr = False
    had_weak_ocr = False
    page_count = min(len(pdf), max_pages)
    for idx in range(page_count):
        page = pdf[idx]
        textpage = page.get_textpage()
        page_txt = (textpage.get_text_range() or "").strip()
        if len(re.findall(r"[\w\u0600-\u06FF]", page_txt)) >= 10:
            texts.append(page_txt)
        else:
            pil_im = page.render(scale=200 / 72).to_pil()
            buf = io.BytesIO()
            pil_im.save(buf, format="PNG")
            ocr_txt, ocr_status = ocr_image_bytes(buf.getvalue(), tmp_dir)
            if ocr_txt:
                texts.append(ocr_txt)
                used_ocr = True
            elif ocr_status == "weak_ocr":
                had_weak_ocr = True

    joined = "\n".join(texts).strip()
    if joined:
        return joined, ("ocr" if used_ocr else "text")
    return "", ("weak_ocr" if had_weak_ocr else "no_text")


def extract_docx_text(data_bytes):
    doc = Document(io.BytesIO(data_bytes))
    parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    for tbl in doc.tables:
        for row in tbl.rows:
            row_vals = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if row_vals:
                parts.append(" | ".join(row_vals))
    return "\n".join(parts).strip()


def extract_xlsx_text(data_bytes):
    wb = load_workbook(io.BytesIO(data_bytes), data_only=True)
    parts = []
    for sheet_name in wb.sheetnames[:10]:
        ws = wb[sheet_name]
        for row in ws.iter_rows(max_row=200, max_col=25, values_only=True):
            vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
            if vals:
                parts.append(" | ".join(vals))
    return "\n".join(parts).strip()


def extract_content(file_meta, service, tmp_dir):
    name = (file_meta.get("title") or "").lower()
    mime = (file_meta.get("mimeType") or "").lower()
    size_val = int(file_meta.get("fileSize") or 0)
    if size_val > 25 * 1024 * 1024:
        return "", "skipped_large", "skipped_large"

    try:
        data, status = download_file_bytes(service, file_meta["id"], mime)
        if status != "ok" or not data:
            return "", "metadata_only", status
    except Exception:
        return "", "metadata_only", "download_error"

    try:
        if mime in IMAGE_MIMES or any(name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")):
            txt, ocr_st = ocr_image_bytes(data, tmp_dir)
            return txt[:6000], ("ocr" if txt else "metadata_only"), ocr_st

        if mime == "application/pdf" or name.endswith(".pdf"):
            txt, src = extract_pdf_text_and_ocr(data, tmp_dir)
            return txt[:8000], (src if txt else "metadata_only"), ("ok" if txt else src)

        if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or name.endswith(".docx"):
            txt = extract_docx_text(data)
            return txt[:8000], ("text" if txt else "metadata_only"), ("ok" if txt else "no_text")

        if (
            mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            or mime == "application/vnd.google-apps.spreadsheet"
            or name.endswith(".xlsx")
        ):
            txt = extract_xlsx_text(data)
            return txt[:8000], ("text" if txt else "metadata_only"), ("ok" if txt else "no_text")

        if mime == "text/csv" or name.endswith(".csv"):
            decoded = data.decode("utf-8", errors="ignore")
            rows = list(csv.reader(io.StringIO(decoded)))[:200]
            txt = "\n".join(" | ".join(c.strip() for c in r if c.strip()) for r in rows if any(c.strip() for c in r))
            return txt[:8000], ("text" if txt else "metadata_only"), ("ok" if txt else "no_text")

        if mime.startswith("text/") or mime.startswith("application/vnd.google-apps.") or name.endswith((".txt", ".md")):
            txt = data.decode("utf-8", errors="ignore").strip()
            return txt[:8000], ("text" if txt else "metadata_only"), ("ok" if txt else "no_text")

    except Exception:
        return "", "metadata_only", "parse_error"

    return "", "metadata_only", "metadata_only"


def scan_root(
    service,
    root,
    budget_seconds=90,
    inspect_contents=True,
    resume_state=None,
    on_checkpoint=None,
):
    start = time.monotonic()

    # استرجاع شجرة المجلدات والملفات المحفوظة مسبقاً إن وُجدت لتفادي إعادة حصر Drive
    if resume_state and resume_state.get("folders") and resume_state.get("files"):
        folders_list = resume_state["folders"]
        raw_files = resume_state["files"]
        scanned_ids = set(resume_state.get("scanned_ids") or [])
    else:
        folders = {
            root["id"]: {"id": root["id"], "title": root["name"], "parentId": None, "viewUrl": ""}
        }
        raw_files = []
        queue = [root["id"]]

        while queue:
            if time.monotonic() - start > budget_seconds:
                return None
            pid = queue.pop(0)
            for c in list_children(service, pid):
                parent = (c.get("parents") or [pid])[0]
                if c.get("mimeType") == "application/vnd.google-apps.folder":
                    folders[c["id"]] = {
                        "id": c["id"],
                        "title": c.get("name", ""),
                        "parentId": parent,
                        "viewUrl": c.get("webViewLink", ""),
                    }
                    queue.append(c["id"])
                else:
                    owners = c.get("owners") or []
                    raw_files.append({
                        "id": c["id"],
                        "title": c.get("name", ""),
                        "mimeType": c.get("mimeType", ""),
                        "fileSize": str(c.get("size", "0")),
                        "parentId": parent,
                        "owner": owners[0].get("emailAddress", "") if owners else "",
                        "createdTime": c.get("createdTime", ""),
                        "viewUrl": c.get("webViewLink", ""),
                        "extractedText": "",
                        "contentSource": "pending",
                        "readStatus": "pending",
                    })

        folders_list = list(folders.values())
        scanned_ids = set()
        # حفظ الحصر الأولي لشجرة المجلدات والملفات فوراً
        if on_checkpoint:
            on_checkpoint(folders_list, raw_files, scanned_ids)

    if not inspect_contents:
        for f in raw_files:
            if f["id"] not in scanned_ids:
                f["extractedText"] = ""
                f["contentSource"] = "metadata_only"
                f["readStatus"] = "metadata_only"
                scanned_ids.add(f["id"])
        return {
            "partial": False,
            "folders": folders_list,
            "files": raw_files,
            "scanned_ids": list(scanned_ids),
        }

    # تجميع الملفات حسب مجلد المؤشر (parentId) لإنهاء كل مؤشر وحفظه كاملاً قبل الانتقال للتالي
    files_by_indicator_folder = {}
    for f in raw_files:
        files_by_indicator_folder.setdefault(f["parentId"], []).append(f)

    tmp_dir = tempfile.mkdtemp(prefix="sahma_ocr_")
    processed_since_save = 0

    for folder_id, folder_files in files_by_indicator_folder.items():
        # تخطّي مجلد المؤشر بالكامل إذا كانت جميع ملفاته مفحوصة مسبقاً
        if all(f["id"] in scanned_ids for f in folder_files):
            continue

        for f in folder_files:
            if f["id"] in scanned_ids:
                continue

            if time.monotonic() - start > budget_seconds:
                if on_checkpoint:
                    on_checkpoint(folders_list, raw_files, scanned_ids)
                return {
                    "partial": True,
                    "folders": folders_list,
                    "files": raw_files,
                    "scanned_ids": list(scanned_ids),
                }

            txt, src, read_st = extract_content(f, service, tmp_dir)
            f["extractedText"] = txt
            f["contentSource"] = src
            f["readStatus"] = read_st
            scanned_ids.add(f["id"])
            processed_since_save += 1

            # حفظ دوري كل 3 ملفات لحماية المؤشرات المزدحمة بالصور (OCR)
            if on_checkpoint and processed_since_save >= 3:
                on_checkpoint(folders_list, raw_files, scanned_ids)
                processed_since_save = 0

        # حفظ فوري عند اكتمال جميع ملفات مجلد المؤشر
        if on_checkpoint and processed_since_save > 0:
            on_checkpoint(folders_list, raw_files, scanned_ids)
            processed_since_save = 0

    return {
        "partial": False,
        "folders": folders_list,
        "files": raw_files,
        "scanned_ids": list(scanned_ids),
    }
