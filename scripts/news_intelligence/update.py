#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ดึงพาดหัวข่าวใหม่จาก The Standard (tag: หนี้ครัวเรือน), รวมกับข้อมูลเดิม,
สกัดวลีที่เกี่ยวกับความเปราะบางการเงินครัวเรือน แล้ว render เป็น word cloud + จัดอันดับ

รันด้วยมือ: python3 scripts/news_intelligence/update.py
รันอัตโนมัติ: .github/workflows/monthly-news-intelligence.yml (รายเดือน)

ขอบเขต: ดึงเฉพาะหน้าแรกของ tag archive (พอสำหรับเช็คข่าวใหม่ตั้งแต่รันครั้งก่อน)
ไม่ใช่การไล่เก็บย้อนหลังทั้งหมด — ฐานข้อมูลย้อนหลังอยู่ใน base_corpus.json แล้ว
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "news_headlines"
BASE_PATH = DATA_DIR / "base_corpus.json"
INCREMENTAL_PATH = DATA_DIR / "incremental.json"
OUT_DIR = ROOT / "news-intelligence"

TAG_URL = "https://thestandard.co/tag/หนี้ครัวเรือน/"

THAI_MONTHS = {
    "มกราคม": "01", "กุมภาพันธ์": "02", "มีนาคม": "03", "เมษายน": "04",
    "พฤษภาคม": "05", "มิถุนายน": "06", "กรกฎาคม": "07", "สิงหาคม": "08",
    "กันยายน": "09", "ตุลาคม": "10", "พฤศจิกายน": "11", "ธันวาคม": "12",
}

ARTICLE_PATTERN = re.compile(
    r'<div class="date">\s*(?:<i[^>]*></i>)?\s*([^<]+?)\s*</div>.*?'
    r'<h3 class="news-title">\s*<a href="([^"]+)">\s*([^<]+?)\s*</a>',
    re.DOTALL,
)


def thai_date_to_iso(text):
    m = re.match(r"(\d{1,2})\s+(\S+)\s+(\d{4})", text.strip())
    if not m:
        return None
    day, month_th, year = m.groups()
    month = THAI_MONTHS.get(month_th)
    if not month:
        return None
    return f"{year}-{month}"


