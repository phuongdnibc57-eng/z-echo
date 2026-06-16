# Z-Echo — Voice-of-Customer Agent · Design Spec (V1 internal)

> **Status:** Draft for review · **Date:** 2026-06-16 · **Owner:** PO (Zalo)
> **Scope:** Claw-a-thon hackathon, V1 internal-employee only.
> **Reference:** kiến trúc chi tiết & sơ đồ ở [`docs/architecture.md`](../architecture.md).

---

## 1. Tổng quan

**Z-Echo** là một agent đóng gói thành **1 Claw skill** giúp đội sản phẩm Zalo biến luồng feedback nội bộ
lộn xộn thành backlog có thể hành động. Nhân viên dogfood Zalo report bug/feedback (kèm screenshot) trong
group nội bộ bằng cách tag bot. Agent **hiểu kiến thức sản phẩm Zalo** để: hỏi bổ sung đúng chỗ thiếu →
validate & **dedup** với pool đã có → **route** tới đúng squad → **pool** thành ticket → **close-loop** báo
ngược cho người report khi có kết quả → **digest** chủ động cho squad/PO → và **học từ verdict của PO** để
case sau tự xử lý.

Điểm khác biệt cốt lõi (moat): agent **ground vào sản phẩm thật** (Confluence KB + pool tích luỹ) và **tự
bồi knowledge** từ phán quyết của PO — không vector DB, không training, chỉ là file mà engine vốn đã đọc.

---

## 2. Goals / Non-goals

### Goals (V1)
- G1. Nhận feedback đa phương thức (text + **screenshot, vision là CORE**) qua Zalo group/DM bằng Claw bot.
- G2. Clarify thông minh theo information-gap: hỏi tối đa 2–3 câu, skip slot vision đã prefill, biết lúc dừng.
- G3. **Dedup** feedback vào pool (component-narrow → LLM đọc `short_desc` → fetch full xác nhận), +1 vào issue cũ thay vì tạo trùng.
- G4. Validate/deflect: đã-fix-ở-version, không-phải-bug (kb), spam; mọi deflect là **soft** có đường thoát.
- G5. Synthesize (cluster + priority minh bạch) → Route theo ownership map → Pool thành issue.
- G6. **Close-loop**: khi issue có kết quả/verdict → nhắn ngược reporter **theo channel gốc**.
- G7. **Daily digest**: per-squad (chỉ khi vượt ngưỡng) + PO rollup + realtime escalation cho Critical.
- G8. **Learning loop**: PO verdict (kèm lý do, version-scoped) ghi ngược pool → case sau tự soft-deflect.
- G9. **Jira-optional**: pool file-based là source of truth; Jira chỉ là adapter sync — tắt Jira core vẫn chạy.

### Non-goals (hoãn V2 / ngoài phạm vi)
- N1. Kênh end-user ngoài (Zalo OA webhook), tone end-user, **full multi-language + localize giao diện bot** (V1 chỉ EN/VI — xem D12).
- N2. Spam/abuse filter nặng (internal = noise thấp), segment/churn-risk scoring.
- N3. Vector DB / embeddings / fine-tuning bất kỳ.
- N4. Auto-fix bug, auto-QA reproduce (chỉ triage, không sửa).
- N5. Web dashboard riêng (digest đi qua Zalo group, không build UI tách).

---

## 3. Phạm vi V1 — 6 phase

V1 = **internal employee only**. Build theo 6 phase (chi tiết giờ-công ở architecture mục 8):

| Phase | Nội dung |
|---|---|
| 0 | Scaffold toolkit `zecho/` (pytest) + `data/` layout + ownership.md |
| 1 | Toolkit core (TDD): frontmatter, versions, priority, issues, ownership, threshold, render, claw, jira_adapter |
| 2 | **Dedup (short_desc 2 tầng)** ⭐ trong skill `zecho-triage` — phần rủi ro/giá trị cao nhất |
| 3 | Toolkit closeloop + digest (deterministic, test) + skill `zecho-triage` route/pool |
| 4 | Skills proactive: `zecho-closeloop` + `zecho-digest` (Claw cron) + `zecho-verdict` write-back |
| 5 | Seed (thật + synthetic) + tập demo 3' |

