# Tài liệu: 20260415-Huong-dan-dung-Claude-Code-dje-build-AssetCore-cho-ky-su-IT-lan-djau.pptx

## Slide 1

Hướng dẫn dùng Claude Code để build AssetCore cho kỹ sư IT lần đầu

Dưới đây là cách tôi sẽ hướng dẫn một kỹ sư IT lần đầu dùng Claude Code để build phần mềm kiểu AssetCore theo tài liệu BA, bám HTM/CMMS của WHO và kiến trúc IMMIS.

Điểm quan trọng đầu tiên: đừng dùng Claude Code như "máy sinh code". Với bài toán này, bạn phải dùng nó như kiến trúc sư phụ tá + BA phụ tá + dev pair programmer + QA reviewer. Vì AssetCore không phải một CMMS rời rạc; blueprint của dự án xác định đây là lớp mở rộng trên ERPNext v15 để quản lý toàn bộ vòng đời thiết bị y tế, với kiến trúc vận hành thống nhất, 4 khối HTM, 17 module, QMS 4 tầng, workflow, dữ liệu, tích hợp và dashboard cùng nối vào một vòng đời khép kín.

Về mặt nghiệp vụ, WHO 2025 cũng nhấn mạnh HTM không dừng ở asset management đơn thuần mà là một chiến lược tổng thể gồm procurement, installation, inventory, maintenance, QA, regulatory compliance, training và decommissioning; tức là phần mềm bạn xây phải phản ánh đầy đủ chuỗi đó chứ không chỉ có "tài sản + phiếu sửa chữa".

---

## Slide 2

### 1. Trước khi mở Claude Code: chuẩn bị đúng "battlefield"

Một kỹ sư mới hay sai ở chỗ mở Claude Code lên rồi yêu cầu "hãy build hệ thống". Cách đó gần như chắc chắn làm Claude đi chệch.

Bạn nên chuẩn bị 5 thứ trước:

Thứ nhất: repo sạch và có cấu trúc rõ

Với AssetCore, repo nên tách tối thiểu thành:

apps/assetcore hoặc thư mục app Frappe custom
docs/ba
docs/architecture
docs/qms
docs/workflows
docs/data-model
docs/api
docs/sprints
.claude/

Thứ hai: nạp toàn bộ bối cảnh nguồn đúng chỗ

Ít nhất phải có:

blueprint kỹ thuật AssetCore
hồ sơ kiến trúc IMMIS/QMS
SOP/form mẫu
bộ WHO liên quan procurement, inventory, maintenance, CMMS, decommissioning, needs assessment

Lý do là WHO 2025 coi inventory + maintenance system là một phần của HTM xuyên suốt từ procurement đến decommissioning, còn hồ sơ IMMIS của bạn lại chốt rõ 4 khối – 17 module và lớp governance/QMS đi cùng. Claude phải thấy cả hai lớp này cùng lúc mới suy luận đúng.

Thứ ba: chốt ranh giới giữa ERPNext core và AssetCore custom

Blueprint nói rất rõ: Frappe Asset là lõi nhưng không phải toàn bộ; phải mở rộng đúng chỗ, không sửa lõi trực tiếp, và nên build thành app riêng với hooks, custom DocType, workflow, report, dashboard riêng.

Thứ tư: chuẩn hóa "ngôn ngữ dự án"

Trong team, mọi người phải dùng cùng mã:

IMM-01 … IMM-17
QC / PR / WI / BM / HS / KPI-DASH
Asset, Device Model, Work Order, Lifecycle Event, Document Record, CAPA, Compliance Finding

Nếu không thống nhất ngôn ngữ, Claude sẽ tạo spec lệch nhau giữa BA và Dev. Blueprint đã chốt điều này rất rõ.

Thứ năm: xác định Wave 1 thật chặt

Tài liệu hiện tại chốt MVP kỹ thuật ưu tiên 6 module: IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12; đầu ra trọng tâm là asset registry, hồ sơ pháp lý-kỹ thuật, PM/CM, inspection/calibration và dashboard vận hành cơ bản.

---

## Slide 3

### 2. Hiểu đúng Claude Code sẽ làm gì cho bạn

Claude Code phù hợp nhất khi bạn giao cho nó 4 loại việc:

A. Phân rã yêu cầu BA thành artefact kỹ thuật

Ví dụ:

process map → workflow states
user story → DocType + field + permission + validation + API
SOP/QMS → checklist + approval matrix + audit rule

B. Thiết kế khung kỹ thuật có kiểm soát

Ví dụ:

ERD logic
mapping ERPNext core ↔ custom DocType
state machine
rule engine
permission matrix
event model

C. Sinh code có ranh giới rõ

Ví dụ:

