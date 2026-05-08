HỒ SƠ KIẾN TRÚC GIẢI PHÁP PHẦN MỀM

IMMIS  – Hệ thống quản trị TBYT theo vòng đời HTM

(Bản Word-ready nội bộ dùng cho rà soát, chuẩn hóa, trình ký và triển khai)

I. THÔNG TIN PHÊ DUYỆT VÀ KIỂM SOÁT TÀI LIỆU

1. Bảng thông tin phê duyệt

2. Lịch sử phiên bản

3. Danh mục phân phối tài liệu

II. MỤC ĐÍCH, PHẠM VI VÀ CĂN CỨ XÂY DỰNG TÀI LIỆU

1. Mục đích tài liệu

Tài liệu này được xây dựng nhằm mô tả kiến trúc giải pháp tổng thể cho phần mềm IMMIS  – Hệ thống quản trị trang thiết bị y tế, đồng thời đóng gói phụ lục hồ sơ QMS phục vụ rà soát, chuẩn hóa, trình ký, thiết kế chi tiết, phát triển phần mềm, kiểm thử, nghiệm thu, triển khai vận hành và kiểm soát tài liệu.

2. Phạm vi áp dụng

Phạm vi của hồ sơ bao phủ toàn bộ chuỗi quản trị trang thiết bị y tế theo 4 khối kiến trúc đã chốt, gồm Planning & Procurement; Deployment & Implementation; Operations & Maintenance; End-of-Life Management; tương ứng 17 module từ IMM-01 đến IMM-17 và lớp kiểm soát QMS đi kèm.

3. Căn cứ xây dựng

4. Thuật ngữ và chữ viết tắt

III. ĐỊNH VỊ GIẢI PHÁP VÀ MỤC TIÊU KIẾN TRÚC

IMMIS  được xác định là nền tảng số hóa điều hành quản trị trang thiết bị y tế của Phòng VT,TBYT – Bệnh viện Nhi Đồng 1. Hệ thống không được thiết kế như tập hợp các màn hình rời rạc, mà phải được tổ chức như một operating architecture thống nhất, trong đó mọi module, workflow, hồ sơ, dashboard, cảnh báo và quyết định điều hành cùng phục vụ một vòng đời HTM khép kín.

Từ góc độ kiến trúc, hệ thống phải đồng thời đáp ứng bốn lớp logic: logic vòng đời thiết bị theo Fig. 3; logic năng lực quản trị HTM; logic QMS 4 tầng; và logic triển khai số hóa trong môi trường bệnh viện. Vì vậy, mọi quyết định thiết kế trong hồ sơ này đều được neo vào 4 khối kiến trúc và 17 module đã chốt, thay vì xuất phát từ chức năng rời hoặc giao diện rời.

1. Mục tiêu kiến trúc

• Chuẩn hóa một kiến trúc giải pháp phần mềm có khả năng truy vết từ quyết định quản trị xuống bản ghi nguồn và hồ sơ bằng chứng.

• Tổ chức thống nhất các lớp nghiệp vụ, dữ liệu, tích hợp, dashboard và QMS cho toàn bộ vòng đời thiết bị y tế.

• Đóng gói một phụ lục QMS có thể dùng ngay làm backlog soạn thảo tài liệu, thiết lập Master List và triển khai kiểm soát tài liệu điện tử.

• Tạo nền cho phát triển chi tiết ở các lớp BA, UI/UX, backend, data model, dashboard và quản trị thay đổi.

IV. KHUNG KIẾN TRÚC TỔNG THỂ CỦA GIẢI PHÁP

1. Mô hình kiến trúc mức cao

Giải pháp được tổ chức theo mô hình nhiều lớp gồm: lớp người dùng và kênh truy cập; lớp workflow và dịch vụ ứng dụng; lớp xử lý nghiệp vụ; lớp dữ liệu lõi và hồ sơ số; lớp tích hợp; lớp phân tích - dashboard - cảnh báo; và lớp QMS/governance xuyên suốt.

2. Kiến trúc 4 khối – 17 module

V. NGUYÊN TẮC THIẾT KẾ NGHIỆP VỤ, DỮ LIỆU VÀ TÍCH HỢP

1. Nguyên tắc nghiệp vụ

• Mỗi module phải được định nghĩa bởi mục tiêu quản trị, actor chủ trì, điểm vào dữ liệu, đầu ra điều hành và hồ sơ bằng chứng.

• Mọi thao tác nghiệp vụ quan trọng phải sinh ra trạng thái, người chịu trách nhiệm, thời điểm, lý do và bằng chứng số tương ứng.

• Các module không được hoạt động độc lập; dữ liệu, cảnh báo và dashboard phải nối vòng từ Planning đến End-of-Life.

2. Nguyên tắc dữ liệu

• Phải tách rõ item danh mục chuẩn, device model, asset instance, vendor, contract, location, work order, document record, compliance issue và dashboard metric.

• Không dùng một mã để thay cho nhiều thực thể khác cấp; kiến trúc định danh phải hỗ trợ truy nguyên theo vòng đời.

• Dữ liệu hồ sơ, audit trail, CAPA, cảnh báo và dashboard phải truy ngược được về bản ghi nguồn.

3. Nguyên tắc tích hợp

Tại lớp giải pháp, hồ sơ này chốt nguyên tắc rằng dữ liệu y tế có cấu trúc khi liên thông với HIS/EMR/LIS/RIS/PACS/BHYT nên được thiết kế theo hướng tương thích FHIR; còn lớp hợp đồng API giữa các dịch vụ nên được mô tả bằng OpenAPI để bảo đảm phát triển, kiểm thử và bàn giao thống nhất. Những chi tiết như resource profile, canonical model, authorization flow hoặc contract API cụ thể chỉ được chốt ở giai đoạn thiết kế chi tiết sau khi khảo sát hệ thống hiện hữu.

VI. ACTOR MAP VÀ GOVERNANCE TRIỂN KHAI

Actor map của IMMIS phải bám đúng tổ chức vận hành thực tế của BV Nhi Đồng 1. Quyền trên giao diện và trong workflow không dùng role chung chung, mà phải gắn với actor thật, thẩm quyền thật và đường phối hợp thật giữa Khối 1, Khối 2, mạng lưới nội viện, khoa/phòng sử dụng, Kho, Workshop, QLCL và CNTT.