---

## 4. Quyết định thiết kế đã chốt

| # | Quyết định | Lý do |
|---|---|---|
| D1 | **File-based store** (`data/*.md` + YAML frontmatter), agent thao tác bằng grep/glob/view/edit/create | zero infra, human-readable, seed/debug nhanh; custom code tối thiểu |
| D2 | **Dedup 2 tầng**: narrow theo `component` (enum) → LLM đọc `short_desc` của ứng viên → **fetch full body** cái nghi ngờ để xác nhận | bỏ keyword/synonym; robust với từ lạ; semantic do LLM, không cần vector DB |
| D3 | **Pool = `data/issues/` là source of truth**; **Jira = adapter optional** sau interface | D9: tắt Jira không vỡ core |
| D4 | **Đóng gói = bộ nhiều Claw skill** (triage/digest/closeloop/verdict) dùng chung **toolkit `zecho/`** (Python deterministic, có test); proactive = Claw cron khởi động skill | tách theo actor/trigger; quyết-định-phải-đúng ở toolkit, ngôn-ngữ/phán-đoán ở skill; mỗi skill demo độc lập |
| D5 | **Close-loop notify theo channel gốc**: report DM→DM, report group→reply group (@mention) | tự nhiên, minh bạch đúng nơi |
| D6 | **Vision là CORE** ở V1: đọc screenshot → prefill version/màn hình/device | giảm số câu clarify, tăng "wow" |
| D7 | **Soft-deflect có đường thoát** ("vẫn lỗi" → escalate) | deflect nhầm hại trust hơn miss dedup |
| D8 | **Verdict version-scoped** (`scope_versions`); report version mới hơn → re-open | chống verdict "ôi thiu" (regression) |
| D9 | **`short_desc` thay keyword**: mỗi issue có 1 dòng mô tả (LLM sinh) làm chỉ mục dedup tầng-1; narrow component rỗng → widen đọc toàn bộ short_desc (rẻ ở quy mô V1) | không phải nuôi synonym; chống miss do từ lạ / component lệch |
| D10 | **Seed = trộn**: vài chục case thật + synthetic cho đủ volume | demo dedup/learning thuyết phục |
| D11 | **Channel chính = Zalo group qua Claw bot**; fallback Claw-chat nếu Zalo chưa nối | chạy thật ưu tiên, không khóa cứng |
| D12 | **i18n: frontmatter EN-normalized, body nguyên ngôn ngữ**. Feedback EN/VI đều nhận; `short_desc` + mọi field = tiếng Anh; body (feedback gốc, Symptoms, verdict reason) giữ ngôn ngữ gốc; **bot trả lời theo ngôn ngữ reporter** | tìm kiếm/dedup nhất quán + **dedup xuyên ngôn ngữ** (VI↔EN cùng bug gom chung); vẫn giữ nguyên văn gốc |

---

## 5. Kiến trúc & ranh giới module

Nguyên tắc: mỗi module **một việc**, interface rõ, test độc lập. `data/issues/` là trục chung.
Đóng gói thành **4 skill** (LLM, judgment) dùng chung **toolkit `zecho/`** (Python, deterministic, có test). Cột "Thuộc" = skill/toolkit chứa nó.