DocType JSON/Python
hook
workflow state script
API endpoint
report query
test case skeleton

D. Review và refactor

Ví dụ:

kiểm tra code có vi phạm domain model không
phát hiện field trùng nghĩa
phát hiện logic không có audit trail
phát hiện dashboard không truy ngược source record

---

## Slide 4

### 3. Cách làm việc đúng với Claude Code cho người mới

Hãy đi theo nhịp này:

1

Bước 1: dùng Claude để "hiểu dự án", chưa vội code

Việc đầu tiên không phải "generate app". Việc đầu tiên là yêu cầu Claude tóm cấu trúc hệ thống theo tài liệu. Mục tiêu là buộc Claude dựng lại mental model dự án.

Bạn là solution architect và lead engineer cho AssetCore. Hãy đọc toàn bộ thư mục docs hiện có và tạo cho tôi: 1) Tóm tắt dự án 1 trang 2) Danh sách module IMM-01..IMM-17 3) Phạm vi Wave 1 4) 20 quyết định thiết kế cần khóa sớm 5) Danh sách điểm chưa rõ cần BA xác nhận. Không viết code.

2

Bước 2: yêu cầu Claude tạo "design baseline"

Blueprint của bạn nói rõ hai deliverable kỹ thuật bắt buộc trước sprint đầu tiên là ERD logic chi tiết và mapping ERPNext DocType ↔ AssetCore custom DocType.

Dựa trên blueprint và hồ sơ kiến trúc IMMIS, hãy tạo: 1) ERD logic cho Wave 1 2) Bảng mapping giữa ERPNext core và AssetCore custom DocType 3) Danh sách field bắt buộc / optional / computed 4) Quan hệ 1-1, 1-n, n-n 5) Các rủi ro nếu dùng sai ranh giới ERPNext core. Không viết code. Xuất ra markdown.

3

Bước 3: chốt state machine trước khi sinh DocType

Với hệ thống HTM/CMMS, sai state machine là hỏng cả hệ thống. Bạn cần yêu cầu Claude định nghĩa: lifecycle status, operational status, release/hold/retire/dispose logic, work order states, approval states, document states.

Hãy định nghĩa state machine cho: Medical Asset, Lifecycle Event, Work Order, Document Record, Compliance/CAPA. Bao gồm: state, transition, actor, pre-condition, post-condition, evidence required, audit trail required.

4

Bước 4: rồi mới cho Claude sinh spec kỹ thuật từng module

Thay vì "build all Wave 1", hãy đi từng module. Ví dụ với IMM-04, khi spec ổn mới tiếp tục sinh skeleton code Frappe theo spec đã chốt. Đó là cách dùng Claude Code an toàn nhất cho người mới.

Dựa trên tài liệu BA/QMS, hãy viết technical spec chi tiết cho IMM-04: mục tiêu module, actor, trigger, input, workflow, custom DocType cần có, field list, validation rules, SLA, audit events, dashboard metrics, test cases. Không viết code.

---

## Slide 5

### 4. Thứ tự build đúng cho AssetCore Wave 1

Với dự án này, trình tự build không nên theo ý thích dev, mà nên theo logic vận hành và kiểm soát hồ sơ.

Giai đoạn A

Nền tảng dữ liệu và truy vết

Device Model
Medical Asset
Asset Identifier đa lớp
Lifecycle Event
Document Record
QMS Artifact

Giai đoạn B

Engine vận hành

Work Order engine dùng chung
Maintenance Plan
Checklist Template
Assignment / SLA / escalation

Giai đoạn C

6 module Wave 1

IMM-04 lắp đặt, định danh, initial inspection
IMM-05 đăng ký, cấp phép, hồ sơ
IMM-08 PM
IMM-09 sửa chữa, spare part, firmware/software change control
IMM-11 inspection / calibration
IMM-12 corrective maintenance

Giai đoạn D

Dashboard vận hành cơ bản

Chỉ làm sau khi đã có source record thật. Hồ sơ kiến trúc đã cảnh báo rõ rủi ro dashboard đi trước dữ liệu nguồn.

Blueprint xác định rõ phải tách đúng item, model, asset, vendor, contract, location, work order, document, event; mọi nghiệp vụ quan trọng phải sinh record; không được để hành động quan trọng không có dấu vết. Work Order là engine trung tâm cho PM, CM, calibration, installation.

---

## Slide 6

### 5. Cách viết prompt cho Claude Code để ra kết quả tốt

Một kỹ sư mới thường prompt quá chung. Muốn Claude làm đúng, prompt nên có 6 phần:

1

Vai trò

"Bạn là lead Frappe architect / HTM domain engineer / QA reviewer…"

2

Nguồn sự thật

"Chỉ dùng các file trong docs/architecture, docs/ba, docs/qms…"