VII. KHUNG QMS ÁP DỤNG CHO GIẢI PHÁP

Tài liệu này áp dụng logic QMS 4 tầng của Phòng VT,TBYT, trong đó L1/QC giữ vai trò chính sách và định hướng; PR/SOP là quy trình điều hành; WI là hướng dẫn thao tác; BM/HS/KPI-DASH là lớp biểu mẫu, hồ sơ và bảng điều khiển. Phụ lục QMS-A đi kèm hồ sơ này là danh mục khởi tạo để thiết lập chuỗi tài liệu theo 4 khối – 17 module.

Ở cấp kiểm soát chất lượng, các điểm khóa phải được giữ xuyên suốt gồm governance và owner dữ liệu; document control; change control; audit trail; data quality; traceability; đào tạo; CAPA; management review; và phân tách rõ record minh chứng theo module. Đây là các yêu cầu bắt buộc trước khi mở go-live và trong suốt giai đoạn vận hành.

• Mọi thay đổi trên master data, mapping, logic cảnh báo, KPI hoặc dashboard phải đi qua change control và đánh giá tác động downstream.

• Audit trail là bắt buộc với các thực thể lõi và các bước duyệt, release, khóa/mở khóa, sửa đổi tiêu chí và trạng thái thiết bị.

• Các dashboard và báo cáo không được công bố khi chưa có quy trình xác minh số liệu nguồn.

VIII. NGUYÊN TẮC DASHBOARD, CẢNH BÁO VÀ PHÂN TÍCH

Toàn bộ 17 module đều được thiết kế để kết thúc ở lớp dashboard hoặc báo cáo quản trị. Tuy nhiên, dashboard không phải lớp hiển thị độc lập mà phải được neo chặt vào workflow, hồ sơ và dữ liệu nguồn. Mỗi dashboard phải có owner, kỳ chốt số liệu, định nghĩa metric, rule cảnh báo, phạm vi drill-down và đường truy nguyên về record gốc.

• Khối Planning & Procurement ưu tiên dashboard về nhu cầu, ưu tiên đầu tư, ngân sách, benchmark kỹ thuật, vendor scorecard.

• Khối Deployment & Implementation ưu tiên dashboard commissioning, release readiness, document compliance, training compliance.

• Khối Operations & Maintenance ưu tiên dashboard hiệu suất, PM, repair, calibration, compliance, spare parts và predictive cockpit.

• Khối End-of-Life ưu tiên dashboard retirement candidate, disposal, reconciliation và closure status.

IX. PHÂN KỲ TRIỂN KHAI ĐỀ XUẤT

X. RỦI RO TRIỂN KHAI VÀ ĐIỂM KHÓA KIỂM SOÁT

• Rủi ro gộp sai thực thể dữ liệu, dùng một mã cho nhiều lớp quản trị hoặc thiết kế asset registry không đủ truy nguyên.

• Rủi ro dashboard đi trước dữ liệu nguồn, không có metric dictionary hoặc không xác minh KPI/KRI trước công bố.

• Rủi ro thiếu owner QMS và thiếu liên kết dọc QC → PR → WI → BM/HS/KPI-DASH, khiến hệ thống vận hành không chứng minh được bằng hồ sơ.

• Rủi ro tích hợp được mô tả quá sớm ở mức kỹ thuật chi tiết khi chưa khảo sát đầy đủ HIS/EMR/LIS/RIS/PACS/ERP/BHYT hiện hữu.

XI. KẾT LUẬN

Hồ sơ này chốt một kiến trúc giải pháp phần mềm IMMIS  theo đúng 4 khối – 17 module đã thống nhất, đồng thời đóng gói phụ lục hồ sơ QMS để làm nền cho thiết kế chi tiết, phát triển, kiểm thử, trình ký và quản trị thay đổi. Giới hạn của hồ sơ nằm ở chỗ tài liệu mới chốt kiến trúc logic, cấu trúc module, actor, dashboard, hồ sơ và quy tắc governance; chưa chốt ở cấp API contract, vật lý cơ sở dữ liệu, mapping field-level, cấu hình hạ tầng và acceptance criteria kỹ thuật chi tiết.

PHỤ LỤC QMS-A. DANH MỤC HỒ SƠ, BIỂU MẪU VÀ DASHBOARD CỦA IMMIS

Phụ lục này được tổ chức theo 4 khối kiến trúc và 17 module. Mỗi module được mô tả dưới dạng nhóm tài liệu độc lập gồm QC/PR/WI/BM/HS/KPI-DASH. Trừ những dòng dashboard, nơi lưu mặc định là QMS điện tử/IMMIS theo thư mục module; controlled copy mặc định là Có.

QMS-A.1. Quy ước mã và nguyên tắc tổ chức phụ lục

• QC-IMMIS-xx: tài liệu nền L1/QC theo từng khối kiến trúc.

• PR-IMMIS-xx-yy: quy trình/SOP cấp module.

• WI-IMMIS-xx-yy: hướng dẫn công việc cấp module.

• BM-IMMIS-xx-yy: biểu mẫu/checklist/kế hoạch chuẩn.

• HS-LOG/HS-REC/HS-REP-IMMIS-xx-yy: nhật ký, hồ sơ ghi nhận, báo cáo và bằng chứng số.

• KPI-DASH-IMMIS-xx: dashboard và cockpit điều hành.

A. KHỐI 1 - PLANNING & PROCUREMENT

IMM-01 – Đánh giá nhu cầu và dự toán

IMM-02 – Thông số kỹ thuật và phân tích thị trường

IMM-03 – Đánh giá nhà cung cấp và quyết định mua sắm

B. KHỐI 2 - DEPLOYMENT & IMPLEMENTATION

IMM-04 – Lắp đặt, định danh và kiểm tra ban đầu

IMM-05 – Đăng ký, cấp phép và hồ sơ

IMM-06 – Đào tạo người dùng

C. KHỐI 3 - OPERATIONS & MAINTENANCE

IMM-07 – Theo dõi hiệu suất

IMM-08 – Bảo trì định kỳ

IMM-09 – Sửa chữa, phụ tùng và cập nhật phần mềm

IMM-10 – Hậu kiểm và tuân thủ

IMM-11 – Hiệu năng và hiệu chuẩn

IMM-12 – Bảo trì khắc phục

IMM-15 – Theo dõi tồn kho phụ tùng

IMM-16 – Theo dõi tuân thủ

