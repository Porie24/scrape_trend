# Portable SA Pipeline

ส่วนนี้แปลงคลังข้อมูลรายเดือนใน `data/series/` เป็นชุดวิเคราะห์ที่ Agent เครื่องอื่นสร้างซ้ำและตรวจสอบได้ โดยไม่แก้ `data/`, `data.js` หรือเส้นทางเก็บข้อมูลดิบ

## ติดตั้งบน macOS/Linux

X-13 ต้อง compile เองครั้งเดียวก่อนใช้งาน (ไม่มี auto-installer) — ดูคำสั่งเต็มที่ README.md หัวข้อ "แพลตฟอร์มและ X-13"

## คำสั่ง

```bash
# สร้างผลวิเคราะห์ใหม่
.venv/bin/python -m analysis.build --allow-unverified-x13

# สร้างใน staging แล้วเทียบผลแบบ byte-for-byte
.venv/bin/python -m analysis.build --check --allow-unverified-x13

# ตรวจ schema, hashes, source digest, raw→pre-SA recomputation และ coverage โดยไม่เรียก X-13
.venv/bin/python -m analysis.build --audit
```

binary ที่ compile เองบน Mac ไม่ผ่าน hash check ที่ pin ไว้กับ build Windows จึงต้องใส่ `--allow-unverified-x13` เสมอ (ไม่ใช้กับ `--audit` เพราะไม่เรียก X-13) ระบุ path เองได้ด้วย `--x13-path <path>` ถ้าไม่ได้อยู่ที่ `.tools/x13/1.1-b62/x13as` หรือ PATH

## Contract การคำนวณ

- อ่าน case จาก `keywords.csv` โดยตรง — จำนวน T1/T2 เปลี่ยนได้เรื่อย ๆ ตามที่ทีมเพิ่ม/คัดกรองคำใหม่ (ดู `keywords.csv` เอง ไม่ pin จำนวนไว้ที่นี่)
- `TH` ใช้ช่วง `2011-01` เป็นต้นไป
- `REG_ISAN20` ใช้ข้อมูลจริงของ 20 จังหวัดภาคอีสาน (`TH-30` ถึง `TH-49`) ตั้งแต่ `2014-01` เป็นต้นไป ห้ามเติมศูนย์ปลอมให้ปี 2011–2013
- **รองรับ partial coverage โดยตั้งใจ**: แต่ละ case ใช้เฉพาะจังหวัดที่มีไฟล์ raw จริงในสโคปนั้น จังหวัดที่ยังไม่ได้เก็บจะถูกข้ามไปเฉย ๆ ไม่ fail ทั้ง build และไม่เติมค่าใด ๆ แทน — `Geo_Support_N`/`Geo_Support_Total` ใน `quality_flags.csv` รายงานตามจริงเทียบกับสโคปเต็ม (20 จังหวัด) เสมอ ไม่ใช่เทียบกับที่เก็บมาแล้วเท่านั้น ถ้า case ไหนยังไม่มีจังหวัดใดเก็บเลยในสโคปนั้น จะได้แถวเดียวสถานะ `NO_SIGNAL` (ไม่ใช่หายไปจากไฟล์) เพื่อให้ทุก case×scope มีแถวครบเสมอ
- T1 ภาค: rebase max100 แยกรายจังหวัดที่มีข้อมูล (A) → เฉลี่ยข้ามจังหวัดที่มีข้อมูล → rebase ภาค (C)
- T2 ภาค: rebase ราย member×จังหวัด (A) → เฉลี่ย members ในจังหวัด → rebase family×จังหวัด (B) → เฉลี่ยข้ามจังหวัดที่มีข้อมูล → rebase ภาค (C)
- ระดับประเทศใช้ลำดับเดียวกันกับ geography เดียว; T2 ยังทำ member rebase และ family rebase
- X-13 ใช้ additive mode, `log=False`, `outlier=False`; ค่า 0 เปลี่ยนเป็น `0.001` เฉพาะสำเนาที่ส่งเข้า X-13
- ใช้ robust STL เฉพาะ timeout หรือ model error ที่ X-13 บันทึกเป็น `ERROR:` ต่อ series และบันทึก `STL_FALLBACK` พร้อมเหตุผล; process crash, output หายโดยไม่มี explicit error หรือไม่พบ binary ต้อง fail build
- หลัง SA: floor ค่าติดลบเป็น 0 → rebase max100 → centered MA3 (`window=3`, `min_periods=1`)
- series ดิบที่เป็นศูนย์ล้วนต้องคงเป็นศูนย์และติดสถานะ `NO_SIGNAL`; ห้ามทำ epsilon ก่อน rebase เพราะจะกลายเป็นค่าคงที่ 100
- เดือนที่ขาดหายในไฟล์ raw ที่มีอยู่จริงต้อง fail เสมอ (ไม่ใช่ "จังหวัดยังไม่เก็บ" แต่คือ "เก็บมาแล้วแต่ไม่สมบูรณ์") — pipeline ไม่เดา ไม่ pad เดือน และไม่เฉลี่ยเฉพาะบางเดือนของ series เดียวกัน
- คำนวณ full precision และปัดเป็น 10 ตำแหน่งเฉพาะตอนเขียน CSV