| # | Module | Việc (1 câu) | Interface (in → out) | Phụ thuộc | Thuộc |
|---|---|---|---|---|---|
| 1 | **Channel** | nhận @mention+media / gửi tin | `inbound(event)`→msg; `claw_send(channel,msg)` | Claw | Claw + toolkit `claw.py` |
| 2 | **Intake+Enrich** | vision đọc screenshot, **detect ngôn ngữ**, tạo feedback file | msg → `data/feedback/<date>/fb_*.md` (+slots, +lang) | LLM multimodal | skill `zecho-triage` |
| 3 | **Clarify** | slot-fill theo issue_type, hỏi ≤2–3, dừng đúng lúc | feedback session → slots đủ-dùng | — | skill `zecho-triage` |
| 4 | **Validate/Dedup** ⭐ | narrow component → LLM đọc short_desc → fetch full → phân loại | feedback → `{known\|fixed\|verdict\|self\|spam\|new, issue_id?}` | toolkit `issues/ownership` | skill `zecho-triage` |
| 5 | **Synthesize** | gán theme + tính priority | issue draft → `priority`, `theme` | toolkit `priority.py` | skill `zecho-triage` |
| 6 | **Route** | component → squad/group/oncall | component → `{squad,group_id,oncall}` | toolkit `ownership.py` | skill `zecho-triage` |
| 7 | **Pool** | upsert issue file, +reporter, cập nhật short_desc | decision → `data/issues/ISS-*.md` (+ optional Jira) | toolkit `issues.py` (+`pool_jira.py`) | skill `zecho-triage` |
| 8 | **Close-loop** | chọn reporter notify (**exactly-once**) + mark; soạn lời theo lang | trigger → Claw sends | toolkit `issues/render/claw` | skill `zecho-closeloop` (cron ~5') |
| 9 | **Digest** | per-squad theo ngưỡng + PO rollup narrative + escalation | trigger → Claw sends | toolkit `threshold/ownership/render` | skill `zecho-digest` (cron 9:00) |
| 10 | **PO-verdict write-back** | verdict → issue file (`scope_versions`) hoặc kb/; feed lại #4 | verdict event → issue/kb edit | toolkit `issues.append_verdict` | skill `zecho-verdict` |

**Phân vai LLM vs toolkit (mấu chốt của multi-skill):**
- **Toolkit (deterministic, test):** chọn-ai-notify + mark-notified (exactly-once), tính ngưỡng/SLA, cấp ID, +freq, query pool, verdict write (reason bắt buộc), Jira REST.
- **Skill (LLM, judgment):** dedup phán, clarify, route, **soạn ngôn ngữ theo lang**, narrative digest, hiểu intent PO.
- **closeloop là HYBRID có chủ đích:** LLM chỉ soạn *lời*; toolkit quyết *gửi cho ai & đánh dấu* — đường notify sai là mất uy tín.

**Adapter boundaries (để Jira optional, D3):**
- `Pool` (#7) gọi interface `Adapter.upsert(issue)` — impl mặc định `NoopAdapter` (no-op); impl Jira = `pool_jira.py` + `JiraAdapter`.
- `Close-loop` (#8) nguồn sự thật là **state trong issue file**; nếu Jira bật, `JiraAdapter.recently_changed()` poll JQL
  cập nhật state vào issue file. Không có Jira → state đổi qua `zecho-verdict`. Engine không đổi.

**Code thật = toolkit `zecho/` (có test) + `pool_jira.py` (optional).** Skill là prompt gọi toolkit; không có "script cron" tách rời — cron khởi động skill.

---

## 6. Data contracts

Mọi entity = 1 file markdown: **YAML frontmatter** (greppable) + body (LLM đọc).

> **Quy ước ngôn ngữ (D12):** **frontmatter = tiếng Anh** (mọi field + `short_desc`, EN-normalized do LLM);
> **body = nguyên ngôn ngữ người report** (feedback gốc, `## Symptoms`, `## PO verdict` reason). Bot trả lời reporter theo ngôn ngữ của họ (`lang` lưu ở feedback file).

```
data/
  ownership.md                      # squad ↔ component, group_id, oncall (bảng markdown)
  feedback/<YYYY-MM-DD>/fb_<id>.md  # raw inbound, 1 file / feedback
  issues/<ISS-id>.md                # canonical pooled issue = SOURCE OF TRUTH
  kb/<topic>.md                     # quy tắc chung (verdict không gắn issue cụ thể)
  notifications.log                 # append-only audit
```

### 6.1 Issue file (`data/issues/ISS-0007.md`) — source of truth
Frontmatter bắt buộc: `id, status, theme, component, squad, severity, priority, affected_versions,
affected_devices, fixed_in, freq, first_seen, last_seen, short_desc`; optional `jira_key`.
- `short_desc`: 1 dòng **tiếng Anh** mô tả vấn đề nền (LLM sinh/normalize khi tạo issue) — **chỉ mục dedup tầng-1** (cho dedup xuyên ngôn ngữ), mô tả bản chất lỗi không phải lời 1 reporter.
- `status ∈ {new, routed, awaiting_po_reason, in_progress, resolved, closed}`
- Body: `## Symptoms` (gộp để LLM phán dedup), `## Reporters` (append-only: `@user | channel | date | notified:no`),
  và khi có PO phán → block `## PO verdict`.

### 6.2 `## PO verdict` block (learning, D7/D8)
```
## PO verdict
- verdict: not_a_bug      # not_a_bug | wont_fix | invalid | backlog | fixed
- by: @po_pay | 2026-06-15
- reason: <bắt buộc — 1 dòng lý do>
- scope_versions: 25.6.0, 25.6.1   # verdict CHỈ áp cho các version này
```
Quy tắc: **verdict trống `reason` → không hợp lệ**; issue vào `awaiting_po_reason`, close-loop hoãn notify
tới khi PO cho lý do.

### 6.3 Feedback file
Frontmatter: `id, reporter, channel, issue_type, app_version, device, lang, status, linked_issue, created_at`.
`lang ∈ {vi, en}` (detect ở Enrich, quyết ngôn ngữ bot trả lời). `status ∈ {new, clarifying, pooled, deflected, dropped}`. Body = nội dung feedback gốc (nguyên ngôn ngữ).

### 6.4 ownership.md
Bảng: `| squad | components | feedback_group_id | oncall |`. Đọc để route (#6) và biết group nào để post (#9).

### 6.5 Phân ranh `issues/` vs `kb/` (rule cho LLM, tránh lệch)
> "Verdict này còn đúng khi đổi sang issue khác không? **Có → `kb/`** (quy tắc chung). **Không → issue file**."

### Priority
`priority = w1*impact + w2*frequency + w3*segment + w4*severity` — ghi thẳng frontmatter (minh bạch, demo được).
Trọng số mặc định (configurable): `w1=0.3, w2=0.3, w3=0.15, w4=0.25`; mỗi thành phần chuẩn hoá về thang 0–100.

---

## 7. Luồng chính (4)

### 7.1 Triage (reactive, trong agent)
`Channel(#1) → Enrich(#2) → Clarify(#3) → Validate(#4) →`
- `new` → `Synthesize(#5) → Route(#6) → Pool(#7)` (tạo issue, +reporter, sync Jira nếu bật)
- `known` → Pool +1 (tăng freq, +reporter, cập nhật short_desc/symptoms nếu lộ facet mới)
- `fixed` → deflect "update lên X"
- `verdict` (trùng issue có PO verdict, **cùng scope_versions**) → **soft-deflect** kèm lý do; version mới hơn → re-open (D8); user "vẫn lỗi" → escalate (D7)
- `self` (rule trong kb) → trả cách tự xử lý
- `spam` → drop

### 7.2 Close-loop (cron `close_loop.py`, ~5')
Quét issue file có state `resolved`/có `## PO verdict` (và poll Jira nếu bật) →
- verdict thiếu reason → set `awaiting_po_reason`, hỏi PO 1 dòng lý do trong group, **hoãn** notify.
- đủ điều kiện → render msg (fix/verdict+reason) → gửi từng reporter `notified:no` **theo channel gốc** (D5) → đánh dấu `notified:yes`.

### 7.3 Learning (PO-verdict write-back, #10)
PO phán qua **tag-bot trong group** *hoặc* **Jira status** → ghi `## PO verdict` (+`scope_versions`) vào issue,
hoặc rule chung vào `kb/`. File này chính là thứ Validate(#4) grep ở case sau → tự tái dùng. Không training.

### 7.4 Digest (cron `daily_digest.py`, 9:00)
- **Per-squad**: grep issue 24h theo squad → **chỉ post group squad nếu vượt ngưỡng** → im lặng nếu không. Ngưỡng mặc định (configurable):
  - **High mới**: có issue `severity ≥ high` mới route vào squad trong 24h, HOẶC
  - **Spike**: `freq` 1 cluster tăng ≥ **50%** so với 24h trước, HOẶC ≥ **10** feedback mới/24h, HOẶC
  - **SLA breach**: issue `high` routed chưa ack sau **4h** (Critical: **1h**), HOẶC
  - **Recurring**: issue đã `resolved` nhưng có feedback mới quay lại.
- **PO rollup**: post group PO — top themes theo volume, new vs recurring, trend delta vs hôm qua.
- **Realtime escalation**: severity Critical → ping oncall **ngay khi POOLED** (trong luồng agent, không đợi cron).

---

## 8. Tiêu chí done / acceptance (testable)

Demo happy-path chạy thật trên Zalo group qua Claw, đạt 5 checkpoint:

| # | Acceptance | Cách kiểm |
|---|---|---|
| A1 | **Dedup** | Thả feedback trùng pool → issue cũ `freq+1`, **không** tạo issue mới; thả feedback mới → issue mới + route đúng squad |
| A2 | **Close-loop** | Set 1 issue `resolved` → **tất cả** reporter `notified:no` được nhắn đúng channel gốc, rồi `notified:yes` |
| A3 | **Learning** | PO phán `not_a_bug`+reason+scope_versions cho ISS-X → feedback giống y hệt **tự soft-deflect** kèm đúng lý do; feedback ở version mới hơn → **không** deflect (re-open) |
| A4 | **Digest** | Group squad chỉ nhận post khi vượt ngưỡng; ngày không có gì → im lặng; PO group nhận rollup |
| A5 | **Jira-optional** | Tắt Jira adapter → A1–A4 vẫn pass (pool = file) |

Metrics chiếu demo: % auto-deflect · feedback→triaged (phút) · dedup 1.000→N · % route đúng ·
**% case học từ PO verdict** · giờ PO tiết kiệm/ngày.

---

## 9. Rủi ro & giả định

| Rủi ro / giả định | Mitigation |
|---|---|
| Claw có Zalo + cron + proactive send | Nếu Zalo chưa nối → fallback channel Claw-chat (D11); cron đã xác nhận có |
| **Dedup miss** (component phân loại lệch → narrow trượt) | `component` multi-value; narrow rỗng → widen đọc toàn bộ `short_desc` (rẻ ở quy mô V1); LLM phán cuối trên full body |
| **Verdict ôi thiu** (not_a_bug cũ bịt regression mới) | `scope_versions` + re-open ở version mới (D8) |
| **Deflect nhầm hại trust** | Soft-deflect + đường thoát "vẫn lỗi" (D7) |
| PO flip Jira không ghi lý do | State `awaiting_po_reason`, hỏi PO 1 dòng, hoãn notify reporter |
| LLM làm lệch YAML frontmatter | Convention chặt trong SKILL.md; optional `append_verdict.py` deterministic |
| Demo "1.000→90s" chậm/đắt nếu cluster live | Seed pool sẵn; live chỉ dedup vài feedback mới đối chiếu pool |
| Seed dữ liệu | Trộn vài chục case thật + synthetic (D10) |

---

## 10. Tham chiếu
- Kiến trúc & sơ đồ chi tiết: [`docs/architecture.md`](../architecture.md)
- Đóng gói skill (cấu trúc thư mục, pseudocode scripts): architecture mục 8.
- Demo script 3 phút: architecture mục 7.