IMM-17 – Phân tích dự đoán

D. KHỐI 4 - END-OF-LIFE MANAGEMENT

IMM-13 – Ngừng sử dụng và điều chuyển

IMM-14 – Giải nhiệm thiết bị

QMS-A.2. Ghi chú sử dụng phụ lục

Phụ lục QMS-A là danh mục khởi tạo phục vụ thiết lập Master List, sinh backlog soạn thảo tài liệu, lập kế hoạch kiểm soát tài liệu điện tử và bóc tách package bàn giao cho BA, UI/UX, backend, data và QA. Tình trạng hiệu lực mặc định trong giai đoạn này là dự thảo/quy hoạch; việc chuyển sang trạng thái chính thức phải theo đúng quy trình kiểm soát tài liệu của Phòng VT,TBYT.

| Nội dung | Thông tin |
| --- | --- |
| Tên đơn vị | Bệnh viện Nhi Đồng 1 – Phòng Vật tư, Thiết bị y tế |
| Tên dự án | IMMIS  – Hệ thống quản trị trang thiết bị y tế |
| Tên tài liệu | Hồ sơ kiến trúc giải pháp phần mềm |
| Mã tài liệu | SSD-IMMIS--ARCH-01 (dự thảo) |
| Phiên bản | 0.1 |
| Ngày ban hành | 03/04/2026 |
| Mức độ bảo mật | Nội bộ |
| Trạng thái tài liệu | Dự thảo trình ký |

| Vai trò | Họ và tên | Chức danh | Đơn vị | Ngày | Ký xác nhận |
| --- | --- | --- | --- | --- | --- |
| Người soạn thảo |  |  |  |  |  |
| Người rà soát nghiệp vụ |  |  |  |  |  |
| Người rà soát kỹ thuật |  |  |  |  |  |
| Người phê duyệt |  |  |  |  |  |

| Phiên bản | Ngày cập nhật | Nội dung thay đổi | Người thực hiện | Ghi chú |
| --- | --- | --- | --- | --- |
| 0.1 | 03/04/2026 | Khởi tạo hồ sơ, đóng gói khung 4 khối – 17 module và phụ lục QMS | Nhóm xây dựng tài liệu | Dự thảo |

| STT | Đơn vị/Người nhận | Hình thức | Phiên bản | Mục đích sử dụng |
| --- | --- | --- | --- | --- |
| 1 | Phòng VT,TBYT | File mềm | 0.1 | Rà soát và chuẩn hóa |
| 2 | Lãnh đạo/đầu mối thẩm định | File mềm/Bản in kiểm soát | 0.1 | Thẩm định, trình ký |

| Nguồn | Tên tài liệu/chuẩn | Vai trò sử dụng trong hồ sơ |
| --- | --- | --- |
| BV nội bộ | Mẫu hồ sơ thiết kế giải pháp phần mềm Word-ready | Khung bố cục hồ sơ, thông tin phê duyệt, mục lục và logic đóng gói tài liệu. |
| BV nội bộ | IMMIS  Full Tech Book BV | Khung hợp nhất Fig. 2, Fig. 3, QMS và UI/UX; định vị IMMIS như operating architecture. |
| BV nội bộ | Master List kiểm soát tài liệu QMS toàn phòng VT,TBYT | Quy ước mã QC/PR/WI/BM/HS/KPI-DASH, controlled copy, nơi lưu, trạng thái và liên kết dọc. |
| BV nội bộ | Bảng tổng hợp đảm bảo tuân thủ QMS IMMIS | Khóa các yêu cầu governance, change control, audit trail, CAPA, kiểm thử, data quality và traceability. |
| WHO 2025 | Inventory and maintenance management information system for medical devices | Khung IMMIS và vòng đời quản trị thiết bị y tế từ procurement đến decommissioning. |
| WHO 2025 | Health technology assessment of medical devices, 2nd ed. | Khung HTA cho lựa chọn công nghệ, ra quyết định đầu tư và đánh giá phương án. |
| HL7 | FHIR Overview | Chuẩn định hướng cho trao đổi dữ liệu y tế điện tử ở lớp tích hợp khi liên thông HIS/EMR/LIS/RIS/PACS/BHYT. |
| OpenAPI Initiative | OpenAPI Specification | Chuẩn mô tả hợp đồng API ở lớp tích hợp ứng dụng và cổng dịch vụ. |
| Văn bản pháp lý Việt Nam | Nghị định 98/2021/NĐ-CP và văn bản hướng dẫn, bộ danh pháp BYT, GMDN | Khung tuân thủ pháp lý, danh pháp và định danh thiết bị y tế. |

| Chữ viết tắt | Diễn giải |
| --- | --- |
| HTM | Health Technology Management |
| HTA | Health Technology Assessment |
| CMMS | Computerized Maintenance Management System |
| IMMIS | Inventory and Maintenance Management Information System |
| QMS | Quality Management System |
| CAPA | Corrective and Preventive Action |
| KPI/KRI | Chỉ số hiệu suất/chỉ số rủi ro trọng yếu |
| FHIR | Fast Healthcare Interoperability Resources |
| API | Application Programming Interface |
| WO | Work Order |

| Lớp kiến trúc | Thành phần chính | Yêu cầu bắt buộc |
| --- | --- | --- |
| Lớp người dùng | Portal web nội bộ; dashboard điều hành; giao diện tác nghiệp theo actor | Quyền phải bám actor thật, không dùng role chung chung. |
| Lớp workflow và dịch vụ | Orchestrator quy trình; work order engine; approval engine; alert engine | Mọi trạng thái nghiệp vụ phải có workflow, SLA và audit trail. |
| Lớp nghiệp vụ | 17 module IMM-01 đến IMM-17 theo 4 khối kiến trúc | Không tách module rời logic vòng đời. |
| Lớp dữ liệu | Master data; asset registry; work order; document repository; audit log; data mart | Phải tách đúng item, model, asset, vendor, contract, location, batch, document, event. |
| Lớp tích hợp | HIS/EMR/LIS/RIS/PACS/ERP/BHYT; notification; identity; document services | Khuyến nghị mô tả API theo OpenAPI; dữ liệu y tế có cấu trúc ưu tiên hướng FHIR. |
| Lớp phân tích và điều hành | KPI, KRI, dashboard, cảnh báo, predictive cockpit | Có drill-down về bản ghi nguồn và record minh chứng. |
| Lớp QMS và governance | QC → PR → WI/JD → BM/HS/KPI-DASH; change control; CAPA; audit | Mọi thay đổi dữ liệu, logic, dashboard phải đi qua kiểm soát thay đổi. |