## ผลลัพธ์

ไฟล์ canonical อยู่ใน `derived/sa_pipeline_v3/`:

| ไฟล์ | เนื้อหา |
|---|---|
| `series.csv` | long-format monthly series: input rebased, SA, floor0, post-SA rebase และ centered MA3; ใช้เป็น Tableau data source ได้ตรง |
| `method_log.csv` | วิธีที่ใช้จริง, fallback reason, signal/support และ post-SA status ต่อ case×scope |
| `rebase_audit.csv` | ค่า pre-max และจำนวน contributor ในขั้น A/B/C/D |
| `x13_diagnostics.csv` | M1–M11, Q และ seasonality tests ที่อ่านได้จาก X-13 output |
| `quality_flags.csv` | สถานะ execution/diagnostic/quality, geographic support, FULL/PARTIAL coverage และ flag ว่าค่า centered-MA3 เดือนปลายยัง provisional ต่อ case×scope |
| `manifest.json` | method contract, windows, package/X-13 versions, source digest, row counts และ hashes |

`quality_flags.csv` เป็น sidecar เท่านั้น ไม่เปลี่ยน schema หรือค่าตัวเลขใน `series.csv` โดย `Quality_Status=PASS` ใช้เฉพาะ X-13 ที่ diagnostics เป็น `ACCEPTED`; conditional/rejected และ STL fallback เป็น `REVIEW` (ดูวิธีรันจริงจาก `Execution_Status`) ส่วน `Coverage_Status=PARTIAL` หมายถึงมีสัญญาณจาก geography ไม่ครบ scope (ทั้งเพราะยังไม่ได้เก็บ และเพราะเก็บแล้วแต่ไม่มีสัญญาณ สองเหตุผลนี้แยกไม่ได้จากตัวเลขนี้อย่างเดียว ต้องดู `data/catalog.json`/`rebase_audit.csv` ประกอบ) ค่า `MA3_Endpoint_Provisional=TRUE` ระบุว่า centered MA3 เดือนสุดท้ายใช้ข้อมูลเพียงสองเดือนและอาจเปลี่ยนเมื่อเดือนถัดไปเข้ามา

`REG_ISAN20` ในชุดนี้ไม่ใช่ `ISAN` ของ dashboard: dashboard เดิมเป็น raw keyword-level composite และมี client-side rebase/trailing MA3 จึงยังไม่ควรนำ analytical series ชุดนี้ไปเสียบตรง ๆ เพราะจะเกิดการแปลงซ้ำ

## หลังอัปเดตข้อมูลดิบ

เมื่อ ingest/audit/build ของ raw ผ่านแล้ว ให้รัน analytical build เป็นขั้นแยก จากนั้นรัน `--check` และ `--audit` ก่อน stage `derived/sa_pipeline_v3/` การแยกขั้นนี้รักษา raw collector ให้ใช้ Python มาตรฐานได้ และทำให้ความล้มเหลวของ X-13 ไม่กระทบคลังดิบ
