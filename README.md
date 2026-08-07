# Isan Household Financial Fragility Toolkit

เครื่องมือเก็บ/อัพเดทข้อมูล Google Trends พร้อมหน้าแสดงผล สำหรับชุดคำค้นความเปราะบางด้านการเงินครัวเรือนภาคอีสาน
(engineering ต่อยอดจาก [google-trends-toolkit](https://github.com/reload0981-ops/google-trends-toolkit) ของทีมเดิม ซึ่งใช้ติดตาม Isan Labor Search-Intent — โครงสร้างระบบเดียวกัน เปลี่ยนหัวข้อและชุดคำค้น)

ระบบ production มีเส้นทางเดียว:

`Google Trends → Chrome extension → incoming/ → Python ingest/audit → data/ → GitHub Pages`

- **ตัวเก็บข้อมูลจริง** คือ Chrome extension ใน `extension/` ซึ่งรันบน Chrome profile ที่ลงชื่อเข้าใช้ Google แล้ว
- **Python** สร้างคิว ตรวจ CSV เข้าคลัง และตรวจ release gate; ไม่ได้เป็นตัวโหลดชุดใหญ่ในเส้นทาง production
- **GitHub** คือคลังถาวรของโค้ดและข้อมูล ไม่ใช่ตัวเก็บจาก Google Trends
- `incoming/`, `extension/data/jobs*.json` และ `.browser-runner/` เป็นสถานะชั่วคราวเฉพาะเครื่อง ไม่ขึ้น Git
- **หน้าแสดงผล** คือ `index.html` และข้อมูลที่สร้างอัตโนมัติใน `data.js`

ด้านบนของหน้าเว็บมี **Data health strip** บอกเดือนข้อมูลล่าสุด ความครอบคลุม จำนวนซีรีส์ในแต่ละ signal tier และวันที่เก็บข้อมูล พร้อมคำเตือนรายเส้นเมื่อสัญญาณบางหรืออีสานคอมโพสิตมีจังหวัดสนับสนุนไม่ครบ 5 จังหวัด คำเตือนนี้บอกคุณภาพการสังเกต ไม่ได้แปลว่า "ครัวเรือนไม่มีความเปราะบางทางการเงิน"

> **แพลตฟอร์ม**: repo นี้รันบน **macOS/Linux** (ต่างจากต้นฉบับที่พึ่ง Windows PowerShell) `scripts/toolkit.sh` และ `scripts/bootstrap-mac.sh` เป็น bash port ของ `toolkit.ps1`/`bootstrap-windows.ps1` เดิม ดู "แพลตฟอร์มและ X-13" ด้านล่างก่อนรัน `setup`

## เปิดหน้าแสดงผล

- ในเครื่อง: เปิดไฟล์ `index.html` ด้วย browser ได้เลย (ข้อมูลฝังใน `data.js` ไม่ต้องรัน server)
- ผ่านเว็บ: ยังไม่ได้ deploy — หลัง push ขึ้น GitHub และตั้ง Pages source เป็น GitHub Actions แล้ว จะเพิ่มลิงก์ตรงนี้

## แพลตฟอร์มและ X-13

- `scripts/toolkit.sh setup` เรียก `scripts/bootstrap-mac.sh` ซึ่งสร้าง `.venv`, ติดตั้ง `requirements-analysis.txt`, ตรวจ Python/Git/Chrome/GitHub CLI เหมือน `bootstrap-windows.ps1` เดิม
- **X-13ARIMA-SEATS ไม่มี auto-installer สำหรับ macOS**: ต้นฉบับดาวน์โหลด `x13as.exe` จาก U.S. Census Bureau โดยตรง (มีแค่ build Windows อย่างเป็นทางการ) บน Mac ต้อง **compile จาก Fortran source เอง** ครั้งเดียวก่อนใช้ `analysis.build` — วิธีนี้ทดสอบแล้วว่าใช้ได้จริง (X-13 1.1 Build 62, รันผ่าน `seasonally_adjust()` จริงสำเร็จ):

  ```bash
  brew install gcc                         # มี gfortran ติดมาด้วย
  curl -sO https://www2.census.gov/software/x-13arima-seats/x13as/unix-linux/program-archives/x13as_asciisrc-v1-1-b62.tar.gz
  mkdir x13src && tar xzf x13as_asciisrc-v1-1-b62.tar.gz -C x13src
  cd x13src/x13as_asciisrc-v1-1-b62
  # gfortran ของ Homebrew ใหม่กว่าที่ source นี้เขียนไว้รองรับ ต้องผ่อนกฎ + เลิก static link (ไม่มีบน macOS)
  sed -i '' 's/^FFLAGS    = -O2/FFLAGS    = -O2 -std=legacy -fallow-argument-mismatch -w/' makefile.gf
  sed -i '' 's/\$(LINKER) -static -o \$@/$(LINKER) -o $@/' makefile.gf
  PATH="/opt/homebrew/opt/gcc/bin:$PATH" make -f makefile.gf
  mkdir -p <repo>/.tools/x13/1.1-b62
  cp x13as_ascii <repo>/.tools/x13/1.1-b62/x13as
  chmod +x <repo>/.tools/x13/1.1-b62/x13as
  ```

  **อย่าใช้ R package `x13binary` (CRAN)** — ดูเหมือนจะสะดวกกว่าเพราะมี binary macOS แถมมาให้เลย แต่มันคือ build รุ่น `x13ashtml` (สำหรับ R package `seasonal` ที่ parse HTML) ซึ่งเขียนผลเป็น `.html` เท่านั้น ไม่สร้าง `.d11`/`.out` ที่ `analysis/x13.py` ต้องอ่าน — ทดสอบแล้วว่าใช้ไม่ได้กับ pipeline นี้ (ได้ error `missing .d11, .out` เสมอ)

  binary ที่ compile เองไม่ผ่าน hash check ที่ pin ไว้กับ build Windows ใน `analysis/x13.py` (แต่ version ตรง 1.1 Build 62 พอดี) — ใช้ `--allow-unverified-x13` เสมอบน macOS; ใส่ path ให้ตรวจเจอได้ทาง `$X13PATH`, PATH ปกติ, `.tools/x13/1.1-b62/x13as`, หรือ `--x13-path`

## ย้ายไปเครื่องใหม่

1. Clone repo แล้วเปิด AI agent ที่ root ของ repo; `AGENTS.md` / `CLAUDE.md` จะชี้ให้ Agent อ่าน `SKILL.md`
2. ให้ Agent รัน `./scripts/toolkit.sh setup` คำสั่งเดียว เพื่อตรวจ Python 3.11–3.13, Git, Chrome, GitHub auth, เตรียม `.venv` และรัน audits/tests ครบ (ยกเว้น X-13 ที่ต้องติดตั้งเองครั้งแรกตามหัวข้อด้านบน)
3. ผู้ใช้ตั้ง Chrome ครั้งเดียว: Load unpacked จาก `extension/`, อนุญาต `trends.google.co.th`, ตั้ง Downloads ไป `incoming/` ของ clone ใหม่ และปิด **Ask where to save each file**
4. หลังจากนั้นบอก Agent เพียง "อัพเดทข้อมูลเดือนนี้" หรือ "เพิ่มคำว่า …" ได้เลย

ข้อมูลถาวรจะตามมาครบจาก GitHub แต่คิวที่กำลังรัน ไฟล์ใน `incoming/`, Chrome extension และ GitHub login ต้องตั้งใหม่ต่อเครื่อง

## Monthly update ทางการ

### Chrome extension + Python ingest

**เก็บชุดใหญ่: ใช้ Chrome extension ใน `extension/`** มันไล่โหลด CSV จากหน้า Google Trends ใน Chrome จริงตามคิวงาน พร้อมระบบ pause/retry/CAPTCHA และตั้งชื่อไฟล์ให้ ingest กินได้ทันที รันด้วย:

```bash
./scripts/toolkit.sh monthly-run
```

`monthly-run` สร้างคิวแล้วหยุดที่ Chrome checkpoint ให้ Import/Start/แก้ CAPTCHA เมื่อ Controller เหลือ 0 FAILED ให้กลับมา terminal พิมพ์ `FINISH`; wrapper จะ ingest และรันทุก release gate ต่อทันที ผลที่ Tableau อ่านได้อยู่ที่ `derived/sa_pipeline_v3/series.csv` คำสั่งนี้ไม่ stage/commit/push

ถ้าต้องแยกคนเก็บกับคนตรวจ ใช้ `monthly-prepare` และ `monthly-finish` แบบเดิมได้ จำกัดคิวโดยส่ง argument ของ `make_jobs.py` ต่อท้าย เช่น `./scripts/toolkit.sh monthly-run --ids FP001 --geo TH`

extension ใช้หน้า Explore รุ่นใหม่ที่ `trends.google.co.th/explore?date=all` ซึ่งส่งข้อมูลรายเดือน (`Time,<keyword>`) ใน Chrome ปกติของผู้ใช้ Controller import queue จากไฟล์ได้ จึงไม่ต้อง Reload extension ทุกครั้งที่สร้างคิวใหม่ Reconcile Downloads รับเฉพาะไฟล์จากรอบปัจจุบัน

ถ้าคู่คำค้น × พื้นที่ใดไม่มีข้อมูล Controller จะลองยืนยัน **no-data ติดต่อกันอย่างน้อย 2 ครั้ง** แล้วดาวน์โหลด `no_data_manifest__YYYY-MM-DD.json` เข้า `incoming/` อัตโนมัติ; `ingest.py` จะตรวจ manifest ก่อนบันทึกสถานะ โดยไม่ยอมเปลี่ยนคู่ที่มี CSV เดิมให้เป็น no-data

**เก็บมือไม่กี่ไฟล์:** โหลด CSV จากหน้าเว็บ Google Trends เอง (ช่วงเวลา = ยาวสุด 2004-01-01 ถึงปัจจุบัน ตามนโยบายข้อมูลหลัก) วางใน `incoming/` จากนั้น:

```bash
./scripts/toolkit.sh monthly-finish
```

ตัว ingest ใช้ Python standard library ส่วน analytical gates ใช้ `.venv` ที่ `setup` เตรียมไว้ มันรู้จักทั้งไฟล์ export ของหน้าเว็บ GT แบบ classic, ไฟล์หน้าใหม่ชื่อ `time_series_<GEO>_*.csv`, ไฟล์ที่ตั้งชื่อ `<ID>__<GEO>.csv`, `manual_<ID>.csv` และ no-data manifest ไฟล์ CSV ต้องเริ่ม `2004-01` (TH) หรือ `2014-01` (จังหวัด), ต่อเนื่องถึงเดือนสมบูรณ์ล่าสุด และมีค่า finite 0–100 จึงจะเขียนทับคลังได้ เดือนปัจจุบันที่หน้าใหม่ระบุว่าเป็น partial จะถูกตัดออก ไฟล์ที่ไม่ผ่านจะถูกย้ายไป `incoming/review/` พร้อมเหตุผล ไม่มีการเดา

`ingest.py --since` ถูกปิดใช้งานโดยตั้งใจ เพราะการตัดข้อมูลเก่าแล้วนำช่วงสั้นไปทับซีรีส์เดิมจะทำลาย canonical long-horizon archive ต้อง export ใหม่ทั้งช่วง `2004-01-01` ถึงวันนี้แล้ว ingest โดยไม่ใส่ `--since` เท่านั้น

### สร้างชุดวิเคราะห์ SA หลัง raw update

ขั้นนี้แยกจาก raw ingest ภายใน pipeline โดยตั้งใจ และไม่แก้ `data/` หรือ `data.js` แต่ `monthly-finish` จะเรียก build → byte-check → audit ให้ครบอัตโนมัติ เพื่อไม่ให้ raw กับ derived หลุดคนละ release (ต้องมี X-13 binary พร้อมใช้งานตามหัวข้อ "แพลตฟอร์มและ X-13" ก่อน)

ผลลัพธ์อยู่ใน `derived/sa_pipeline_v3/` สำหรับทุกคำ × `TH` และ `REG_ISAN5` พร้อม method log, rebase audit, X-13 diagnostics, quality sidecar และ manifest ที่ผูกกับ hash ของ raw source โดย `series.csv` เป็น long-format ที่ต่อ Tableau ได้ตรง ดูสัญญาวิธีคำนวณและกติกา fallback ฉบับเต็มที่ `analysis/README.md`

### ทาง diagnostic (ห้ามใช้กับ canonical data หรือ publish)

#### Python browser runner

`collector/browser_runner.py` เปิด persistent Playwright Chromium พร้อม extension ตัวเดิม ทำให้ AI คุม queue จาก terminal ได้โดยไม่ต้องพอร์ต retry/CAPTCHA/no-data logic ซ้ำ:

```
pip install -r requirements.txt
python -m playwright install chromium               # ครั้งแรกครั้งเดียว
python collector/make_jobs.py --all
python collector/browser_runner.py --plan --json
python collector/browser_runner.py --start
python collector/browser_runner.py --status --json   # เรียกจากอีก terminal ได้
python collector/browser_runner.py --resume
```

runner เก็บ browser profile/status และไฟล์ที่ตรวจแล้วไว้เฉพาะ `.browser-runner/` (gitignored) โดยไม่เขียน `incoming/`, หยุดรอคนเมื่อเจอ CAPTCHA และใช้ parser + canonical coverage guard ชุดเดียวกับ `ingest.py` ตรวจไฟล์ Playwright เก็บชื่อ download ภายในเป็น GUID จึงมี acknowledgment bridge ที่ extension ยอมรับเฉพาะ filename/job/time ที่ตรงกันและไฟล์ที่ผ่าน guard แล้วเท่านั้น ผลจาก runner เป็น diagnostic เท่านั้น: ห้ามนำเข้า canonical archive, stage หรือ publish

#### pytrends (diagnostic เท่านั้น)

ติดตั้งครั้งแรกใน working copy สำหรับทดลอง: `pip install -r requirements.txt` (Python 3.11–3.13)

```
python collector/collect.py --plan --all          # ดูก่อนว่าจะเก็บอะไรบ้าง ไม่ยิง API
python collector/collect.py --ids FP001,FU001     # ทดลองรายคำ (เกิด local changes)
python collector/collect.py --group FP,FU         # ทดลองรายกลุ่ม (prefix ของ ID)
python collector/collect.py --all                 # ทดลองทุกคำทุกพื้นที่ (เสี่ยงโดน rate limit)
```

โดน 429 จะรอแล้วลองใหม่เอง ถ้าโดนหนักจะหยุดทั้งรอบ รันคำสั่งเดิมซ้ำได้เลย ตัวที่สำเร็จแล้ววันนี้จะถูกข้าม อย่าลด `--sleep` ต่ำกว่า default

คำสั่งกลุ่มนี้อาจสร้าง local changes เพื่อใช้วินิจฉัย แต่ผลไม่ใช่ canonical data และห้าม ingest, stage หรือ publish การเพิ่ม/อัพเดทคำจริงต้องกลับไปสร้างคิว extension ด้วย `monthly-prepare`

`make_jobs.py` และ `collect.py` บังคับ canonical window เดียวกัน: `--start 2004-01-01`, `--end` ต้องเป็นวันที่วันนี้ และ `collect.py --sleep` ต้องไม่น้อยกว่า 15 วินาที ค่าอื่นจะถูกปฏิเสธก่อนเริ่มเก็บ เพื่อกันข้อมูลช่วงสั้นทับคลังหลัก

เส้นทาง production จะแปลงข้อมูลเป็นรายเดือน ตัดเดือนที่ยังไม่จบ และ **แทนที่ซีรีส์เดิมทั้งเส้น** (ค่า Google Trends เป็น index เทียบภายในช่วงที่ดึง การต่อท่อนคนละช่วงทำให้ scale เพี้ยน) แล้ว rebuild `data.js`

### ตรวจสุขภาพและเผยแพร่อย่างปลอดภัย

หลัง extension เก็บครบ ให้รันคำสั่งเดียว:

```bash
./scripts/toolkit.sh monthly-finish
```

wrapper จะรัน ingest dry-run → ingest จริง → raw structural/freshness audits → `data.js` check → analytical build/byte-check/audit → full tests → `git status` และหยุดทันทีเมื่อ native command ใดคืน exit code ผิดปกติ ระบุเดือน gate เองได้ด้วย `monthly-finish 2026-06` คำสั่งนี้ **ไม่ stage, commit, push หรือ deploy**

- `--strict` fail เมื่อไฟล์ที่มีอยู่มี schema/ลำดับเดือนไม่ถูกต้อง, catalog ไม่สอดคล้อง หรือหลักฐาน no-data ผิดรูป; คู่ที่ยัง missing จะแสดงใน coverage แยก
- `--require-latest` คือ complete-release gate: ทุกคู่คำ×พื้นที่ต้องเป็นซีรีส์ที่ถึงเดือนกำหนด หรือ confirmed no-data จาก canonical window หลังเดือนนั้น; missing, invalid, stale data และ stale no-data ทำให้ fail ระบุเดือนเองได้ เช่น `--require-latest 2026-06`
- `collector/audit.py --json` แสดงรายงาน machine-readable สำหรับตรวจต่อหรือเก็บหลักฐาน
- signal tier คำนวณจากช่วง **2014-01 ถึงเดือนล่าสุด** ของแต่ละซีรีส์ (จุดที่ข้อมูลระดับจังหวัดเริ่มใช้ได้ ทำให้ด่าน National และ Regional อ่านช่วงเดียวกัน): `VERY_GOOD` = ไม่มีเดือนศูนย์, `ACCEPTABLE` = เดือนศูนย์ไม่เกิน 25% ของช่วง, `WEAK` = เกินกว่านั้น ซีรีส์ศูนย์ตลอดถูกระบุแยกด้วย
- `collector/audit.py` เป็นตัวคำนวณ signal tier ส่วน `collector/check_keyword.py` เอาตัวเลขชุดเดียวกันมาตัดสินด่านคัดกรองคำ (อ่านอย่างเดียวทั้งคู่)

ถ้าทุก gate ผ่านและ `git status --short` มีเฉพาะ generated data ที่คาดไว้ ให้ stage แบบ allowlist แล้ว publish:

```
git add -- data/series data/catalog.json data.js derived/sa_pipeline_v3
git diff --cached --name-only
git commit -m "update data <รายละเอียดสั้น>"
git push
```

ถ้าเพิ่ม/แก้คำค้น ให้ตรวจและ stage `keywords.csv` แยกต่างหาก ห้ามใช้ `git add -A` ในรอบ publish ข้อมูล หน้าเว็บบน Pages จะอัพเดทในราว 1–2 นาที (หลังตั้ง Pages source เป็น GitHub Actions)

## สำหรับ AI agent

repo นี้มี `SKILL.md` เป็นคู่มือปฏิบัติงานสำหรับ AI: เปิด AI agent (Claude Code, Codex ฯลฯ) ในโฟลเดอร์นี้แล้วสั่งงานภาษาคน เช่น "อัพเดทข้อมูลเดือนนี้" หรือ "เพิ่มคำว่า X" ได้เลย agent จะทำตาม workflow และกติกาเหล็กในนั้น (`CLAUDE.md` และ `AGENTS.md` ชี้มาที่ `SKILL.md` ให้อัตโนมัติ)

Agent ต้องเสนอเฉพาะ `toolkit.sh setup` / `monthly-prepare` / `monthly-finish` ก่อนเสมอ และขอผู้ใช้เฉพาะสิ่งที่ automation ทำแทนไม่ได้: ตั้ง Chrome ครั้งแรก, กด Import/Start และแก้ CAPTCHA หากพบ, ติดตั้ง X-13 binary ครั้งแรก (ไม่มี auto-installer บน Mac) ไม่ควรโยนรายชื่อสคริปต์หรือทางทดลองทั้งหมดให้ผู้ใช้เลือก

## ข้อมูลในชุด

| ไฟล์ | คืออะไร |
|---|---|
| `keywords.csv` | คำค้นที่ใช้งานอยู่ (เริ่มต้น 47 คำ seed ครอบคลุม 6 กลุ่ม Segment×Factor — ดูหัวข้อ "Taxonomy คำค้น" — ยังไม่ผ่านด่านคัดกรองจริงจากข้อมูล เพราะยังไม่มีข้อมูลเก็บ) พร้อม Tier / Segment / Factor |
| `reference/keywords_tried.csv` | คำค้นที่เคยถูกคิด/ทดสอบทั้งหมด พร้อมคอลัมน์ `best_stage` บอกว่าแต่ละคำไปไกลสุดถึงขั้นไหน (เริ่มต้นว่างเปล่า จะสะสมขึ้นเมื่อทีมคัดกรองคำใหม่ผ่าน `collector/add_keyword.py`) |
| `data/series/<ID>__<GEO>.csv` | ข้อมูลรายเดือนต่อคำต่อพื้นที่ (`Month,Value`) — ว่างเปล่าจนกว่าจะเก็บรอบแรก |
| `data/catalog.json` | บันทึกเวลา/ช่วงเก็บและสถานะ `available` หรือ confirmed `no_data` ของแต่ละคู่ |
| `data.js` | ข้อมูลรวมสำหรับหน้าแสดงผล (สร้างอัตโนมัติ อย่าแก้มือ) |
| `collector/audit.py` | ตรวจ coverage, โครงสร้าง, signal quality และ freshness gate โดยไม่แก้ข้อมูล |

พื้นที่ที่รองรับ: `TH` ประเทศไทย, `TH-30` นครราชสีมา, `TH-31` บุรีรัมย์, `TH-34` อุบลราชธานี, `TH-40` ขอนแก่น, `TH-41` อุดรธานี
(เพิ่ม/ลดได้ที่ตัวแปร `GEOS` ใน `collector/collect.py` และ `collector/build_site_data.py`)

พื้นที่พิเศษ `ISAN` "อีสาน (คอมโพสิต)" เป็น**ซีรีส์คำนวณ** ไม่ได้เก็บจาก Google โดยตรง: rebase จังหวัดที่มีสัญญาณ (ค่าสูงสุดมากกว่า 0) ให้ max = 100 → เฉลี่ยด้วยน้ำหนักเท่ากัน → rebase ผลรวมให้ max = 100 (สูตรเดียวกับ REG_ISAN5 ของโปรเจกต์เดิม) คำนวณใหม่อัตโนมัติทุกครั้งที่ rebuild `data.js`

คอมโพสิตไม่ได้มีครบ 5 จังหวัดทุกคำเสมอไป แต่ละซีรีส์จึงแนบ `support_n`, `support_total=5` และ `support_geos` ใน `data.js`; หน้าเว็บจะแสดง `N/5` และเตือนเมื่อใช้เพียง 2–4 จังหวัด ห้ามตีความหรือเรียกเส้นดังกล่าวว่าเป็นผลรวมครบทั้ง 5 จังหวัด

### Taxonomy คำค้น

คงโครงสร้าง 2 มิติเดิมจากโปรเจกต์ต้นทาง (Segment × Factor, ID prefix 2 ตัวอักษร) แต่เปลี่ยนความหมายให้เข้ากับหนี้ครัวเรือนแทนตลาดแรงงาน:

| Prefix | Segment | ความหมาย | Factor |
|---|---|---|---|
| `FP` | Formal | สถาบันการเงินในระบบ | Pull — แสวงหาสินเชื่อ/ความช่วยเหลือ |
| `FU` | Formal | สถาบันการเงินในระบบ | Push — สัญญาณเปราะบาง (ค้างชำระ, ล้มละลาย) |
| `TP` | Informal-Traditional | นอกระบบดั้งเดิม (จำนำ/ขายฝาก) | Pull — แสวงหาสินเชื่อ |
| `TU` | Informal-Traditional | นอกระบบดั้งเดิม | Push — สัญญาณเปราะบาง |
| `NP` | Informal-New | ช่องทางดิจิทัลใหม่ (แอปกู้เงิน) | Pull — แสวงหาสินเชื่อ |
| `NU` | Informal-New | ช่องทางดิจิทัลใหม่ | Push — สัญญาณเปราะบาง |

**ที่มาของ seed**: `FP001`–`FU015` (30 คำ) แปลจาก **Table A.1 "Constructing Google Searches for Household Stress"** ใน [Bellrose, Norman & Royters (RBA Bulletin, Dec 2022) "New Measures of Financial Stress from Non-traditional Data"](https://www.rba.gov.au/publications/bulletin/2022/dec/new-measures-of-financial-stress-from-non-traditional-data.html) — งานต้นฉบับผูก query ด้วย boolean AND/OR/NOT (เช่น `mortgage-problems` = `(mortgage AND default) OR (mortgage AND behind) OR (mortgage AND defer) OR (mortgage AND stress)`); ที่นี่แปลแต่ละแถวเป็นวลีไทยที่ใกล้เคียงแล้วรวมเป็น query เดียวด้วย `+` (Google Trends OR syntax) เช่น `FU013 = ผ่อนบ้านไม่ไหว+สินเชื่อบ้านค้างชำระ+ขอเลื่อนผ่อนบ้าน` หมวด `assistance` ของ paper แปลงเป็น Factor=Pull และหมวด `problems` แปลงเป็น Factor=Push (เพิ่ม `FP015`/`FU015` สินเชื่อ/หนี้ ธ.ก.ส. เองเพราะ paper ไม่มีบริบทเกษตร)

`TP`/`TU`/`NP`/`NU` (17 คำ) เป็นช่องว่างที่ paper (บริบทออสเตรเลีย) ไม่ครอบคลุม — ร่างขึ้นเองจากความรู้พื้นที่จริงเรื่องหนี้นอกระบบและแอปเงินกู้ในไทย (จำนำทอง, ขายฝากที่ดิน, เงินกู้นอกระบบ, แอปเงินกู้เถื่อน ฯลฯ) ยังไม่ผ่านด่านคัดกรองเหมือนกันทั้งชุด

การเพิ่มคำใหม่: ให้ Agent เช็ค `reference/keywords_tried.csv`, เพิ่มแถวใน `keywords.csv` ด้วย ID ที่ไม่ซ้ำ (หรือใช้ `collector/add_keyword.py --interactive`) แล้วสร้าง/นำเข้าคิว extension เฉพาะ ID นั้น; ห้ามใช้ pytrends เป็น release path

## ข้อควรรู้เรื่องตัวเลข

- ค่าเป็น Google Trends index 0-100 เทียบภายในช่วงเวลาที่ดึงของแต่ละคำและพื้นที่ **ไม่ใช่จำนวนการค้นจริง** และห้ามเทียบขนาดข้ามคำตรงๆ
- **นโยบายการเก็บ: โหลดยาวสุดเสมอ (2004-01-01 ถึงปัจจุบัน)** ข้อมูลหลักของชุดนี้คือ long horizon
- **ระดับจังหวัดใช้ได้ตั้งแต่ 2014-01 เท่านั้น** Google ปรับระบบระบุตำแหน่งช่วง 2011-2013 ข้อมูลจังหวัดก่อนหน้านั้นเป็นรู/break เครื่องมือทุกตัวตัดทิ้งให้อัตโนมัติ ระดับประเทศไม่ตัด
- **ยังไม่มีข้อมูลเก็บ**: `keywords.csv` เป็นชุด seed เริ่มต้น 47 คำที่ร่างไว้ให้ครอบคลุมทั้ง 6 กลุ่ม Segment×Factor ยังไม่ผ่านด่านคัดกรองจริง (`collector/check_keyword.py`) เพราะต้องมีข้อมูลจริงก่อนถึงจะตัดสิน Tier ได้ รอบเก็บข้อมูลแรกควรใช้ `collector/add_keyword.py --finalize` หรือ audit ทวนทุกคำหลังเก็บเสร็จ แล้วตัดคำที่สัญญาณอ่อนออกตามผล ไม่ใช่คงไว้ตามที่ร่างไว้

## ที่มา

engineering (Chrome extension, ingest/audit pipeline, X-13 SA pipeline) พอร์ตมาจาก [google-trends-toolkit](https://github.com/reload0981-ops/google-trends-toolkit) ของทีม ซึ่งใช้ติดตาม Isan Labor Search-Intent — โครงสร้างเดียวกัน เปลี่ยนหัวข้อและชุดคำค้นสำหรับความเปราะบางด้านการเงินครัวเรือนภาคอีสาน