| Khối kiến trúc | Mã module | Tên module | Mục tiêu vận hành |
| --- | --- | --- | --- |
| A. KHỐI 1 | IMM-01 | Đánh giá nhu cầu và dự toán | Chuẩn hóa quy trình tiếp nhận nhu cầu, chấm điểm ưu tiên, lập dự toán, điều chỉnh ngoại lệ và dự báo nhu cầu phục vụ hoạch định đầu tư. |
| A. KHỐI 1 | IMM-02 | Thông số kỹ thuật và phân tích thị trường | Tạo khung xây dựng hồ sơ kỹ thuật, benchmark công nghệ, đánh giá tương thích hạ tầng và kiểm soát nguy cơ khóa hãng/khóa nền tảng. |
| A. KHỐI 1 | IMM-03 | Đánh giá nhà cung cấp và quyết định mua sắm | Chuẩn hóa vendor evaluation, lựa chọn phương án mua sắm, quản lý approved vendor list, hậu kiểm năng lực cung ứng và dashboard vendor scorecard. |
| B. KHỐI 2 | IMM-04 | Lắp đặt, định danh và kiểm tra ban đầu | Khóa chất lượng tiếp nhận, định danh đa lớp, baseline kỹ thuật, initial inspection và release gate trước khi đưa thiết bị vào sử dụng. |
| B. KHỐI 2 | IMM-05 | Đăng ký, cấp phép và hồ sơ | Quản trị document repository theo asset/model, kiểm soát hiệu lực hồ sơ và audit trail tài liệu. |
| B. KHỐI 2 | IMM-06 | Đào tạo người dùng | Bảo đảm người dùng đủ năng lực trước vận hành, có tái đào tạo định kỳ và kiểm soát quyền sử dụng theo trạng thái competency. |
| C. KHỐI 3 | IMM-07 | Theo dõi hiệu suất | Chuẩn hóa KPI/KRI vận hành, theo dõi availability-utilization-downtime, xác minh số liệu và phát hiện replacement signal. |
| C. KHỐI 3 | IMM-08 | Bảo trì định kỳ | Thiết lập vòng lặp PM đầy đủ từ lập lịch, WO, checklist, theo dõi quá hạn, báo cáo compliance đến dashboard điều hành. |
| C. KHỐI 3 | IMM-09 | Sửa chữa, phụ tùng và cập nhật phần mềm | Kiểm soát corrective execution, truy nguyên phụ tùng, change control firmware/software và chi phí sửa chữa. |
| C. KHỐI 3 | IMM-10 | Hậu kiểm và tuân thủ | Quản trị post-market surveillance, recall/FSCA, CAPA, action tracker và compliance dashboard. |
| C. KHỐI 3 | IMM-11 | Hiệu năng và hiệu chuẩn | Quản trị inspection, calibration, kiểm định, certificate hiệu lực và xử lý fail/out-of-tolerance. |
| C. KHỐI 3 | IMM-12 | Bảo trì khắc phục | Thiết lập khung triage sự cố, escalation, RCA, phục hồi vận hành và báo cáo SLA corrective. |
| C. KHỐI 3 | IMM-15 | Theo dõi tồn kho phụ tùng | Kiểm soát tồn kho phụ tùng chiến lược, truy nguyên cấp phát theo WO, kiểm kê và dự báo spare demand. |
| C. KHỐI 3 | IMM-16 | Theo dõi tuân thủ | Thiết lập compliance monitoring, audit, NC/CAPA, scorecard tuân thủ và management review. |
| C. KHỐI 3 | IMM-17 | Phân tích dự đoán | Tạo lớp predictive analytics, model governance, what-if analysis và chuyển insight thành hành động vận hành. |
| D. KHỐI 4 | IMM-13 | Ngừng sử dụng và điều chuyển | Kiểm soát chuyển trạng thái, điều chuyển nội viện, replacement review và residual risk trước khi decommissioning. |
| D. KHỐI 4 | IMM-14 | Giải nhiệm thiết bị | Đóng vòng đời asset, đối soát tài sản - kho - kế toán - hồ sơ và phát hành closure record cuối vòng đời. |

| Actor/đầu mối | Vai trò trong hệ thống | Trục module hiện diện chính |
| --- | --- | --- |
| Trưởng phòng P.VT,TBYT | Điều hành tổng thể, phê duyệt định hướng, KPI/KRI, liên kết chiến lược hai khối. | QC-IMMIS-01 đến QC-IMMIS-04; dashboard điều hành |
| PTP phụ trách Khối 1 | Điều phối kế hoạch, tài chính, SCM, đấu thầu, hợp đồng, kho vận. | IMM-01, IMM-02, IMM-03, IMM-15 |
| PTP phụ trách Khối 2 | Điều phối CMMS, Workshop, tuân thủ kỹ thuật, đổi mới và dashboard. | IMM-04 đến IMM-14, IMM-17 |
| Tổ HC-QLCL & Risk | Giữ nhịp ISO/QMS, rủi ro, audit, CAPA, change control, đào tạo. | IMM-05, IMM-06, IMM-10, IMM-16, IMM-17 |
| Nhóm KH-TC / ĐT-HĐ-NCC | Nhu cầu, dự toán, thông số kỹ thuật, vendor, quyết định mua sắm. | IMM-01, IMM-02, IMM-03 |
| CMMS/IMMIS | Asset registry, workflow, dashboard, log, hồ sơ số, tích hợp và data governance. | Xuyên suốt 17 module |
| Workshop / Nhóm TBYT | Commissioning, PM, CM, inspection, calibration, RCA, phụ tùng. | IMM-04, IMM-08, IMM-09, IMM-11, IMM-12 |
| Kho trung tâm & Kho vận | Phụ tùng, kiểm kê, tồn kho, truy nguyên cấp phát. | IMM-15 |
| Mạng lưới TBYT nội viện | Phản hồi sử dụng, điều chuyển, phối hợp cập nhật hiện trường, hỗ trợ tuân thủ. | IMM-04, IMM-06, IMM-13 |