3

Phạm vi

"Chỉ làm IMM-04", "Chỉ làm ERD Wave 1", "Không chạm module khác"

4

Đầu ra bắt buộc

"Xuất markdown gồm sections A, B, C…"

5

Ràng buộc

"Không được gộp Asset và Device Model nếu chưa nêu rõ mapping"
"Không được thiết kế dashboard nếu chưa có source record"
"Không sửa ERPNext core"

6

Tiêu chí kiểm tra

"Phải có audit trail, owner, evidence required, downstream impact"

Một prompt tốt hơn sẽ trông như sau:

Bạn là senior Frappe architect có kinh nghiệm HTM/CMMS.
Nguồn sự thật là:
- docs/architecture/blueprint.md
- docs/architecture/qmsa.md
- docs/who/*
Mục tiêu: tạo technical spec cho IMM-08.
Ràng buộc:
- Không sửa ERPNext core
- Phải dùng Work Order engine chung
- Mọi bước phải có audit trail
- PM không được close nếu checklist mandatory fail
Đầu ra:
1) mục tiêu module
2) workflow
3) DocType/field
4) validation
5) permission
6) KPI/dashboard
7) test cases
8) rủi ro triển khai

---

## Slide 7

### 6. Những việc bắt buộc phải yêu cầu Claude review trước khi code nhiều

Blueprint của bạn nói có các quyết định thiết kế cần khóa sớm, nếu chậm sẽ dẫn đến tái cấu trúc tốn kém. Ít nhất phải khóa các câu hỏi này trước khi sprint đi sâu:

8 quyết định kiến trúc cần khóa sớm

Asset và AC Medical Asset là 1 record hay 2 record ánh xạ 1-1
state model 1 lớp hay 2 lớp
Work Order dùng chung hay tách
document lưu trong Frappe File hay DMS ngoài
QMS artifact quản như metadata hay chỉ link file
nguồn sự thật cho location/department
dashboard realtime hay snapshot
change control trong app hay ngoài app

Prompt mẫu cho decision memo

Claude Code rất giỏi giúp bạn làm "decision memo" cho các điểm này.

Hãy lập decision memo cho 8 quyết định
kiến trúc sau. Mỗi quyết định gồm:
- vấn đề
- phương án A/B/C
- ưu nhược
- tác động đến BA
- tác động đến code
- khuyến nghị
- quyết định tạm thời

---

## Slide 8

### 7. Cách ghép BA – Dev – QA – QMS trong Claude Code

Hệ thống này không chỉ là dev. Hồ sơ kiến trúc đã chốt actor map và QMS 4 tầng: L1/QC, PR/SOP, WI, BM/HS/KPI-DASH.

Vì vậy, khi dùng Claude Code, bạn nên chạy theo chu trình 4 vai:

Vai 1: BA mode

Claude tạo:

process narrative
actor
exception
acceptance criteria
traceability matrix

Vai 2: Architect mode

Claude chuyển BA thành:

ERD
module boundary
state machine
integration contract
rule engine

Vai 3: Dev mode

Claude sinh:

DocType
script
API
test
migration note

Vai 4: QA/QMS mode

Claude kiểm:

có audit trail chưa
có owner chưa
có evidence chưa
có change control chưa
có drill-down về source record chưa

Đó là cách để Claude Code không chỉ "code xong", mà "code có thể go-live".

---

## Slide 9

### 8. Những nguyên tắc không được vi phạm khi build AssetCore

Không biến AssetCore thành CMMS thuần

WHO 2025 và blueprint đều cho thấy hệ thống phải bao toàn vòng đời, không chỉ maintenance.

Không gộp sai thực thể

Nếu gộp item/model/asset/document/event/work order vào nhau, sau này audit trail và dashboard sẽ hỏng.

Không làm dashboard trước source record

Đây là lỗi cực phổ biến. Hồ sơ đã cảnh báo rõ.

Không để workflow không có evidence

Mỗi bước quan trọng phải có trạng thái, actor, thời điểm, lý do, bằng chứng số.

Không bỏ change control

Đặc biệt IMM-09 có firmware/software update; blueprint nêu rõ phải qua workflow change control riêng, có phê duyệt và record sau hoàn tất.

Không thiết kế tích hợp quá sớm ở mức quá chi tiết

Hồ sơ chốt hướng FHIR cho dữ liệu y tế có cấu trúc và OpenAPI cho API contract, nhưng chi tiết profile/canonical/auth flow chỉ chốt sau khảo sát hệ thống hiện hữu.

---

## Slide 10

### 9. Cách dùng Claude Code theo sprint cho kỹ sư mới

Một sprint tốt với Claude Code có thể như sau:

1

Bước 1

yêu cầu Claude tóm tắt dự án
dựng glossary
liệt kê scope Wave 1
liệt kê open questions

2

Bước 2

tạo ERD logic Wave 1
mapping ERPNext core ↔ custom DocType
chốt decision memo

3

Bước 3

viết spec IMM-04, IMM-05
review bởi BA/QMS mode

4

Bước 4

generate skeleton code IMM-04, IMM-05
generate unit tests cơ bản

5

Bước 5

viết spec IMM-08, IMM-12
review workflow và SLA

6

Bước 6

code IMM-08, IMM-12
review PM checklist, escalation, overdue logic

7

Bước 7

viết spec IMM-09, IMM-11
đặc biệt review spare part traceability + calibration fail flow

Sau mỗi module, hãy tuân theo chu trình 6 bước:

01

Claude viết spec

02

Claude review spec

03

Claude sinh code

04

Claude review code

05

Claude sinh test

06

Claude review test coverage

---

## Slide 11

### 10. Cách yêu cầu Claude review code cho đúng

Đừng hỏi: "Code này ổn không?"

Hãy hỏi đúng cách với vai trò rõ ràng và tiêu chí cụ thể để nhận được phản hồi có giá trị thực sự.

Review code này với vai trò lead architect của AssetCore.
Kiểm tra:
1) có vi phạm boundary giữa ERPNext core và assetcore custom không
2) có thiếu audit trail không
3) có field nào trùng nghĩa với domain model không
4) workflow có khớp IMM-08 không
5) có thiếu validation QMS nào không
6) có rủi ro data lineage nào cho dashboard không
Trả lời theo mức: blocker / major / minor.

🔴 Blocker

Vi phạm nghiêm trọng cần sửa ngay trước khi tiếp tục. Ảnh hưởng đến toàn bộ hệ thống.

🟡 Major

Vấn đề quan trọng cần giải quyết trong sprint hiện tại. Có thể ảnh hưởng đến audit trail hoặc data lineage.

🟢 Minor

Cải tiến nhỏ, có thể xử lý sau. Không ảnh hưởng đến chức năng cốt lõi.

---

## Slide 12

### 11. Bộ tài liệu Claude nên giúp bạn tạo ngay từ đầu

Bạn nên nhờ Claude Code tạo lần lượt các file sau. Nếu thiếu bộ này, dev mới sẽ rất dễ biến Claude Code thành tool "vá bug theo cảm tính".

Tài liệu nền tảng

PROJECT_CONTEXT.md
DOMAIN_GLOSSARY.md
WAVE1_SCOPE.md
WAVE1_ERD.md
ERP_MAPPING.md
STATE_MACHINES.md
WORKFLOW_CATALOG.md

Tài liệu kỹ thuật và vận hành

RULE_ENGINE.md
PERMISSION_MATRIX.md
AUDIT_TRAIL_POLICY.md
QMS_TRACEABILITY_MATRIX.md
API_CONTRACT_GUIDE.md
TEST_STRATEGY.md
SPRINT_BACKLOG_W1.md

---

## Slide 13

### 12. Một lộ trình thực chiến rất gọn cho người mới

Nếu bạn muốn bắt đầu ngay mà không bị quá tải, hãy làm đúng thứ tự này:

Bước 1

Yêu cầu Claude đọc toàn bộ docs và viết bản hiểu dự án.

Bước 2

Chốt ERD và ERP mapping.

Bước 3

Chốt state machine và rule engine.

Bước 4

Viết spec IMM-04.

Bước 5

Code IMM-04.

Bước 6

Test + review.

Bước 7

Lặp lại cho IMM-05, IMM-08, IMM-12.

Bước 8

Sau đó mới sang IMM-09 và IMM-11.

Bước 9

Cuối cùng mới lên dashboard cơ bản.

Đây cũng khớp với logic triển khai đợt 1 trong hồ sơ: khóa định danh, hồ sơ, WO, log và owner trước.

---

## Slide 14

### 13. Kết luận ngắn gọn cho kỹ sư mới

Muốn dùng Claude Code hiệu quả trong dự án này, hãy nhớ 5 điều:

Không yêu cầu Claude build cả hệ thống một lần.

Luôn bắt đầu từ spec và ranh giới domain, chưa bắt đầu từ code.

Khóa quyết định kiến trúc sớm.

Mỗi module phải có workflow, audit trail, evidence, owner.

Dashboard chỉ được làm sau khi source record và data lineage đã đúng.

Với AssetCore, thành công không nằm ở việc Claude viết được bao nhiêu code, mà ở việc bạn dùng Claude để giữ cho hệ thống đúng HTM, đúng QMS, đúng ranh giới ERPNext, và đúng vòng đời thiết bị y tế.

---