def fetch_page1():
    """Fetch The Standard tag page 1 via headless WebKit.
    Plain requests/urllib gets silently blocked (bot protection) — a real
    browser engine is required. See conversation history for the diagnosis.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_page()
        page.goto(TAG_URL, timeout=20000)
        page.wait_for_timeout(2000)
        content = page.content()
        browser.close()
    return content


def parse_articles(html):
    out = []
    for date_text, url, title in ARTICLE_PATTERN.findall(html):
        iso_month = thai_date_to_iso(date_text)
        out.append({"date": iso_month, "title": title.strip(), "url": url, "source": "The Standard"})
    return out


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def update_incremental():
    known_urls = set()
    known_titles = set()
    for row in load_json(BASE_PATH, []):
        known_titles.add(row["title"])
    incremental = load_json(INCREMENTAL_PATH, [])
    for row in incremental:
        if row.get("url"):
            known_urls.add(row["url"])
        known_titles.add(row["title"])

    try:
        html = fetch_page1()
    except Exception as e:
        print(f"WARNING: fetch failed ({e}) — proceeding with existing data only", file=sys.stderr)
        return incremental, 0

    fetched = parse_articles(html)
    new_rows = [
        r for r in fetched
        if r["url"] not in known_urls and r["title"] not in known_titles
    ]
    if new_rows:
        incremental = incremental + new_rows
        INCREMENTAL_PATH.write_text(
            json.dumps(incremental, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return incremental, len(new_rows)


# --- phrase extraction (same logic as the exploratory scratchpad version) ---

# Use pythainlp's own maintained stopword corpus (1,030 words) rather than a
# hand-typed list — a hand-typed list is exactly how "แม้" slipped through
# and produced nonsense phrase fragments (reported and fixed once already;
# switching to the standard corpus fixes the whole class of bug, not just
# the one word that happened to get noticed).
# Words the standard corpus treats as generic stopwords but that are load-
# bearing in this domain — e.g. "นอก" is a stopword in general Thai, but it's
# half of "นอกระบบ" (informal debt), one of the two keywords that survived
# out-of-sample testing earlier in this project. Filtering it out here would
# silently break "นอกระบบ"/"หนี้นอกระบบ" phrase reconstruction.
STOPWORD_EXCEPTIONS = {"นอก"}


def _load_stopwords():
    from pythainlp.corpus import thai_stopwords
    return set(thai_stopwords()) - STOPWORD_EXCEPTIONS

# Categories are anchored to two research sources already cited in this
# project (summary_memo.html section 1.1 + this conversation):
#   - Lusardi, Schneider & Tufano (2011): fragility = liquidity-buffer shortfall
#   - Levy Institute fragility index: debt-to-income, DSR, short-term-debt
#     proportion, liquid-assets-to-liabilities, net worth
#   - PIER Discussion Paper 012 "Gauging Households' Debt Tolerance: Evidence
#     from Thailand" (pier.or.th/files/dp/pier_dp_012.pdf) — Thai-specific:
#     debt tolerance's determinants are debt burden, financial cushion,
#     income security, financial history, and financial discipline.
#   - NPL/Stage2 (this project's real data) = proxy for "DSR-failure"
# This taxonomy makes that mapping explicit in the news-phrase categorization.
ANCHORS = set("""
หนี้ ครัวเรือน เปราะบาง วิกฤต เสี่ยง ห่วง จับตา ปัญหา ดอกเบี้ย สินเชื่อ
เครดิตบูโร ลูกหนี้ NPL SM ยึด ล้มละลาย ค้างชำระ ผ่อน ทวง กับดัก
ทรุด ท่วม บาน ตกชั้น ตกงาน ว่างงาน มหกรรม ไกล่เกลี่ย เจรจา พัก
ลด ปรับโครงสร้าง เยียวยา อุ้ม รัดเข็มขัด กู้ นอกระบบ ฉุกเฉิน
สภาพคล่อง เงินสำรอง เงินสด รายได้ ทรัพย์สิน ภาระ DSR ระยะสั้น
จ่ายไม่ไหว เงินไม่พอ ไม่มีเงิน GDP จีดีพี ต่อรายได้ สัดส่วนหนี้
แบล็คลิสต์ ประวัติ อาชีพ มั่นคง วินัย ออม เกษตรกร รับจ้าง
""".split())

CAT_KEYWORDS = [
    # realized distress — the project's own NPL/Stage2 data is exactly this ("DSR-failure")
    ("dsr_failure", ["หนี้เสีย", "NPL", "SM", "ยึดทรัพย์", "ยึดรถ", "ยึดบ้าน", "ล้มละลาย", "ค้างชำระ",
                      "ผ่อนไม่ไหว", "เอาไม่อยู่", "ทรุด", "ตกชั้น", "เข้าขั้น"]),
    # debt burden / Debt-Service Ratio — PIER's #1 determinant of debt tolerance
    ("debt_burden", ["จ่ายไม่ไหว", "เงินไม่พอ", "ขาดสภาพคล่อง", "ภาระหนี้", "ภาระผ่อน", "DSR",
                      "รายได้ไม่พอ"]),
    # financial cushion / liquidity buffer — Lusardi et al. (2011) + PIER's "financial cushion"
    ("financial_cushion", ["สภาพคล่อง", "เงินสำรอง", "เงินสด", "ไม่มีเงิน", "ทรัพย์สิน"]),
    # income security — PIER: farmers/general-workers/business-owners have lower debt tolerance
    ("income_security", ["ตกงาน", "ว่างงาน", "เกษตรกร", "รับจ้าง", "อาชีพอิสระ", "รายได้ไม่มั่นคง"]),
    # financial history — PIER: past delinquency lowers debt tolerance long-term
    ("financial_history", ["เครดิตบูโร", "แบล็คลิสต์", "ประวัติ"]),
    # debt structure/leverage — debt-to-income, short-term debt proportion (Levy Institute)
    ("debt_structure", ["ต่อรายได้", "ระยะสั้น", "สัดส่วนหนี้", "ต่อ GDP", "ต่อจีดีพี", "หนี้ต่อ"]),
    # general risk sentiment — not a specific framework component, but the dominant news register
    ("warning_general", ["ห่วง", "จับตา", "เสี่ยง", "เปราะบาง", "กังวล", "หวั่น", "วิกฤต", "ปัญหา",
                          "ฉุกเฉิน", "กับดัก", "ผันผวน"]),
    ("policy", ["แก้", "พักหนี้", "ลดหนี้", "ปรับโครงสร้าง", "เจรจา", "ไกล่เกลี่ย", "มหกรรม",
                "อุ้ม", "เยียวยา", "รัดเข็มขัด"]),
]


def classify(text):
    for cat, keywords in CAT_KEYWORDS:
        if any(kw in text for kw in keywords):
            return cat
    if text in ("หนี้", "ครัวเรือน"):
        return "core"
    return "other"


_STOPWORDS_CACHE = None


def is_content_token(t):
    global _STOPWORDS_CACHE
    if _STOPWORDS_CACHE is None:
        _STOPWORDS_CACHE = _load_stopwords()
    t = t.strip()
    if len(t) < 1 or t in _STOPWORDS_CACHE:
        return False
    if re.match(r"^[\d\.,%\-/]+$", t):
        return False
    # drop stray single Latin letters — leftover fragments from things like
    # "Q1/2026" where the tokenizer splits off "Q" and the digits get filtered
    if len(t) == 1 and re.match(r"^[A-Za-z]$", t):
        return False
    return bool(t.strip())


def extract_phrases(headlines):
    from pythainlp.tokenize import word_tokenize

    phrase_counter = Counter()
    for row in headlines:
        title = re.sub(r'["\'“”‘’]', "", row["title"])
        toks_raw = word_tokenize(title, engine="newmm")
        runs, current = [], []
        for t in toks_raw:
            if is_content_token(t):
                current.append(t.strip())
            else:
                if current:
                    runs.append(current)
                current = []
        if current:
            runs.append(current)

        for run in runs:
            n = len(run)
            for size in (3, 2, 1):
                for i in range(n - size + 1):
                    gram = "".join(run[i:i + size])
                    if len(gram) < 2:
                        continue
                    if not any(a in gram for a in ANCHORS):
                        continue
                    phrase_counter[gram] += 1

    kept, kept_texts = [], []
    for text, count in sorted(phrase_counter.items(), key=lambda kv: -kv[1]):
        if any(text in k and text != k for k in kept_texts):
            continue
        kept.append((text, count))
        kept_texts.append(text)
    kept.sort(key=lambda kv: -kv[1])
    return kept[:70]


def main():
    incremental, n_new = update_incremental()
    print(f"new headlines found this run: {n_new}")

    base = load_json(BASE_PATH, [])
    all_headlines = base + incremental
    print(f"total corpus: {len(all_headlines)} headlines")

    phrases = extract_phrases(all_headlines)
    phrase_data = {"words": [{"text": w, "count": c} for w, c in phrases]}

    manifest_out = DATA_DIR / "phrase_data.json"
    manifest_out.write_text(json.dumps(phrase_data, ensure_ascii=False, indent=1), encoding="utf-8")

    OUT_DIR.mkdir(exist_ok=True)
    render(phrase_data, len(all_headlines))
    print(f"rendered outputs to {OUT_DIR}")


def render(phrase_data, n_headlines):
    """Reuses the same generator logic as the exploratory scratchpad scripts
    (gen_wordcloud_news.py / gen_wordlist_news.py) — kept here inline so this
    script has no dependency on the scratchpad directory.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_pages import render_wordcloud, render_wordlist

    render_wordcloud(phrase_data, n_headlines, OUT_DIR / "wordcloud.html", classify)
    render_wordlist(phrase_data, n_headlines, OUT_DIR / "index.html", classify)


if __name__ == "__main__":
    main()