| Đợt triển khai | Phạm vi module ưu tiên | Đầu ra trọng tâm | Điều kiện chuyển giai đoạn |
| --- | --- | --- | --- |
| Đợt 1 | IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12 | Asset registry; hồ sơ pháp lý-kỹ thuật; PM/CM; inspection/calibration; dashboard vận hành cơ bản. | Đã khóa định danh, hồ sơ, WO, log và owner. |
| Đợt 2 | IMM-01, IMM-02, IMM-03, IMM-06, IMM-15, IMM-16 | Nhu cầu và dự toán; hồ sơ kỹ thuật; vendor management; training; spare parts; compliance scorecard. | Đã có QMS, dashboard nguồn tin cậy và change control. |
| Đợt 3 | IMM-07, IMM-10, IMM-13, IMM-14, IMM-17 | Hiệu suất, hậu kiểm, retirement, decommissioning, predictive cockpit. | Đã có data lineage, đủ chất lượng dữ liệu và cơ chế management review. |

| Mã QC nền | Tên tài liệu nền L1/QC | Chủ sở hữu | Nơi lưu / CC | Chuỗi liên kết dọc |
| --- | --- | --- | --- | --- |
| QC-IMMIS-01 | Chính sách hoạch định, đánh giá nhu cầu, lựa chọn công nghệ và mua sắm TBYT trong IMMIS | Trưởng phòng + Nhóm KH-TC + Nhóm ĐT-HĐ-NCC + Nhóm HTM | QMS điện tử/IMMIS/L1 | Controlled copy: Có | QC-IMMIS-01 → PR-IMMIS-01…; PR-IMMIS-02…; PR-IMMIS-03… |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-01-01, PR-IMMIS-01-02, PR-IMMIS-01-03 | Đánh giá nhu cầu và dự toán | Nhóm KH-TC, Phòng TCKT phối hợp, Nhóm HTM, CMMS/IMMIS | QMS điện tử/IMMIS/01-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-01-01 đến WI-IMMIS-01-05 | Hướng dẫn công việc của Đánh giá nhu cầu và dự toán | Nhóm KH-TC, Phòng TCKT phối hợp, Nhóm HTM, CMMS/IMMIS | QMS điện tử/IMMIS/01-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-01-01 đến BM-IMMIS-01-03 | Biểu mẫu / checklist / kế hoạch chuẩn của Đánh giá nhu cầu và dự toán | Nhóm KH-TC, Phòng TCKT phối hợp, Nhóm HTM, CMMS/IMMIS | QMS điện tử/IMMIS/01-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-01-01; HS-REC-IMMIS-01-01, HS-REC-IMMIS-01-02; HS-REP-IMMIS-01-01, HS-REP-IMMIS-01-02, HS-REP-IMMIS-01-03 | Nhật ký, hồ sơ và báo cáo bằng chứng của Đánh giá nhu cầu và dự toán | Nhóm KH-TC, Phòng TCKT phối hợp, Nhóm HTM, CMMS/IMMIS | QMS điện tử/IMMIS/01-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-01 | Dashboard/cockpit của Đánh giá nhu cầu và dự toán | Nhóm KH-TC, Phòng TCKT phối hợp, Nhóm HTM, CMMS/IMMIS | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-02-01, PR-IMMIS-02-02, PR-IMMIS-02-03, PR-IMMIS-02-04 | Thông số kỹ thuật và phân tích thị trường | Nhóm HTM, Nhóm ĐT-HĐ-NCC, CMMS/IMMIS, CNTT, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/02-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-02-01 đến WI-IMMIS-02-05 | Hướng dẫn công việc của Thông số kỹ thuật và phân tích thị trường | Nhóm HTM, Nhóm ĐT-HĐ-NCC, CMMS/IMMIS, CNTT, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/02-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-02-01, BM-IMMIS-02-02 | Biểu mẫu / checklist / kế hoạch chuẩn của Thông số kỹ thuật và phân tích thị trường | Nhóm HTM, Nhóm ĐT-HĐ-NCC, CMMS/IMMIS, CNTT, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/02-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-02-01; HS-REC-IMMIS-02-01; HS-REP-IMMIS-02-01, HS-REP-IMMIS-02-02 | Nhật ký, hồ sơ và báo cáo bằng chứng của Thông số kỹ thuật và phân tích thị trường | Nhóm HTM, Nhóm ĐT-HĐ-NCC, CMMS/IMMIS, CNTT, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/02-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-02 | Dashboard/cockpit của Thông số kỹ thuật và phân tích thị trường | Nhóm HTM, Nhóm ĐT-HĐ-NCC, CMMS/IMMIS, CNTT, Tổ HC-QLCL & Risk | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-03-01, PR-IMMIS-03-02, PR-IMMIS-03-03, PR-IMMIS-03-04 | Đánh giá nhà cung cấp và quyết định mua sắm | Nhóm ĐT-HĐ-NCC, Nhóm KH-TC, Nhóm HTM | QMS điện tử/IMMIS/03-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-03-01 đến WI-IMMIS-03-05 | Hướng dẫn công việc của Đánh giá nhà cung cấp và quyết định mua sắm | Nhóm ĐT-HĐ-NCC, Nhóm KH-TC, Nhóm HTM | QMS điện tử/IMMIS/03-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-03-01, BM-IMMIS-03-02 | Biểu mẫu / checklist / kế hoạch chuẩn của Đánh giá nhà cung cấp và quyết định mua sắm | Nhóm ĐT-HĐ-NCC, Nhóm KH-TC, Nhóm HTM | QMS điện tử/IMMIS/03-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-03-01; HS-REC-IMMIS-03-01; HS-REP-IMMIS-03-01, HS-REP-IMMIS-03-02 | Nhật ký, hồ sơ và báo cáo bằng chứng của Đánh giá nhà cung cấp và quyết định mua sắm | Nhóm ĐT-HĐ-NCC, Nhóm KH-TC, Nhóm HTM | QMS điện tử/IMMIS/03-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-03 | Dashboard/cockpit của Đánh giá nhà cung cấp và quyết định mua sắm | Nhóm ĐT-HĐ-NCC, Nhóm KH-TC, Nhóm HTM | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Mã QC nền | Tên tài liệu nền L1/QC | Chủ sở hữu | Nơi lưu / CC | Chuỗi liên kết dọc |
| --- | --- | --- | --- | --- |
| QC-IMMIS-02 | Chính sách triển khai, định danh, hồ sơ và đào tạo trước vận hành trong IMMIS | Trưởng phòng + Nhóm HTM + CMMS/IMMIS + Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/L1 | Controlled copy: Có | QC-IMMIS-02 → PR-IMMIS-04…; PR-IMMIS-05…; PR-IMMIS-06… |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-04-01 đến PR-IMMIS-04-04 | Lắp đặt, định danh và kiểm tra ban đầu | Nhóm HTM, CMMS/IMMIS, Workshop | QMS điện tử/IMMIS/04-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-04-01 đến WI-IMMIS-04-05 | Hướng dẫn công việc của Lắp đặt, định danh và kiểm tra ban đầu | Nhóm HTM, CMMS/IMMIS, Workshop | QMS điện tử/IMMIS/04-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-04-01 đến BM-IMMIS-04-03 | Biểu mẫu / checklist / kế hoạch chuẩn của Lắp đặt, định danh và kiểm tra ban đầu | Nhóm HTM, CMMS/IMMIS, Workshop | QMS điện tử/IMMIS/04-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-04-01; HS-REC-IMMIS-04-01, HS-REC-IMMIS-04-02; HS-REP-IMMIS-04-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Lắp đặt, định danh và kiểm tra ban đầu | Nhóm HTM, CMMS/IMMIS, Workshop | QMS điện tử/IMMIS/04-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-04 | Dashboard/cockpit của Lắp đặt, định danh và kiểm tra ban đầu | Nhóm HTM, CMMS/IMMIS, Workshop | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-05-01, PR-IMMIS-05-02, PR-IMMIS-05-03 | Đăng ký, cấp phép và hồ sơ | CMMS/IMMIS, Tổ HC-QLCL & Risk, Nhóm HTM | QMS điện tử/IMMIS/05-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-05-01 đến WI-IMMIS-05-04 | Hướng dẫn công việc của Đăng ký, cấp phép và hồ sơ | CMMS/IMMIS, Tổ HC-QLCL & Risk, Nhóm HTM | QMS điện tử/IMMIS/05-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-05-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Đăng ký, cấp phép và hồ sơ | CMMS/IMMIS, Tổ HC-QLCL & Risk, Nhóm HTM | QMS điện tử/IMMIS/05-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-05-01; HS-REC-IMMIS-05-01; HS-REP-IMMIS-05-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Đăng ký, cấp phép và hồ sơ | CMMS/IMMIS, Tổ HC-QLCL & Risk, Nhóm HTM | QMS điện tử/IMMIS/05-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-05 | Dashboard/cockpit của Đăng ký, cấp phép và hồ sơ | CMMS/IMMIS, Tổ HC-QLCL & Risk, Nhóm HTM | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-06-01, PR-IMMIS-06-02, PR-IMMIS-06-03 | Đào tạo người dùng | Tổ HC-QLCL & Risk, Nhóm HTM, CoE/Học viện KTYT, CMMS/IMMIS, CNTT | QMS điện tử/IMMIS/06-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-06-01 đến WI-IMMIS-06-04 | Hướng dẫn công việc của Đào tạo người dùng | Tổ HC-QLCL & Risk, Nhóm HTM, CoE/Học viện KTYT, CMMS/IMMIS, CNTT | QMS điện tử/IMMIS/06-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-06-01, BM-IMMIS-06-02 | Biểu mẫu / checklist / kế hoạch chuẩn của Đào tạo người dùng | Tổ HC-QLCL & Risk, Nhóm HTM, CoE/Học viện KTYT, CMMS/IMMIS, CNTT | QMS điện tử/IMMIS/06-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-06-01; HS-REC-IMMIS-06-01, HS-REC-IMMIS-06-02; HS-REP-IMMIS-06-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Đào tạo người dùng | Tổ HC-QLCL & Risk, Nhóm HTM, CoE/Học viện KTYT, CMMS/IMMIS, CNTT | QMS điện tử/IMMIS/06-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-06 | Dashboard/cockpit của Đào tạo người dùng | Tổ HC-QLCL & Risk, Nhóm HTM, CoE/Học viện KTYT, CMMS/IMMIS, CNTT | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Mã QC nền | Tên tài liệu nền L1/QC | Chủ sở hữu | Nơi lưu / CC | Chuỗi liên kết dọc |
| --- | --- | --- | --- | --- |
| QC-IMMIS-03 | Chính sách vận hành, bảo trì, tuân thủ, dữ liệu và quyết định điều hành trong IMMIS | Trưởng phòng + Workshop + CMMS/IMMIS + Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/L1 | Controlled copy: Có | QC-IMMIS-03 → PR-IMMIS-07…; PR-IMMIS-08…; PR-IMMIS-09…; PR-IMMIS-10…; PR-IMMIS-11…; PR-IMMIS-12…; PR-IMMIS-15…; PR-IMMIS-16…; PR-IMMIS-17… |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-07-01, PR-IMMIS-07-02, PR-IMMIS-07-03 | Theo dõi hiệu suất | CMMS/IMMIS, Nhóm HTM, CNTT, Workshop | QMS điện tử/IMMIS/07-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-07-01 đến WI-IMMIS-07-04 | Hướng dẫn công việc của Theo dõi hiệu suất | CMMS/IMMIS, Nhóm HTM, CNTT, Workshop | QMS điện tử/IMMIS/07-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-07-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Theo dõi hiệu suất | CMMS/IMMIS, Nhóm HTM, CNTT, Workshop | QMS điện tử/IMMIS/07-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-07-01; HS-REC-IMMIS-07-01; HS-REP-IMMIS-07-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Theo dõi hiệu suất | CMMS/IMMIS, Nhóm HTM, CNTT, Workshop | QMS điện tử/IMMIS/07-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-07 | Dashboard/cockpit của Theo dõi hiệu suất | CMMS/IMMIS, Nhóm HTM, CNTT, Workshop | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-08-01, PR-IMMIS-08-02, PR-IMMIS-08-03 | Bảo trì định kỳ | Workshop, CMMS/IMMIS, Nhóm HTM, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/08-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-08-01 đến WI-IMMIS-08-04 | Hướng dẫn công việc của Bảo trì định kỳ | Workshop, CMMS/IMMIS, Nhóm HTM, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/08-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-08-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Bảo trì định kỳ | Workshop, CMMS/IMMIS, Nhóm HTM, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/08-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-08-01; HS-REC-IMMIS-08-01; HS-REP-IMMIS-08-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Bảo trì định kỳ | Workshop, CMMS/IMMIS, Nhóm HTM, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/08-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-08 | Dashboard/cockpit của Bảo trì định kỳ | Workshop, CMMS/IMMIS, Nhóm HTM, Tổ HC-QLCL & Risk | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-09-01, PR-IMMIS-09-02, PR-IMMIS-09-03 | Sửa chữa, phụ tùng và cập nhật phần mềm | Workshop, Nhóm Kho, CMMS/IMMIS, CNTT | QMS điện tử/IMMIS/09-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-09-01 đến WI-IMMIS-09-04 | Hướng dẫn công việc của Sửa chữa, phụ tùng và cập nhật phần mềm | Workshop, Nhóm Kho, CMMS/IMMIS, CNTT | QMS điện tử/IMMIS/09-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-09-01, BM-IMMIS-09-02 | Biểu mẫu / checklist / kế hoạch chuẩn của Sửa chữa, phụ tùng và cập nhật phần mềm | Workshop, Nhóm Kho, CMMS/IMMIS, CNTT | QMS điện tử/IMMIS/09-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-09-01; HS-REC-IMMIS-09-01, HS-REC-IMMIS-09-02; HS-REP-IMMIS-09-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Sửa chữa, phụ tùng và cập nhật phần mềm | Workshop, Nhóm Kho, CMMS/IMMIS, CNTT | QMS điện tử/IMMIS/09-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-09 | Dashboard/cockpit của Sửa chữa, phụ tùng và cập nhật phần mềm | Workshop, Nhóm Kho, CMMS/IMMIS, CNTT | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-10-01, PR-IMMIS-10-02, PR-IMMIS-10-03 | Hậu kiểm và tuân thủ | Tổ HC-QLCL & Risk, Nhóm HTM, Tổ HC-Tổng hợp, CMMS/IMMIS | QMS điện tử/IMMIS/10-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-10-01 đến WI-IMMIS-10-04 | Hướng dẫn công việc của Hậu kiểm và tuân thủ | Tổ HC-QLCL & Risk, Nhóm HTM, Tổ HC-Tổng hợp, CMMS/IMMIS | QMS điện tử/IMMIS/10-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-10-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Hậu kiểm và tuân thủ | Tổ HC-QLCL & Risk, Nhóm HTM, Tổ HC-Tổng hợp, CMMS/IMMIS | QMS điện tử/IMMIS/10-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-10-01; HS-REC-IMMIS-10-01, HS-REC-IMMIS-10-02; HS-REP-IMMIS-10-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Hậu kiểm và tuân thủ | Tổ HC-QLCL & Risk, Nhóm HTM, Tổ HC-Tổng hợp, CMMS/IMMIS | QMS điện tử/IMMIS/10-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-10 | Dashboard/cockpit của Hậu kiểm và tuân thủ | Tổ HC-QLCL & Risk, Nhóm HTM, Tổ HC-Tổng hợp, CMMS/IMMIS | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-11-01, PR-IMMIS-11-02, PR-IMMIS-11-03 | Hiệu năng và hiệu chuẩn | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/11-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-11-01 đến WI-IMMIS-11-04 | Hướng dẫn công việc của Hiệu năng và hiệu chuẩn | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/11-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-11-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Hiệu năng và hiệu chuẩn | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/11-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-11-01; HS-REC-IMMIS-11-01, HS-REC-IMMIS-11-02; HS-REP-IMMIS-11-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Hiệu năng và hiệu chuẩn | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/11-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-11 | Dashboard/cockpit của Hiệu năng và hiệu chuẩn | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-12-01, PR-IMMIS-12-02, PR-IMMIS-12-03 | Bảo trì khắc phục | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk, QLCL | QMS điện tử/IMMIS/12-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-12-01 đến WI-IMMIS-12-04 | Hướng dẫn công việc của Bảo trì khắc phục | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk, QLCL | QMS điện tử/IMMIS/12-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-12-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Bảo trì khắc phục | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk, QLCL | QMS điện tử/IMMIS/12-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-12-01; HS-REC-IMMIS-12-01, HS-REC-IMMIS-12-02; HS-REP-IMMIS-12-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Bảo trì khắc phục | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk, QLCL | QMS điện tử/IMMIS/12-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-12 | Dashboard/cockpit của Bảo trì khắc phục | Workshop, CMMS/IMMIS, Tổ HC-QLCL & Risk, QLCL | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-15-01, PR-IMMIS-15-02, PR-IMMIS-15-03, PR-IMMIS-15-04 | Theo dõi tồn kho phụ tùng | Nhóm Kho, Workshop, KH-TC, CMMS/IMMIS, QLCL | QMS điện tử/IMMIS/15-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-15-01 đến WI-IMMIS-15-05 | Hướng dẫn công việc của Theo dõi tồn kho phụ tùng | Nhóm Kho, Workshop, KH-TC, CMMS/IMMIS, QLCL | QMS điện tử/IMMIS/15-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-15-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Theo dõi tồn kho phụ tùng | Nhóm Kho, Workshop, KH-TC, CMMS/IMMIS, QLCL | QMS điện tử/IMMIS/15-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-15-01; HS-REC-IMMIS-15-01, HS-REC-IMMIS-15-02; HS-REP-IMMIS-15-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Theo dõi tồn kho phụ tùng | Nhóm Kho, Workshop, KH-TC, CMMS/IMMIS, QLCL | QMS điện tử/IMMIS/15-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-15 | Dashboard/cockpit của Theo dõi tồn kho phụ tùng | Nhóm Kho, Workshop, KH-TC, CMMS/IMMIS, QLCL | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-16-01, PR-IMMIS-16-02, PR-IMMIS-16-03, PR-IMMIS-16-04 | Theo dõi tuân thủ | Tổ HC-QLCL & Risk, CMMS/IMMIS, PTP1/PTP2 | QMS điện tử/IMMIS/16-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-16-01 đến WI-IMMIS-16-05 | Hướng dẫn công việc của Theo dõi tuân thủ | Tổ HC-QLCL & Risk, CMMS/IMMIS, PTP1/PTP2 | QMS điện tử/IMMIS/16-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-16-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Theo dõi tuân thủ | Tổ HC-QLCL & Risk, CMMS/IMMIS, PTP1/PTP2 | QMS điện tử/IMMIS/16-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-16-01; HS-REC-IMMIS-16-01, HS-REC-IMMIS-16-02; HS-REP-IMMIS-16-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Theo dõi tuân thủ | Tổ HC-QLCL & Risk, CMMS/IMMIS, PTP1/PTP2 | QMS điện tử/IMMIS/16-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-16 | Dashboard/cockpit của Theo dõi tuân thủ | Tổ HC-QLCL & Risk, CMMS/IMMIS, PTP1/PTP2 | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-17-01, PR-IMMIS-17-02, PR-IMMIS-17-03, PR-IMMIS-17-04 | Phân tích dự đoán | CMMS/IMMIS, Trung tâm Đổi mới sáng tạo, Tổ HC-QLCL & Risk, Nhóm HTM, Nhóm Kho, KH-TC, Workshop | QMS điện tử/IMMIS/17-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-17-01 đến WI-IMMIS-17-05 | Hướng dẫn công việc của Phân tích dự đoán | CMMS/IMMIS, Trung tâm Đổi mới sáng tạo, Tổ HC-QLCL & Risk, Nhóm HTM, Nhóm Kho, KH-TC, Workshop | QMS điện tử/IMMIS/17-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-17-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Phân tích dự đoán | CMMS/IMMIS, Trung tâm Đổi mới sáng tạo, Tổ HC-QLCL & Risk, Nhóm HTM, Nhóm Kho, KH-TC, Workshop | QMS điện tử/IMMIS/17-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-17-01; HS-REC-IMMIS-17-01; HS-REP-IMMIS-17-01, HS-REP-IMMIS-17-02 | Nhật ký, hồ sơ và báo cáo bằng chứng của Phân tích dự đoán | CMMS/IMMIS, Trung tâm Đổi mới sáng tạo, Tổ HC-QLCL & Risk, Nhóm HTM, Nhóm Kho, KH-TC, Workshop | QMS điện tử/IMMIS/17-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-17 | Dashboard/cockpit của Phân tích dự đoán | CMMS/IMMIS, Trung tâm Đổi mới sáng tạo, Tổ HC-QLCL & Risk, Nhóm HTM, Nhóm Kho, KH-TC, Workshop | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Mã QC nền | Tên tài liệu nền L1/QC | Chủ sở hữu | Nơi lưu / CC | Chuỗi liên kết dọc |
| --- | --- | --- | --- | --- |
| QC-IMMIS-04 | Chính sách ngừng sử dụng, điều chuyển, giải nhiệm và đóng vòng đời asset trong IMMIS | Trưởng phòng + Nhóm HTM + Nhóm KH-TC + Tổ HC-QLCL & Risk | QMS điện tử/IMMIS/L1 | Controlled copy: Có | QC-IMMIS-04 → PR-IMMIS-13…; PR-IMMIS-14… |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-13-01, PR-IMMIS-13-02, PR-IMMIS-13-03 | Ngừng sử dụng và điều chuyển | Nhóm HTM, Mạng lưới nội viện, KH-TC, QLCL, CMMS/IMMIS | QMS điện tử/IMMIS/13-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-13-01 đến WI-IMMIS-13-04 | Hướng dẫn công việc của Ngừng sử dụng và điều chuyển | Nhóm HTM, Mạng lưới nội viện, KH-TC, QLCL, CMMS/IMMIS | QMS điện tử/IMMIS/13-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-13-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Ngừng sử dụng và điều chuyển | Nhóm HTM, Mạng lưới nội viện, KH-TC, QLCL, CMMS/IMMIS | QMS điện tử/IMMIS/13-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-13-01; HS-REC-IMMIS-13-01, HS-REC-IMMIS-13-02; HS-REP-IMMIS-13-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Ngừng sử dụng và điều chuyển | Nhóm HTM, Mạng lưới nội viện, KH-TC, QLCL, CMMS/IMMIS | QMS điện tử/IMMIS/13-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-13 | Dashboard/cockpit của Ngừng sử dụng và điều chuyển | Nhóm HTM, Mạng lưới nội viện, KH-TC, QLCL, CMMS/IMMIS | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

