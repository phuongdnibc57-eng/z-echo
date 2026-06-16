# "Z-Echo" — Voice-of-Customer Agent (Zalo)

### Kiến trúc build nhanh cho Claw-a-thon (24–48h)

> Mục tiêu: agent có **kiến thức sản phẩm Zalo**, nhận feedback (kèm ảnh) → hỏi follow-up
> → validate/dedup/deflect → pool & route đúng squad → close-loop báo lại reporter →
> **chủ động post vào group feedback từng squad (daily, chỉ khi có gì cần notice)** + digest PO →
> PO phản hồi (Jira / tag bot) → verdict ghi ngược vào pool → **tự bồi knowledge** cho case sau.

---

## 0. SCOPE V1 — CHỈ INTERNAL EMPLOYEE (build trước, rush)

Lý do internal-first: bỏ rủi ro tích hợp lớn nhất, vẫn giữ phần lõi judges chấm.

**Bối cảnh:** nhân viên Zalo dogfood sản phẩm → report feedback/bug trong **group nội bộ**
(tag bot) hoặc web UI. Reporter có identity sẵn → close-loop dễ. KB = Confluence nội bộ.

**IN (V1):**

- Kênh: **Zalo group qua Claw bot** (tag bot, nhận @mention + media); fallback Claw-chat nếu Zalo chưa nối.
- **Vision CORE**: đọc screenshot → prefill version/màn hình/device.
- Nhận feedback **EN/VI**; frontmatter EN-normalized, body nguyên ngữ.
- Clarify nhẹ (NV tự khai version/device tốt → ít slot).
- Validate + **dedup** (short_desc 2 tầng) trên pool file-based.
- Synthesize + priority + **route** theo ownership map.
- **Pool = `data/issues/`** (source of truth); **sync Jira optional** (tắt được, core vẫn chạy).
- **Close-loop** nhắn lại NV theo channel gốc (DM→DM, group→group).
- **Daily squad digest** + PO digest theo ngưỡng notice.
- **PO-verdict write-back** → tự bồi knowledge cho case sau.

**OUT (hoãn sang V2 — external users):**

- Zalo OA webhook / kênh end-user thật.
- **Full multi-language (>EN/VI) + localize tone end-user** — V1 đã nhận EN/VI (xem D12 ở spec).
- Spam/abuse filter (internal = noise thấp).
- Self-help flow phức tạp cho end-user (V1 chỉ deflect bằng rule chung trong `kb/`).
- Segment/churn-risk scoring.

**Hệ quả tốc độ:** bỏ Phase tích hợp kênh ngoài → tập trung 100% vào lõi
validate→dedup→route→pool→close-loop→digest. Rút build từ 48h xuống \~24-30h.

---

## 1. Sơ đồ hệ thống