| Nhóm tài liệu | Mã/nhóm mã | Tên tài liệu / phạm vi | Chủ sở hữu chính | Nơi lưu / CC | Ghi chú vận hành |
| --- | --- | --- | --- | --- | --- |
| PR/SOP | PR-IMMIS-14-01, PR-IMMIS-14-02, PR-IMMIS-14-03 | Giải nhiệm thiết bị | Nhóm HTM, KH-TC, Nhóm Kho, CMMS/IMMIS, CNTT, QLCL | QMS điện tử/IMMIS/14-*; BI/IMMIS | CC: Có | Quy trình điều hành chính của module. |
| WI | WI-IMMIS-14-01 đến WI-IMMIS-14-04 | Hướng dẫn công việc của Giải nhiệm thiết bị | Nhóm HTM, KH-TC, Nhóm Kho, CMMS/IMMIS, CNTT, QLCL | QMS điện tử/IMMIS/14-*; BI/IMMIS | CC: Có | Chuẩn hóa thao tác, tiêu chí và xử lý ngoại lệ. |
| BM | BM-IMMIS-14-01 | Biểu mẫu / checklist / kế hoạch chuẩn của Giải nhiệm thiết bị | Nhóm HTM, KH-TC, Nhóm Kho, CMMS/IMMIS, CNTT, QLCL | QMS điện tử/IMMIS/14-*; BI/IMMIS | CC: Có | Điểm capture dữ liệu và hồ sơ đầu vào. |
| HS | HS-LOG-IMMIS-14-01; HS-REC-IMMIS-14-01, HS-REC-IMMIS-14-02; HS-REP-IMMIS-14-01 | Nhật ký, hồ sơ và báo cáo bằng chứng của Giải nhiệm thiết bị | Nhóm HTM, KH-TC, Nhóm Kho, CMMS/IMMIS, CNTT, QLCL | QMS điện tử/IMMIS/14-*; BI/IMMIS | CC: Có | Audit trail, record minh chứng và báo cáo quản trị. |
| KPI-DASH | KPI-DASH-IMMIS-14 | Dashboard/cockpit của Giải nhiệm thiết bị | Nhóm HTM, KH-TC, Nhóm Kho, CMMS/IMMIS, CNTT, QLCL | BI/IMMIS | CC: Có | Lớp điều hành và phân tích theo kỳ chốt số liệu. |