```javascript
                    ┌──────────────────────────────────────────────┐
   Zalo DM / Group  ───▶ │  CLAW BOT (channel — nhận & gửi, kể cả     │
   (@mention bot)        │  proactive) → normalize message + media      │
   + screenshot          │  - phát hiện DM vs group, lấy reporter id     │
                         └───────────────┬──────────────────────────────┘
                                         ▼
                         ┌──────────────────────────────────────────────┐
                         │  VISION / MEDIA (LLM multimodal)             │
                         │  - hiểu screenshot                            │
                         │  - bóc metadata: màn hình, error, version,    │
                         │    device → prefill slots                     │
                         └───────────────┬──────────────────────────────┘
                                         ▼
        ┌────────────────────────────────────────────────────────────────────────┐
        │              AGENT ORCHESTRATOR  (LLM trên Claw + file tools)            │
        │                                                                          │
        │  CLARIFY ──▶ VALIDATE ──▶ SYNTHESIZE ──▶ ROUTE ──▶ POOL                  │
        │   (slot-      (dedup/      (cluster +     (theme→     (Jira issue +       │
        │    filling     deflect/     priority)      squad)      reporter link)     │
        │    theo gap)   spam)                                                      │
        └───┬─────────────┬──────────────┬───────────────┬───────────────┬─────────┘
            ▼             ▼              ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌────────────┐  ┌────────────────┐
   │ KNOWLEDGE  │  │ DATA STORE │  │ DEDUP    │  │ OWNERSHIP  │  │ POOL / TICKETS │
   │ (RAG)      │  │ files .md  │  │ grep +   │  │ ownership  │  │ Jira (issues)  │
   │ Confluence │  │ frontmatter│  │ LLM phán │  │ .md        │  │ real backend   │
   │ → data/kb  │  │ feedback/  │  │ (no DB)  │  │ squad↔comp │  │                │
   │            │  │ issues/    │  │          │  │            │  │                │
   └────────────┘  └─────┬──────┘  └──────────┘  └────────────┘  └────────────────┘
                         │
                         ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │  CRON JOBS (Claw scheduler — gọi script trong skill)                           │
   │   • CLOSE-LOOP (mỗi 5'): Jira issue đổi state → nhắn lại reporter                │
   │   • DAILY per-squad digest: post vào group squad NẾU vượt ngưỡng notice         │
   │   • PO digest: tổng hợp cuối ngày (trend delta, new vs recurring)               │
   │   • REALTIME escalation: severity cao → ping on-call ngay (trong luồng agent)    │
   └──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent loop (orchestration logic)

State machine cho mỗi feedback session:

```javascript
NEW
 └▶ ENRICH      : vision bóc metadata, prefill slots
 └▶ CLARIFY     : tính missing slots theo issue_type; hỏi tối đa N câu; biết lúc dừng
 └▶ VALIDATE    : narrow component → LLM đọc short_desc của ứng viên → fetch full body cái nghi ngờ
        ├─ trùng issue đã có      → +1, +reporter, cập nhật short_desc nếu lộ facet mới  → DEFLECT_KNOWN
        ├─ đã fix ở version > user → trả "update lên X"                   → DEFLECT_FIXED
        ├─ trùng issue có PO verdict (cùng affected_versions) → SOFT-deflect kèm lý do
        │     · report ở version MỚI hơn → KHÔNG deflect, re-open (chống verdict ôi thiu)
        │     · user gõ "vẫn lỗi" → bỏ deflect, escalate lại               → DEFLECT_VERDICT*
        ├─ không phải bug (rule chung trong kb/) → trả cách tự xử lý       → DEFLECT_SELF
        ├─ spam/abuse              → drop                                  → DROPPED
        └─ signal mới (confidence) → tiếp
 └▶ SYNTHESIZE  : gán cluster, tính priority score
 └▶ ROUTE       : map theme → squad; chọn severity → SLA
 └▶ POOLED      : tạo/đổi Jira issue; lưu issue↔reporter
 └▶ (async) PO_VERDICT : PO phán (Jira status / tag bot) → edit issue file (resolution + ## PO verdict) → bồi knowledge cho dedup
 └▶ (async) CLOSED : issue resolved HOẶC có verdict-kèm-lý-do → notify reporters (kèm lý do)
```

**Slot template theo issue\_type** (information-gap engine):

| issue\\_type | slots bắt buộc |
| --- | --- |
| crash | device, os\\_version, app\\_version, repro\\_steps |
| ux\\_complaint | screen/flow, expectation |
| payment\\_fail | txn\\_id, amount, time, method |
| performance | screen, network, frequency |
| feature\\_request | use\\_case, current\\_workaround |

Quy tắc dừng: hỏi tối đa **2–3 câu**; slot nào vision đã prefill thì skip; sau cap thì xử lý với thông tin hiện có.

---

## 3. Data store — FILE-BASED (markdown + frontmatter, agent grep/glob)

Không SQLite, không vector DB. Mọi entity = 1 file markdown có **YAML frontmatter** để grep theo
field, body để LLM đọc. Agent Claw dùng grep/glob/view/edit natively → gần như **không phải viết tool**.

> **Quy ước ngôn ngữ (D12):** feedback nhận cả EN/VI. **Frontmatter = tiếng Anh** (mọi field + `short_desc`,
> do LLM normalize) → tìm kiếm/dedup nhất quán + **dedup xuyên ngôn ngữ**. **Body = nguyên ngôn ngữ gốc**
> (feedback, `## Symptoms`, `## PO verdict` reason). Bot trả lời reporter theo `lang` của họ.

### Cây thư mục

```javascript
data/
  ownership.md                      # 1 file: squad ↔ component, group_id, oncall
  feedback/<YYYY-MM-DD>/fb_<id>.md  # raw inbound, 1 file / feedback
  issues/<ISS-id>.md                # canonical pooled issue (the "pool"); mirror jira_key
  notifications.log                 # append-only audit (close-loop / digest đã gửi)
```

### Issue file — `data/issues/ISS-0007.md` (source of truth của pool)

```markdown
---
id: ISS-0007
jira_key: PAY-2451            # set sau khi pool_jira tạo
status: routed               # new|routed|awaiting_po_reason|in_progress|resolved|closed
theme: payment-qr-fail
component: payment, qr        # ← grep field để narrow dedup
squad: payment
severity: high
priority: 82
affected_versions: 25.6.0, 25.6.1
affected_devices: android-14
fixed_in:                    # set khi resolved → trigger close-loop
freq: 18
first_seen: 2026-06-15
last_seen: 2026-06-15
short_desc: QR payment spins then errors out, Android 14 only   # ← EN-normalized, chỉ mục dedup tầng-1 (LLM sinh)
---
# Thanh toán QR fail trên Android 14
## Symptoms (gộp từ nhiều feedback — agent đọc để phán dedup)
- Quét QR xong xoay vòng rồi báo lỗi
- Chỉ trên Android 14, version 25.6.x
## Reporters (append-only — phục vụ close-loop)
- @nvA | zalo:group:prod-payment | 2026-06-15 | notified:no
- @nvB | zalo:dm | 2026-06-15 | notified:no
```

### Feedback file — `data/feedback/2026-06-15/fb_0042.md`

```markdown
---
id: fb_0042
reporter: @nvA
channel: zalo:group:prod-payment
issue_type: payment_fail
app_version: 25.6.1
device: android-14
lang: vi                      # vi|en — detect ở Enrich, quyết ngôn ngữ bot trả lời
status: pooled                # new|clarifying|pooled|deflected|dropped
linked_issue: ISS-0007        # set sau dedup
created_at: 2026-06-15T22:10
---
Quét QR trả tiền thì app xoay vòng rồi báo lỗi, thử 3 lần đều vậy.   # body giữ nguyên ngôn ngữ gốc
```

### ownership.md (đọc để route + biết group nào để post)

```markdown
| squad | components | feedback_group_id | oncall |
|-------|-----------|-------------------|--------|
| payment | payment, qr, wallet | zalo:group:squad-payment | @oncall_pay |
| messaging | chat, sticker, call | zalo:group:squad-msg | @oncall_msg |
```

### Dedup 2 tầng (narrow + LLM đọc, không keyword)

```javascript
# Tầng 1 — narrow theo component (enum ổn định), LLM đọc short_desc của ứng viên
grep -rl "component: payment" data/issues/   →  view frontmatter (short_desc) các file
   →  LLM: cái nào nghi trùng?
   (narrow ra rỗng → widen: đọc short_desc TOÀN BỘ issue — mỗi file 1 dòng nên rẻ)
# Tầng 2 — fetch full body cái nghi ngờ để xác nhận
view data/issues/ISS-0007.md (## Symptoms)  →  LLM: trùng? +1 : tạo mới

# Daily squad digest: lọc frontmatter
grep -rl -e "squad: payment" data/issues/ | xargs grep -l "status: routed" | grep "severity: high"

# Close-loop: issue đã resolved, reporter chưa nhắn
grep -rl "status: resolved" data/issues/  →  trong file tìm "notified:no"
```

`priority` = w1*impact + w2*frequency + w3*segment + w4*severity (ghi thẳng vào frontmatter, minh bạch).

> **Vì sao bỏ keyword:** grep keyword lexical → vỡ với từ lạ + phải nuôi synonym. Thay bằng `short_desc`
> (1 dòng mô tả bản chất lỗi do LLM sinh) làm chỉ mục tầng-1: LLM **đọc** short_desc thay vì so khớp chuỗi,
> nghi ngờ thì fetch full body. Robust với cách diễn đạt khác nhau, không phải maintain từ khoá.

> **Chống miss khi component lệch:** `component` cho phép multi-value; nếu narrow ra rỗng → widen đọc toàn bộ
> short_desc (rẻ ở quy mô V1). Quy mô rất lớn mới cần ANN/embeddings — ngoài scope V1.

> **Ranh giới `issues/` vs `kb/` (phải dứt khoát kẻo LLM làm lệch):**
> - Verdict **gắn 1 issue cụ thể** (vì sao ISS-0007 là not_a_bug) → ở **trong issue file** (`## PO verdict`).
> - **Quy tắc chung, không gắn issue nào** (vd "lỗi múi giờ luôn là do user config") → 1 file trong `data/kb/`.
> - Rule cho LLM: "verdict này còn đúng khi đổi sang issue khác không? Có → kb/. Không → issue file."

---

## 4. Daily per-squad group notification (phần bạn vừa thêm)

Mục tiêu: bot **chỉ lên tiếng khi đáng** → tránh spam group.

**Trigger ngưỡng "cần notice"** (post vào `squad.feedback_group_id`):

- Có issue **mới severity ≥ High** route vào squad, HOẶC
- **Spike**: 1 cluster tăng ≥ X% / ≥ Y feedback trong 24h, HOẶC
- **SLA breach**: issue đã route nhưng quá hạn chưa ack, HOẶC
- Issue **recurring** (đã fix nhưng quay lại).

Nếu không có gì vượt ngưỡng → **không post** (hoặc post 1 dòng "hôm nay không có gì cần chú ý" tùy cấu hình).

**Cấu trúc bản tin squad (daily):**

```javascript
🟠 [Squad Payment] Daily feedback digest — 15/06
• 🔴 MỚI/High: "Thanh toán QR fail trên Android 14" — 18 báo cáo (▲ từ 5 hôm qua)
   → Jira issue PAY-2451 đã tạo · cần ack trước 12h
• 🟡 Recurring: "OTP chậm" quay lại sau 25.6.2 — 7 báo cáo
• 🟢 Trend: tổng complaint Payment ▼ 12% tuần này
[Mở backlog] [Gán owner]
```

**Realtime escalation** (không đợi daily): severity Critical → ping `oncall_handle` ngay khi POOLED.

**PO digest (1 group tổng):** top themes theo volume, new vs recurring, trend delta vs hôm qua/release, mục "cần PO quyết".

Cron (Claw): job `close_loop` chạy mỗi \~5' + job `daily_digest` chạy 9:00. Cả hai là **script trong skill**,
không cần process riêng. Realtime escalation Critical xử lý ngay trong luồng agent (không đợi cron).

---

## 4B. PO feedback ngược → write-back & tự bồi knowledge

Mục tiêu: khi PO phản hồi lên feedback (không phải bug / chưa valid / để backlog / đã xử lý…),
verdict đó được ghi ngược vào pool và **tự thành knowledge** cho case tương tự về sau — **không subsystem mới**.

**Hai kênh PO phản hồi:**

- **Trên Jira:** đổi status/resolution (Not a bug / Won't Fix / Invalid / Done), set `fixed_in`. → `close_loop` poll bắt được.
- **Trong group:** tag bot kèm verdict + lý do. → agent xử lý ngay trong luồng.

**Bot làm gì (toàn bộ là `edit` file — native, ~0 code):**

1. Ghi vào `data/issues/ISS-xxxx.md`: set `status`/`resolution`/`fixed_in`, append block verdict:

```markdown
## PO verdict
- verdict: not_a_bug          # not_a_bug | wont_fix | invalid | backlog | fixed
- by: @po_pay | 2026-06-15
- reason: do user bật sai múi giờ, không phải lỗi app
- scope_versions: 25.6.0, 25.6.1   # verdict CHỈ áp cho các version này (chống ôi thiu)
```

2. **Tái dùng tự động (có guard):** file này chính là thứ VALIDATE grep. Case sau giống → agent đọc verdict + reason,
   **soft-deflect** tại intake ("giống ISS-0007, PO đã phán not_a_bug vì …, bạn vẫn thấy lỗi? gõ 'vẫn lỗi'").
   **Issue file = knowledge**, không vector DB / không training.
   - **Chống verdict ôi thiu:** verdict chỉ áp trong `scope_versions`. Feedback ở **version mới hơn** → KHÔNG deflect,
     **re-open** issue (regression có thể đã quay lại). Verdict cũ không được phép bịt miệng signal mới.
   - **Soft, không cứng:** auto-deflect luôn kèm đường thoát ("vẫn lỗi" → escalate). Deflect nhầm hại trust hơn miss dedup.
3. **Đóng vòng cho reporter:** `close_loop` notify không chỉ khi `resolved` mà cả khi có **verdict-kèm-lý-do**
   → reporter biết "không phải bug vì X" / "sẽ fix ở Y".

**Nuance bắt buộc — phải có LÝ DO, không chỉ status:** verdict trống lý do thì lần sau agent không học được gì.
Nếu PO flip Jira mà không comment → issue vào state **`awaiting_po_reason`**: `close_loop` **hoãn** notify reporter,
bot hỏi PO đúng **1 dòng lý do** trong group squad; khi lý do về mới ghi verdict + notify. (Không có lý do → không close-loop.)

**Verdict riêng issue vs quy tắc chung** (xem rule ở mục 3): verdict gắn 1 issue → ở trong issue file;
quy tắc chung không gắn issue → 1 file `data/kb/` để nhánh DEFLECT_SELF (grep, **không phải RAG**) nhặt được.

**Ranh giới toolkit vs skill:**

- Ghi verdict vào issue file = **toolkit** `issues.append_verdict(...)` (reason bắt buộc, version-scoped) — gọi từ skill `zecho-verdict`.
- Đẩy status ngược lên Jira = `scripts/pool_jira.py` (REST, có auth, optional).
- Notify reporter theo verdict = skill `zecho-closeloop`: toolkit khoá notify-set + mark exactly-once, LLM soạn lời theo lang.

---

## 5. Tech stack (chọn để build NHANH)

| Layer | Lựa chọn | Vì sao nhanh |
| --- | --- | --- |
| Packaging | **Bộ nhiều Claw skill** (triage/digest/closeloop/verdict) + toolkit `zecho/` | tách theo actor/trigger; mỗi skill demo độc lập |
| Agent | **LLM trên Claw** (native file tools) + import toolkit | grep/glob/view/edit sẵn; quyết-định-đúng ở toolkit |
| Vision | LLM multimodal (đọc screenshot trực tiếp) | khỏi dựng OCR riêng |
| Data store | **File markdown + frontmatter** (grep/glob) | zero infra, human-readable, seed nhanh |
| Dedup | **narrow component → LLM đọc short_desc → fetch full** (2 tầng) | bỏ keyword/synonym; không cần vector DB; semantic nhờ LLM |
| KB/RAG | Confluence dump → markdown trong `data/kb/` | grep + LLM đọc, ground sản phẩm |
| Pool thật | **Jira** (REST API, adapter optional) | demo chạy thật; tắt được, core vẫn chạy |
| Scheduler | **Claw cron** → khởi động skill theo lịch | không APScheduler/sidecar/process riêng |
| Channel | **Zalo bot qua Claw** (proactive outbound) | Claw lo nhận/gửi, kể cả gửi chủ động |

**Toolkit `zecho/` (deterministic, có test) là nơi chứa mọi quyết-định-phải-đúng:**

- `issues.py` (pool CRUD, reporters, verdict), `ownership.py`, `threshold.py`, `versions.py`, `priority.py`.
- `jira_adapter.py` (Noop/Jira), `claw.py` (send), `render.py` (template fallback).
- Skill (LLM) chỉ lo **phán đoán + ngôn ngữ**; gọi toolkit cho phần phải chính xác.

**Nguyên tắc fake/real cho hackathon:**

- **REAL**: dedup (2 tầng short_desc+LLM)→route→pool (file/Jira), close-loop, digest. Đây là phần judges chấm.
- **MOCK nếu thiếu thời gian**: vision → vài screenshot mẫu set sẵn; KB → dump 1 phần Confluence.

---

## 6. Kế hoạch build

→ Xem **mục 8** (kế hoạch V1 trên Claw, file-based, \~18-22h). Mục này giữ lại bản 48h gốc làm tham chiếu
nếu cần mở rộng scope; nhưng bản chính thức để rush là mục 8.

---

## 7. Demo script 3 phút (kill shot)

1. (0:00) Thả feedback + screenshot vào group, tag bot.
2. (0:30) Bot đọc ảnh → "màn Payment, v25.6" → hỏi đúng 1 câu (device).
3. (1:00) Case A → deflect "trùng PAY-234, fix ở 25.7". Case B → mới → tạo Jira issue, route Payment squad (chạy thật trên Jira).
4. (1:30) Tua: đổ **1.000 feedback → 90s** ra backlog đã rank + số dedup.
5. (2:00) Bật **daily squad digest** trong group Payment (chỉ post vì có spike).
6. (2:20) Mark PAY-234 = fixed → **12 reporter gốc tự được nhắn lại**. Khép vòng.
7. (2:40) **Kill-shot — vòng học:** PO phán 1 issue khác là `not_a_bug` + lý do ("lỗi múi giờ do config").
   Thả ngay 1 feedback **y hệt** → bot **tự deflect kèm đúng lý do PO**, có đường thoát "vẫn lỗi". Agent đã học.

**Metrics chiếu cuối:** % auto-deflect · feedback→triaged (phút) · dedup 1.000→N · % route đúng · **% case học từ PO verdict** · giờ PO tiết kiệm/ngày.

---

## 8. ĐÓNG GÓI — BỘ NHIỀU CLAW SKILL DÙNG CHUNG 1 TOOLKIT

Z-Echo = **một bộ skill composable**, không phải 1 skill khổng lồ. Mỗi skill = 1 actor/trigger riêng,
tất cả gọi chung **toolkit `zecho/`** (thư viện Python deterministic, có test). Nguyên tắc tách:
**quyết-định-phải-đúng → toolkit (deterministic, test); ngôn-ngữ/phán-đoán → skill (LLM).**

### Cấu trúc

```javascript
zecho/                     # TOOLKIT deterministic (có test) — KHÔNG phán đoán
  issues.py  ownership.py  threshold.py  versions.py  priority.py
  jira_adapter.py  claw.py  render.py(fallback templates)
skills/
  zecho-triage/SKILL.md    # reactive: capture→clarify→dedup→route→pool (LLM phán)
  zecho-digest/SKILL.md     # CRON 9:00: toolkit lấy data+ngưỡng → LLM viết narrative digest → post
  zecho-closeloop/SKILL.md  # CRON ~5': toolkit KHOÁ notify-set + mark (exactly-once) → LLM soạn lời theo lang
  zecho-verdict/SKILL.md    # reactive: PO tag bot → write-back verdict (+reason, scope_versions)
scripts/
  pool_jira.py            # adapter Jira (REST) — tích hợp ngoài duy nhất
data/                     # store file-based (xem mục 3): ownership.md feedback/ issues/ kb/
```

### Vì sao tách skill thế này (ranh giới theo actor + trigger)

| Skill | Trigger | LLM lo (judgment) | Toolkit lo (deterministic) |
|---|---|---|---|
| **zecho-triage** | NV tag bot + feedback | clarify, dedup phán, route, soạn reply | cấp ID, +1 freq, +reporter, query pool |
| **zecho-digest** | Cron 9:00 | narrative, trend "than phiền X ▲40%", "PO nên chú ý gì" | grep 24h, tính ngưỡng notice, rollup số |
| **zecho-closeloop** | Cron ~5' | soạn câu chữ theo `lang` reporter | **chọn ai notify + mark notified (exactly-once)**, đọc verdict/state |
| **zecho-verdict** | PO tag bot | hiểu intent, tách reason vs rule chung | ghi `## PO verdict`, set status, append kb |

> **closeloop là HYBRID có chủ đích:** việc *chọn reporter nào để gửi* và *đánh dấu đã gửi* phải
> **exactly-once** → để toolkit làm (an toàn, có test). LLM **chỉ** soạn lời. Không để LLM tự quyết
> "gửi cho ai" lúc 9h sáng — sai một cái là mất uy tín đường notify.

> **triage KHÔNG xé nhỏ:** clarify/dedup/route gắn chặt, chung state 1 feedback, không trigger độc lập
> → giữ trong 1 skill. Chỉ tách những gì **proactive/khác-actor** (digest, closeloop, verdict).

```javascript
       ┌──────────────────────── CLAW ────────────────────────┐
Zalo ◀─▶│ Zalo bot                                              │
        │  @mention feedback ─▶ skill: zecho-triage             │  reactive
        │  PO tag bot        ─▶ skill: zecho-verdict            │  reactive
        │  CRON ~5'          ─▶ skill: zecho-closeloop          │  proactive
        │  CRON 9:00         ─▶ skill: zecho-digest             │  proactive
        └───────────────┬───────────────────────┬──────────────┘
                        │ mọi skill import       │ Claw send
                        ▼                        │
                 ┌──────────────┐         ┌──────────────┐
                 │ toolkit zecho/│ ──────▶ │ data/*.md     │  (source of truth)
                 │ + pool_jira  │ ──────▶ │ Jira (optional)│
                 └──────────────┘         └──────────────┘
```

### Phần agent làm bằng NATIVE tools / toolkit

```javascript
# trong zecho-triage (LLM + native + toolkit)
dedup     = grep "component: X" data/issues/ → view short_desc ứng viên → fetch full nghi ngờ → LLM phán
upsert    = issues.create_issue(...) | issues.bump_frequency(...) | issues.add_reporter(...)   # toolkit
route     = ownership.route(parse_ownership(), component)                                       # toolkit
reply     = LLM soạn theo lang reporter

# trong zecho-verdict
write_verdict = issues.append_verdict(iid, verdict, by, reason, scope_versions)   # toolkit, reason bắt buộc
```

Tích hợp ngoài duy nhất phải code REST: `scripts/pool_jira.py` (tạo Jira issue, ghi `jira_key` ngược file).

### Build plan V1 (\~18-22h — toolkit có test + nhiều skill mỏng)

| Phase | Giờ | Ra cái gì |
| --- | --- | --- |
| 0. Scaffold | 1.5h | `zecho/` toolkit package + pytest; `data/` layout + ownership.md |
| 1. Toolkit core (TDD) | 5h | `frontmatter, versions, priority, issues, ownership, threshold, render, claw, jira_adapter` + tests |
| 2. skill **zecho-triage** ⭐ | 5h | SKILL.md: capture→clarify→**dedup 2 tầng**→route→pool (gọi toolkit) |
| 3. skill **zecho-closeloop** | 3h | SKILL.md gọi toolkit khoá notify-set/mark + soạn lời theo lang; cron ~5' |
| 4. skill **zecho-digest** + **zecho-verdict** | 4h | digest narrative (cron 9:00) + PO verdict write-back |
| 5. Seed + demo | 4h | seed pool (thật + synthetic) + tập demo 3' |

**Đường wow nhanh nhất:** Phase 1 (toolkit) → 2 (zecho-triage dedup) trước, rồi Phase 3-4 (proactive skills) để chốt hạ.

> **Lưu ý demo "1.000 feedback → 90s":** clustering 1.000 cái live bằng LLM sẽ chậm/đắt.
> Cách làm: **seed `data/issues/` như pool đã tích luỹ sẵn**, demo live chỉ chạy **dedup vài feedback mới**
> đối chiếu pool có sẵn → nhanh, vẫn thật, vẫn thấy "+1 vào issue đang có".
