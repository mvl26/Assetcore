 
 
 
 
 
 AssetCore – BA Analysis Wave 1 

 
 

 
 
   AssetCore · BA Analysis · Wave 1 
    Business Analysis  — Wave 1 Module Decomposition 
   
    Phân tích nghiệp vụ chi tiết 6 module ưu tiên Đợt 1: Process map, Actor/Role, Input/Output,
    User Story (INVEST), Acceptance Criteria (Gherkin), Business Rules, Exception Handling,
    WHO Mapping và QMS Control.
   
   
     IMM-04 · Lắp đặt & Định danh 
     IMM-05 · Đăng ký & Hồ sơ 
     IMM-08 · Bảo trì định kỳ 
     IMM-09 · Sửa chữa & Phụ tùng 
     IMM-11 · Hiệu chuẩn & Kiểm định 
     IMM-12 · Bảo trì khắc phục 
   
 

 
 
   IMM-04 
   IMM-05 
   IMM-08 
   IMM-09 
   IMM-11 
   IMM-12 
 

 

 
 
   
     
       IMM-04 
     
     
       Lắp đặt, Định danh và Kiểm tra ban đầu 
       Khóa chất lượng tiếp nhận · Baseline kỹ thuật · Release gate trước khi đưa vào sử dụng 
     
   

   
   
     1 · Process Map (BPMN Style) 
     
       
         START 
         Nhận thiết bị từ kho / NCC 
         Kho vận · HTM 
       
       → 
       
         1 
         Kiểm tra hồ sơ giao hàng & đối chiếu PO 
         HTM / Kho 
       
       → 
       
         GW-1 
         Hồ sơ đầy đủ? 
         KT. HTM 
       
       → 
       
         2 
         Định danh đa lớp (mã TBYT, S/N, QR/barcode) 
         KT. HTM 
       
       → 
       
         3 
         Chuẩn bị mặt bằng & điều kiện lắp đặt 
         Khoa phòng · Workshop 
       
       → 
       
         4 
         Lắp đặt & kết nối (điện, mạng, khí, nước) 
         Workshop / NCC 
       
       → 
       
         5 
         Kiểm tra ban đầu — Initial Inspection checklist 
         KT. HTM 
       
       → 
       
         GW-2 
         Passed all checks? 
         KT. HTM 
       
       → 
       
         6 
         Gắn nhãn trạng thái "Passed" + QR 
         KT. HTM 
       
       → 
       
         END 
         Asset status → "In Service" / "Ready" 
         CMMS · IMMIS 
       
     
     
       
         ⚠ 
          Exception path:  GW-1 fail → Lập phiếu NC (non-conformance), giữ thiết bị cách ly, thông báo NCC. GW-2 fail → Mở CM Work Order hoặc trả hàng. 
       
     
   

   
   
     2 · Actor & Role 
     
        Actor  Vai trò  Quyền hệ thống  Trách nhiệm chính  
        Kỹ thuật viên HTM  Người thực hiện chính  Create/Edit Asset, Initial Inspection  Định danh, lắp đặt, điền checklist, ký biên bản  
        Trưởng Workshop / KT trưởng  Phê duyệt kỹ thuật  Approve Inspection, Release Asset  Xem xét kết quả inspection, quyết định release  
        PTP phụ trách Khối 2  Giám sát & escalation  View All, Approve NC  Phê duyệt ngoại lệ, xử lý NC nghiêm trọng  
        Kho vận  Bàn giao vật lý  View Asset, Delivery Confirm  Ký biên bản giao nhận, cập nhật vị trí kho  
        Khoa phòng sử dụng  Tiếp nhận vận hành  View Asset, Accept Transfer  Xác nhận điều kiện lắp đặt, ký biên bản bàn giao  
        QLCL / Tổ HC-QLCL  Kiểm soát chất lượng  Audit View, NC Review  Theo dõi NC, cập nhật compliance record  
     
   

   
   
     3 · Input / Output 
     
       
         INPUT 
         
            Tài liệu / Dữ liệu đầu vào  Nguồn  
            Phiếu giao hàng / Packing list  NCC / Kho  
            Hợp đồng / PO (reference)  IMM-03  
            Thông số kỹ thuật (spec sheet)  IMM-02 / NCC  
            Checklist lắp đặt của nhà sản xuất  IFU / Service manual  
            Điều kiện mặt bằng (site readiness report)  Khoa phòng / Kỹ thuật hạ tầng  
            Danh mục thiết bị cần nhận (Asset category)  Asset Category master  
         
       
       
         OUTPUT 
         
            Đầu ra / Chứng từ  DocType (ERPNext)  
            Asset record (mã định danh duy nhất)   Asset   
            Biên bản lắp đặt & kiểm tra ban đầu   Asset Commissioning  (custom)  
            Initial Inspection checklist đã ký   Asset Commissioning → Child Table   
            Nhãn QR / barcode gắn thiết bị  Print Format từ Asset  
            Phiếu NC (nếu fail)   Quality Inspection  / NC Log  
            Biên bản bàn giao khoa phòng   Asset Movement   
            Trạng thái asset: In Service / Hold   Asset.status   
         
       
     
   

   
   
     4 · User Stories (INVEST) 
     
       🔵  US-04-01:  Với tư cách là  Kỹ thuật viên HTM , tôi muốn  nhập thông tin định danh thiết bị (S/N, model, nhà sản xuất, năm SX) ngay khi nhận hàng  để  mọi thiết bị có mã duy nhất trong CMMS trước khi lắp đặt . 
       ✅ Independent · Negotiable · Valuable · Estimable · Small · Testable | SP: 5 
     
     
       🔵  US-04-02:  Với tư cách là  Kỹ thuật viên HTM , tôi muốn  điền checklist kiểm tra ban đầu trực tiếp trên tablet/điện thoại  để  loại bỏ giấy tờ thủ công và có bằng chứng số thời gian thực . 
       ✅ Independent · Negotiable · Valuable · Estimable · Small · Testable | SP: 8 
     
     
       🔵  US-04-03:  Với tư cách là  Trưởng Workshop , tôi muốn  xem danh sách thiết bị đang chờ release gate và phê duyệt/từ chối từ một màn hình  để  kiểm soát chất lượng trước khi thiết bị vào vận hành . 
       ✅ Independent · Valuable · Estimable · Small · Testable | SP: 5 
     
     
       🔵  US-04-04:  Với tư cách là  PTP Khối 2 , tôi muốn  xem dashboard tỷ lệ thiết bị hoàn thành commissioning đúng hạn  để  theo dõi tiến độ triển khai theo kế hoạch đầu tư . 
       ✅ Valuable · Estimable · Testable | SP: 3 
     
   

   
   
     5 · Acceptance Criteria (Gherkin) 
      Scenario: Tạo Asset và hoàn thành Initial Inspection thành công 
 Given  KTV đã nhận thiết bị có đủ hồ sơ giao hàng
 When  KTV tạo record trong  Asset Commissioning  và điền đủ S/N, model, manufacturer, category
 And  KTV hoàn thành tất cả mục trong checklist với kết quả "Pass"
 And  Trưởng Workshop bấm "Approve Release"
 Then  Asset.status = "Active / In Service"
 And  Asset.asset_number được gán theo Naming Series  TBYT-YYYY-##### 
 And  Biên bản commissioning được lock (không thể edit)
 And  Hệ thống tự động tạo lịch PM đầu tiên theo asset category 

      Scenario: Phát hiện lỗi khi kiểm tra ban đầu 
 Given  KTV đang điền checklist Initial Inspection
 When  KTV đánh dấu bất kỳ mục nào là "Fail"
 Then  Hệ thống bắt buộc KTV nhập mô tả lỗi và ảnh đính kèm
 And  Asset.status = "Hold – Pending Inspection"
 And  Hệ thống tạo NC record và gửi alert đến Trưởng Workshop
 But  Nút "Approve Release" bị disable cho đến khi NC được đóng 
   

   
   
     6 · Business Rules 
     
        Mã rule  Nội dung  Hệ quả vi phạm  Kiểm soát trong ERPNext  
         BR-04-01   Mỗi thiết bị PHẢI có mã định danh duy nhất trước khi lắp đặt  Không cho phép tạo Commissioning record nếu chưa có Asset code  Mandatory field + Naming Series  
         BR-04-02   Checklist PHẢI hoàn thành 100% trước khi release  Block nút Submit nếu còn mục chưa điền  Validation script trên Child Table  
         BR-04-03   Asset KHÔNG được chuyển trạng thái "Active" nếu có NC chưa đóng  Workflow transition bị block  Workflow condition  
         BR-04-04   Tất cả thay đổi về S/N, model sau khi Submit phải có lý do và người duyệt  Audit trail bắt buộc  Amend + Custom log  
         BR-04-05   Thiết bị nguy cơ cao (class III) phải có ảnh chụp thực tế gắn kèm commissioning  Submit bị block nếu thiếu attachment  File attachment mandatory check by category  
     
   

   
   
     7 · Exception Handling 
     
        Tình huống ngoại lệ  Điều kiện kích hoạt  Xử lý hệ thống  Xử lý nghiệp vụ  
        Hồ sơ giao hàng không đủ  Thiếu packing list hoặc không khớp PO  Create NC record, đặt asset = "Quarantine"  Liên hệ NCC trong 24h, leo thang PTP nếu >48h  
        Thiết bị bị hư hỏng khi vận chuyển  KTV ghi nhận hư hỏng vật lý khi mở kiện  Tạo incident report, chụp ảnh, block release  Lập biên bản với NCC/bảo hiểm, trả hàng hoặc yêu cầu thay thế  
        NCC cần hỗ trợ lắp đặt nhưng chưa đến  Commissioning deadline gần nhưng NCC vắng  Cảnh báo deadline, alert tự động  Leo thang phòng vật tư – hợp đồng NCC  
        Thiết bị không đạt tiêu chí kỹ thuật sau lắp đặt  Performance check fail nhưng không phải hư hỏng  Status = "Hold", mở CM Work Order  KTV + NCC debug, re-inspection sau sửa  
        Site chưa sẵn sàng (điện, hạ tầng)  Pre-installation checklist fail  Block commissioning step 4, tạo site readiness task  Phối hợp khoa phòng + kỹ thuật hạ tầng BV  
     
   

   
   
     8 · Mapping WHO Guideline 
     
        Yêu cầu AssetCore  WHO Reference  Nội dung WHO  
        Site preparation trước lắp đặt  WHO HTM 2025, §3.2.2  "Ensuring location meets requirements for power, ventilation, water before device arrives"  
        Initial inspection + commissioning  WHO HTM 2025, §3.2.3  "Formal testing and validation that device works as intended before routine clinical use"  
        Định danh: ghi nhận manufacturer, model, S/N, year  WHO HTM 2025, §3.2.3  "Device carefully identified and recorded – ensures traceability and proper documentation"  
        Performance & safety checks theo manufacturer guidelines  WHO HTM 2025, §3.2.3 + ISO/IEC 17020  "Biomedical engineers conduct checks according to international standards or manufacturer guidelines"  
        Release gate trước khi vào clinical use  WHO Procurement §6.6  "Commissioning = series of tests and adjustments to check equipment is functioning correctly and safely"  
     
   

   
   
     9 · QMS Control Mapping 
     
        QMS Element  ISO 9001:2015 Clause  Điểm kiểm soát trong IMM-04  Hồ sơ bằng chứng  
        Kiểm soát sản phẩm/dịch vụ được cung cấp từ bên ngoài  §8.4  Đối chiếu PO vs packing list, NC khi không khớp  Biên bản giao nhận, NC record  
        Kiểm soát đầu ra không phù hợp  §8.7  Status "Hold" khi inspection fail, block release  NC Log, Hold tag (physical + digital)  
        Xác định & truy nguyên  §8.5.2  Naming series, QR code, link Asset ↔ hồ sơ  Asset record với đầy đủ metadata  
        Kiểm soát tài liệu hồ sơ  §7.5  Biên bản commissioning locked sau Submit  Immutable commissioning record  
        Hành động khắc phục  §10.2  NC → CM Work Order → Re-inspection  NC record + CM WO + Re-inspection log  
        Năng lực nhân sự  §7.2  Chỉ KTV được phân quyền mới có thể release  Role permission matrix  
     
   
  


 
 
   
      IMM-05  
     
       Đăng ký, Cấp phép và Hồ sơ 
       Document repository · Hiệu lực hồ sơ · Audit trail tài liệu · Pháp lý & Kỹ thuật 
     
   

   
   
     1 · Process Map (BPMN Style) 
     
       
         START 
         Asset được tạo (từ IMM-04) 
         Trigger từ IMM-04 
       
       → 
       
         1 
         Thu thập hồ sơ pháp lý (số ĐK lưu hành, giấy phép nhập khẩu) 
         Tổ HC-QLCL 
       
       → 
       
         2 
         Upload & phân loại tài liệu kỹ thuật (IFU, manual, certificate) 
         KT. HTM 
       
       → 
       
         3 
         Đăng ký số ĐK lưu hành và theo dõi hiệu lực 
         Tổ HC-QLCL 
       
       → 
       
         GW 
         Bộ hồ sơ đủ tối thiểu? 
         QMS Check 
       
       → 
       
         4 
         Phê duyệt bộ hồ sơ & đặt expiry alert 
         PTP Khối 2 / QLCL 
       
       → 
       
         END 
         Hồ sơ "Active & Compliant" 
         CMMS 
       
     
     
       
         ℹ 
          Lưu ý thiết kế:  IMM-05 hoạt động song song với IMM-04. Hồ sơ cần được hoàn thiện TRƯỚC khi asset có thể release (GW-2 của IMM-04 phải kiểm tra IMM-05 status). Đây là điểm khóa compliance. 
       
     
   

   
   
     2 · Actor & Role 
     
        Actor  Vai trò  Quyền hệ thống  Trách nhiệm chính  
        Tổ HC-QLCL & Risk  Document owner  Create/Edit/Approve Document Record  Thu thập, phân loại, theo dõi hiệu lực hồ sơ pháp lý  
        Kỹ thuật viên HTM  Document contributor  Upload documents, Edit technical docs  Upload tài liệu kỹ thuật, manual, certificate  
        PTP Khối 2  Approver  Approve document set  Phê duyệt bộ hồ sơ đủ điều kiện vận hành  
        CMMS Admin  System control  Manage expiry alerts, document lifecycle  Cấu hình cảnh báo hết hạn, kiểm soát phiên bản  
     
   

   
   
     3 · Input / Output 
     
       
         INPUT 
         
            Tài liệu  Loại  
            Số đăng ký lưu hành (Bộ Y tế)  Pháp lý – NĐ 98/2021  
            Giấy phép nhập khẩu thiết bị y tế  Pháp lý  
            Hướng dẫn sử dụng (IFU / User manual)  Kỹ thuật  
            Service manual / Maintenance manual  Kỹ thuật  
            Certificate of Conformity / CE / FDA 510k  Chứng nhận  
            Biên bản nghiệm thu (từ IMM-04)  Nội bộ  
            Hợp đồng bảo hành  Thương mại  
            Catalogue, technical specs  Kỹ thuật  
         
       
       
         OUTPUT 
         
            Đầu ra  DocType  
            Document record gắn với Asset   Asset Document  (custom)  
            Trạng thái hồ sơ: Compliant / Incomplete / Expired   Asset.document_status   
            Alert hết hạn ĐK / Giấy phép  Frappe Notification  
            Dashboard compliance rate  KPI-DASH-IMMIS-05  
            Audit trail mọi thay đổi tài liệu  Document Change Log  
         
       
     
   

   
   
     4 · User Stories (INVEST) 
     
       🟣  US-05-01:  Với tư cách là  Tổ HC-QLCL , tôi muốn  upload và phân loại tài liệu theo loại (pháp lý/kỹ thuật/chứng nhận) và gắn trực tiếp với từng Asset ID  để  tra cứu hồ sơ nhanh trong kiểm tra . 
       ✅ SP: 5 
     
     
       🟣  US-05-02:  Với tư cách là  Tổ HC-QLCL , tôi muốn  nhận cảnh báo trước 90/60/30 ngày khi giấy phép hoặc ĐK lưu hành sắp hết hạn  để  chủ động gia hạn trước khi vi phạm pháp lý . 
       ✅ SP: 3 
     
     
       🟣  US-05-03:  Với tư cách là  PTP Khối 2 , tôi muốn  xem tỷ lệ tài sản có đủ hồ sơ hợp lệ theo khoa/phòng  để  ưu tiên xử lý tồn đọng hồ sơ . 
       ✅ SP: 3 
     
   

   
   
     5 · Acceptance Criteria (Gherkin) 
      Scenario: Upload và gắn tài liệu cho Asset 
 Given  Asset đã được tạo với status "Active"
 When  HC-QLCL upload file PDF và chọn loại "Số đăng ký lưu hành" + nhập ngày hết hạn
 Then  Tài liệu được lưu gắn với Asset ID tương ứng
 And  System tự tạo reminder 90 ngày trước expiry date
 And  Document version = 1.0, status = "Active" 

      Scenario: Tài liệu hết hạn và cảnh báo 
 Given  Số đăng ký lưu hành của Asset XYZ có expiry_date = hôm nay + 25 ngày
 When  Hệ thống chạy job kiểm tra định kỳ hàng ngày
 Then  Gửi email + in-app notification đến Tổ HC-QLCL
 And  Asset.document_status = "Expiring Soon"
 And  Dashboard compliance widget highlight màu vàng cho asset đó 
   

   
   
     6 · Business Rules 
     
        Mã rule  Nội dung  Kiểm soát  
         BR-05-01   Thiết bị y tế thuộc nhóm A/B/C theo NĐ98/2021 PHẢI có số ĐK lưu hành hoặc miễn đăng ký có văn bản trước khi release  Document completeness check linked to IMM-04 GW-2  
         BR-05-02   Mọi tài liệu được phê duyệt không được xóa, chỉ được archive với lý do  Hard delete disabled; only "Archived" status change  
         BR-05-03   Phiên bản mới của tài liệu phải có change summary và người duyệt  Version control + approver field mandatory  
         BR-05-04   Alert hết hạn phải gửi tối thiểu 90 ngày trước, nhắc lại 60 và 30 ngày  Frappe Notification Rules  
         BR-05-05   Hồ sơ tối thiểu cho một asset phải bao gồm: IFU, số ĐK (nếu có), service manual  Document checklist validation on Asset  
     
   

   
   
     7 · Exception Handling 
     
        Tình huống  Xử lý hệ thống  Xử lý nghiệp vụ  
        Thiết bị nhập khẩu cần miễn ĐK theo NĐ98  Cho phép chọn "Exempt" + upload văn bản miễn đăng ký  Tổ HC-QLCL lưu công văn miễn đăng ký làm bằng chứng  
        Tài liệu bị mất / NCC không cung cấp  Tạo "Document Request" task với deadline, set status = "Incomplete"  Phòng vật tư theo dõi yêu cầu NCC; leo thang nếu quá 30 ngày  
        Số ĐK lưu hành hết hạn khi đang vận hành  Asset.document_status = "Non-Compliant", cảnh báo đỏ dashboard  Tạm đình chỉ nếu không gia hạn được; leo thang BGĐ  
        Tài liệu confidential của NCC  Đặt document visibility = "Internal Only"  Chỉ nhóm HTM và QLCL truy cập được  
     
   

   
   
     8 · WHO + 9 · QMS Mapping 
     
        Khía cạnh  WHO / QMS Reference  Áp dụng vào IMM-05  
        Document repository per asset/model  WHO CMMS §3.2.3; HTM 2025 §4.2  Asset Document child table gắn với Asset record  
        Kiểm soát tài liệu  ISO 9001 §7.5 "Documented Information"  Version control, approval workflow, immutable after approve  
        Tuân thủ pháp lý Việt Nam  NĐ 98/2021/NĐ-CP – Quản lý TTBYT  Trường số ĐK lưu hành, ngày hết hạn, loại thiết bị A/B/C  
        Post-market surveillance documents  WHO HTM §6.4 "Regulatory compliance"  Link tới IMM-10 khi có recall/FSCA liên quan đến số model  
        Audit trail  ISO 9001 §7.5.3  Document Change Log với timestamp + user  
     
   
  


 
 
   
      IMM-08  
     
       Bảo trì Định kỳ (Preventive Maintenance) 
       PM Schedule · Work Order · Checklist · Compliance tracking · PM dashboard 
     
   

   
   
     1 · Process Map (BPMN Style) 
     
       
         START 
         Lịch PM đến hạn / Trigger tự động 
         CMMS Scheduler 
       
       → 
       
         1 
         Tạo PM Work Order tự động 
         CMMS Auto 
       
       → 
       
         2 
         Assign KTV & xác nhận lịch 
         Workshop Manager 
       
       → 
       
         3 
         Thông báo khoa phòng & điều phối thiết bị 
         KTV / Workshop 
       
       → 
       
         4 
         Thực hiện PM theo checklist chuẩn 
         KTV HTM 
       
       → 
       
         GW 
         Phát hiện lỗi? 
         KTV HTM 
       
       → 
       
         5 
         Cập nhật kết quả & đóng WO 
         KTV HTM 
       
       → 
       
         6 
         Cập nhật lịch PM tiếp theo 
         CMMS Auto 
       
       → 
       
         END 
         PM gắn sticker + trả thiết bị 
         KTV HTM 
       
     
     
       
         ⚠ 
          Exception path (phát hiện lỗi khi PM):  Nếu lỗi minor → hoàn thành PM + mở CM WO tham chiếu PM WO. Nếu lỗi major → dừng PM, set status "Out of Service", mở CM WO khẩn. Cả hai case đều tham chiếu số PM WO gốc. 
       
     
   

   
   
     2 · Actor & Role 
     
        Actor  Vai trò  Quyền  Trách nhiệm  
        CMMS Scheduler  Hệ thống – auto trigger  System process  Tạo WO tự động theo PM Schedule  
        Workshop Manager  Lập kế hoạch & phân công  Assign WO, view PM calendar  Phân công KTV, điều phối lịch với khoa phòng  
        Kỹ thuật viên HTM  Thực hiện PM  Execute WO, fill checklist  Thực hiện PM, điền kết quả, gắn sticker  
        Trưởng khoa phòng  Phối hợp  View schedule, confirm availability  Xác nhận thiết bị sẵn sàng cho PM, ký biên bản  
        PTP Khối 2  Giám sát KPI PM compliance  View PM dashboard  Theo dõi tỷ lệ PM đúng hạn, quyết định escalation  
     
   

   
   
     3 · Input / Output 
     
       
         INPUT 
         
            Đầu vào  Nguồn  
            PM Schedule (interval, due date)  Asset Maintenance Schedule  
            PM Checklist template theo Asset Category  Maintenance Template  
            Lịch sử PM trước (last PM date, last result)  Asset Maintenance Log  
            Service manual (phần PM)  IMM-05 document  
            Danh sách vật tư tiêu hao cần thay  Spare parts catalog  
         
       
       
         OUTPUT 
         
            Đầu ra  DocType  
            PM Work Order (WO)   Asset Maintenance   
            PM Maintenance Log (kết quả từng lần)   Asset Maintenance Log   
            Checklist kết quả PM đã ký  Child table of Maintenance  
            PM sticker (physical) + digital tag  Print Format + Asset field update  
            CM WO (nếu phát sinh)   Asset Repair   
            Lịch PM kỳ tiếp theo (auto)   Asset Maintenance.next_due_date   
         
       
     
   

   
   
     4 · User Stories (INVEST) 
     
       🟢  US-08-01:  Với tư cách là  CMMS , tôi muốn  tự động tạo PM Work Order khi đến ngày đáo hạn theo lịch  để  không có thiết bị nào bị bỏ sót PM do quên lịch thủ công . 
       ✅ SP: 8 
     
     
       🟢  US-08-02:  Với tư cách là  Kỹ thuật viên HTM , tôi muốn  xem PM checklist theo template của từng model thiết bị ngay trong WO  để  thực hiện đúng quy trình mà không cần tra tài liệu riêng . 
       ✅ SP: 5 
     
     
       🟢  US-08-03:  Với tư cách là  Workshop Manager , tôi muốn  xem lịch PM của tuần/tháng theo dạng calendar view  để  điều phối nhân lực và lịch với khoa phòng hiệu quả . 
       ✅ SP: 3 
     
     
       🟢  US-08-04:  Với tư cách là  PTP Khối 2 , tôi muốn  xem PM compliance rate (% WO hoàn thành đúng hạn) theo tháng  để  báo cáo BGĐ và cải tiến kế hoạch PM . 
       ✅ SP: 3 
     
   

   
   
     5 · Acceptance Criteria (Gherkin) 
      Scenario: Tự động tạo PM WO và hoàn thành 
 Given  Asset A có PM Schedule interval = 3 tháng, last_pm_date = 90 ngày trước
 When  CMMS scheduler chạy daily job
 Then  Tạo Asset Maintenance WO với type = "Preventive Maintenance"
 And  WO được assign tự động đến Workshop queue
 And  Gửi notification đến Workshop Manager
 When  KTV hoàn thành checklist và Submit WO
 Then  Asset.last_pm_date = today
 And  Asset.next_pm_date = today + interval
 And  Maintenance Log entry được tạo với timestamp và KTV name 

      Scenario: PM quá hạn 
 Given  PM WO có due_date = hôm nay - 5 ngày và status = "Open"
 When  Scheduler chạy overdue check
 Then  WO status = "Overdue"
 And  Gửi alert đến Workshop Manager và PTP Khối 2
 And  Asset hiển thị badge "PM Overdue" trên dashboard 
   

   
   
     6 · Business Rules 
     
        Mã  Rule  Kiểm soát  
         BR-08-01   PM WO phải có checklist template tương ứng với Asset Category trước khi assign  Validate template exists on WO creation  
         BR-08-02   Khi phát hiện lỗi trong PM, phải mở CM WO có tham chiếu số PM WO gốc  CM WO field "source_pm_wo" mandatory khi từ PM  
         BR-08-03   Ngày PM tiếp theo được tính từ ngày HOÀN THÀNH (không phải ngày dự kiến)  next_pm_date = completion_date + interval  
         BR-08-04   Thiết bị "Out of Service" không được tạo PM WO mới cho đến khi restored  Workflow condition check on WO creation  
         BR-08-05   PM WO hoàn thành sau due_date vẫn tính là "Late" trên compliance report  Late flag = completion_date > due_date  
     
   

   
   
     7 · Exception Handling 
     
        Tình huống  Xử lý hệ thống  Xử lý nghiệp vụ  
        Thiết bị đang sử dụng ca cấp cứu khi PM đến hạn  WO status = "Pending – Device Busy", reschedule  Workshop phối hợp khoa phòng đặt lại lịch trong vòng 7 ngày  
        KTV bị ốm / vắng khi PM đến hạn  WO unassigned, alert Workshop Manager  Manager reassign KTV khác hoặc hoãn có ghi lý do  
        Không có vật tư tiêu hao cần thay thế  WO blocked, trigger spare part request  Liên hệ kho, nếu tồn kho = 0 thì đặt mua khẩn  
        Thiết bị có multiple PM types (annual + quarterly)  Tạo riêng WO cho mỗi loại PM, phân biệt bằng maintenance_type  Workshop có thể combine nếu cùng ngày  
     
   

   
   
     8 · WHO + 9 · QMS Mapping 
     
        Khía cạnh  Reference  Áp dụng IMM-08  
        PM là scheduled activity, interval theo manufacturer  WHO Maintenance §5.3.1; WHO CMMS §3.2.3  Maintenance Template per Asset Category, interval configurable  
        Work order system  WHO Maintenance Programme §5.3.6  Asset Maintenance DocType với đủ procedure + history  
        PM compliance tracking  WHO HTM 2025 §6.2  PM compliance rate KPI = completed on time / total scheduled  
        Kiểm soát sản xuất & cung cấp dịch vụ  ISO 9001 §8.5.1  PM checklist mandatory, completion sign-off  
        Hồ sơ bảo trì  ISO 9001 §7.5; WHO Maintenance §5.3.5  Asset Maintenance Log immutable, searchable by asset/date  
     
   
  


 
 
   
      IMM-09  
     
       Sửa chữa, Phụ tùng và Cập nhật Phần mềm 
       Corrective execution · Spare part traceability · Firmware change control · Cost tracking 
     
   

   
   
     1 · Process Map (BPMN Style) 
     
       
         START 
         Yêu cầu sửa chữa (từ khoa phòng hoặc PM/CM) 
         Khoa phòng / KTV 
       
       → 
       
         1 
         Tạo CM Work Order + mô tả sự cố 
         KTV / Workshop 
       
       → 
       
         2 
         Đánh giá lỗi (troubleshoot) 
         KTV HTM 
       
       → 
       
         GW-1 
         Cần phụ tùng? 
         KTV 
       
       → 
       
         3 
         Yêu cầu & cấp phát phụ tùng từ kho 
         KTV / Kho 
       
       → 
       
         4 
         Thực hiện sửa chữa / thay linh kiện 
         KTV HTM 
       
       → 
       
         5 
         Kiểm tra sau sửa chữa 
         KTV HTM 
       
       → 
       
         GW-2 
         Pass test? 
         KTV / KT trưởng 
       
       → 
       
         END 
         Return to service · WO closed 
         CMMS 
       
     
     
       
         🔴 
          Firmware/SW update path:  Cập nhật firmware phải qua Change Control — cần phê duyệt KT trưởng và log version trước/sau. Không thực hiện update firmware nếu chưa có approved change request. 
       
     
   

   
   
     2 · Actor & Role 
     
        Actor  Vai trò  Quyền  Trách nhiệm  
        Khoa phòng sử dụng  Báo cáo sự cố  Create Service Request  Báo lỗi thiết bị, cung cấp mô tả hiện tượng  
        KTV HTM  Sửa chữa chính  Create/Execute CM WO, Request spare parts  Troubleshoot, sửa, thay linh kiện, test  
        Kho vận  Cấp phát phụ tùng  Issue spare parts, update inventory  Cấp phát linh kiện, ghi nhận xuất kho  
        KT trưởng / Workshop Manager  Kiểm soát phụ tùng và firmware  Approve firmware change, sign-off repair  Phê duyệt change request firmware, verify sau sửa  
        NCC / Đại lý bảo hành  External service provider  View WO (read-only external portal)  Thực hiện sửa chữa ngoài warranty/contract  
     
   

   
   
     3 · Input / Output 
     
       
         INPUT 
         
            Đầu vào  Nguồn  
            Yêu cầu sửa chữa / mô tả sự cố  Khoa phòng / PM WO  
            Lịch sử sửa chữa trước  Asset Repair history  
            Danh sách spare parts catalog  IMM-15 / Kho  
            Service manual – phần sửa chữa  IMM-05 document  
            Firmware version hiện tại  Asset technical specs field  
         
       
       
         OUTPUT 
         
            Đầu ra  DocType  
            CM Work Order   Asset Repair   
            Danh sách phụ tùng đã dùng + chi phí   Asset Repair.items (child table)   
            Firmware change log (version trước/sau)   Asset Activity  / custom field  
            Biên bản bàn giao sau sửa chữa  Print Format WO  
            Tổng chi phí sửa chữa   Asset Repair.repair_cost   
            MTTR metric  KPI-DASH-IMMIS-09  
         
       
     
   

   
   
     4 · User Stories (INVEST) 
     
       🟠  US-09-01:  Với tư cách là  KTV HTM , tôi muốn  ghi nhận phụ tùng đã dùng trong WO và hệ thống tự cập nhật tồn kho  để  truy nguyên được phụ tùng đã gắn vào từng thiết bị . 
       ✅ SP: 8 
     
     
       🟠  US-09-02:  Với tư cách là  KT trưởng , tôi muốn  phê duyệt change request trước khi firmware được cập nhật  để  ngăn cập nhật không kiểm soát ảnh hưởng đến vận hành lâm sàng . 
       ✅ SP: 5 
     
     
       🟠  US-09-03:  Với tư cách là  PTP Khối 2 , tôi muốn  xem Mean Time To Repair (MTTR) theo loại thiết bị  để  đánh giá hiệu quả xử lý sự cố và xác định điểm cải tiến . 
       ✅ SP: 3 
     
   

   
   
     5 · Acceptance Criteria (Gherkin) 
      Scenario: Ghi nhận phụ tùng và tự cập nhật tồn kho 
 Given  CM WO đang ở trạng thái "In Progress"
 When  KTV thêm spare part "Filter HEPA – part#123" qty=1 vào WO
 Then  Warehouse stock của part#123 giảm 1 đơn vị
 And  Ghi nhận xuất kho với reference = CM WO number
 And  WO cost được cập nhật = giá phụ tùng × qty + labor cost 

      Scenario: Cập nhật firmware phải qua approval 
 Given  KTV muốn cập nhật firmware từ v2.1 → v2.3 cho Asset ID XYZ
 When  KTV chọn "Firmware Update" trong WO và nhập version mới
 Then  Hệ thống tạo "Firmware Change Request" và chuyển trạng thái "Pending Approval"
 And  KT trưởng nhận notification để review
 But  KTV không thể submit WO với firmware update cho đến khi được duyệt
 When  KT trưởng Approve
 Then  Asset.firmware_version được cập nhật = v2.3 với timestamp + approver 
   

   
   
     6 · Business Rules 
     
        Mã  Rule  Kiểm soát  
         BR-09-01   Mọi phụ tùng thay thế phải truy nguyên về WO cụ thể  Spare part item line trong WO mandatory  
         BR-09-02   Firmware update phải có approval trước khi thực hiện  Firmware Change Request workflow  
         BR-09-03   CM WO từ PM phải reference số PM WO gốc  source_wo field mandatory  
         BR-09-04   Sửa chữa do NCC thực hiện phải ghi nhận chi phí và kết quả kiểm tra after-repair của KTV nội bộ  External repair flag + internal verification mandatory  
         BR-09-05   MTTR = thời gian từ lúc WO tạo đến lúc WO closed + asset returned to service  Computed field = closed_at - created_at  
     
   

   
   
     7 · Exception Handling + 8 · WHO + 9 · QMS 
     
        Loại  Nội dung  Áp dụng  
        Exception: Không có phụ tùng tồn kho  WO blocked "Waiting Parts", tạo spare part request  Link sang IMM-15 để mua phụ tùng khẩn  
        Exception: Sửa nhiều lần không khỏi  Sau 3 lần CM WO cùng lỗi → trigger "Chronic Failure Alert"  Escalate lên xem xét replacement (IMM-13)  
        WHO: Corrective maintenance  WHO Maintenance §6.2 – "resolve problem, replace/mend faulty parts, test device"  CM WO với troubleshoot step, repair action, after-repair test  
        WHO: MTTR tracking  WHO HTM 2025 – "mean time to repair measure of effectiveness"  MTTR KPI per asset category on dashboard  
        QMS: Change control  ISO 9001 §8.5.6 "Control of changes"  Firmware Change Request approval workflow  
        QMS: Truy nguyên phụ tùng  ISO 9001 §8.5.2 "Identification and traceability"  Spare part → WO → Asset → Date linkage  
     
   
  


 
 
   
      IMM-11  
     
       Hiệu năng và Hiệu chuẩn (Inspection & Calibration) 
       Calibration planning · Certificate management · Out-of-tolerance handling · CAPA trigger 
     
   

   
   
     1 · Process Map (BPMN Style) 
     
       
         START 
         Lịch hiệu chuẩn đến hạn 
         CMMS Scheduler 
       
       → 
       
         1 
         Tạo Calibration/Inspection WO 
         CMMS Auto / KT trưởng 
       
       → 
       
         2 
         Gửi thiết bị đến lab hiệu chuẩn (nội bộ/bên ngoài) 
         Workshop 
       
       → 
       
         3 
         Đo lường baseline → điều chỉnh → xác minh 
         KTV / Lab hiệu chuẩn 
       
       → 
       
         GW 
         Kết quả Pass? 
         KTV 
       
       → 
       
         4 
         Upload certificate + cập nhật ngày hiệu lực 
         KTV / QLCL 
       
       → 
       
         END 
         Asset = "Calibrated & Valid" 
         CMMS 
       
     
     
       
         🔴 
          Out-of-tolerance path:  Fail → Asset status = "Out of Service", trigger CAPA record, phân tích nguyên nhân, xem xét toàn bộ kết quả lâm sàng liên quan trong khoảng thời gian thiết bị lệch chuẩn (lookback period). 
       
     
   

   
   
     2 · Actor & Role 
     
        Actor  Vai trò  Quyền  Trách nhiệm  
        Workshop / KTV hiệu chuẩn  Thực hiện  Create Calibration WO, upload cert  Thực hiện calibration, ghi kết quả đo  
        Lab hiệu chuẩn bên ngoài  External provider  Provide certificate (offline)  Phát hành chứng chỉ hiệu chuẩn có truy nguyên  
        Tổ HC-QLCL  CAPA owner  Create CAPA, manage lookback  Xử lý CAPA khi out-of-tolerance, assess risk lâm sàng  
        KT trưởng  Sign-off  Approve calibration result  Phê duyệt kết quả và cho phép tái vận hành  
        PTP Khối 2  Oversight  Dashboard view, CAPA oversight  Theo dõi compliance, chỉ đạo CAPA nghiêm trọng  
     
   

   
   
     3 · Input / Output 
     
       
         INPUT 
         
            Đầu vào  Nguồn  
            Lịch hiệu chuẩn (interval, due date)  Asset calibration schedule  
            Tiêu chí chấp nhận (tolerance)  Manufacturer spec / ISO standard  
            Certificate hiệu chuẩn cũ  IMM-05 document  
            Reference standard (thiết bị chuẩn đo)  Lab hiệu chuẩn  
         
       
       
         OUTPUT 
         
            Đầu ra  DocType  
            Calibration/Inspection record   Asset Maintenance Log  (type=Calibration)  
            Chứng chỉ hiệu chuẩn (PDF) đính kèm   File attachment on Asset   
            Certificate expiry date   Asset.calibration_due_date   
            CAPA record (nếu fail)   Quality Inspection / CAPA   
            Lookback assessment report  Custom report  
         
       
     
   

   
   
     4 · User Stories (INVEST) 
     
       🔴  US-11-01:  Với tư cách là  KTV hiệu chuẩn , tôi muốn  upload certificate PDF và hệ thống tự đọc ngày hết hạn để cập nhật lịch kỳ tiếp theo  để  không phải nhập tay và tránh nhầm ngày . 
       ✅ SP: 5 | [Giả định: cần manual input, auto OCR là enhancement] 
     
     
       🔴  US-11-02:  Với tư cách là  Tổ HC-QLCL , tôi muốn  hệ thống tự động tạo CAPA khi thiết bị fail hiệu chuẩn  để  đảm bảo rủi ro lâm sàng được đánh giá kịp thời . 
       ✅ SP: 8 
     
     
       🔴  US-11-03:  Với tư cách là  PTP Khối 2 , tôi muốn  xem danh sách thiết bị đang hết hạn hiệu chuẩn trong 30 ngày tới  để  lên kế hoạch kinh phí và nhân lực . 
       ✅ SP: 3 
     
   

   
     5 · Acceptance Criteria (Gherkin) 
      Scenario: Hiệu chuẩn thành công 
 Given  Calibration WO đang "In Progress" cho Asset ID ABC
 When  KTV ghi kết quả đo = "Pass" và upload certificate PDF
 Then  Asset.calibration_status = "Calibrated"
 And  Asset.calibration_cert_expiry = ngày ghi trên certificate
 And  Hệ thống tạo lịch calibration kỳ tiếp theo = expiry - buffer period
 And  Certificate được lưu trong IMM-05 document repository 

      Scenario: Thiết bị fail hiệu chuẩn (out-of-tolerance) 
 Given  KTV ghi kết quả = "Fail – Out of Tolerance" 
 Then  Asset.status = "Out of Service"
 And  Hệ thống tự tạo CAPA record với type = "Calibration Failure"
 And  Alert gửi đến Tổ HC-QLCL và PTP Khối 2
 And  CAPA yêu cầu nhập "lookback_period" và "clinical_impact_assessment"
 But  Asset không thể return to service cho đến khi CAPA closed và re-calibration passed 
   

   
   
     6 · Business Rules + 7 · Exception + 8-9 · WHO/QMS 
     
        Loại  Nội dung  Kiểm soát / Reference  
         RULE  BR-11-01  Thiết bị đo lường lâm sàng PHẢI có certificate hiệu chuẩn còn hiệu lực mới được sử dụng  Calibration status check trước khi cho phép lâm sàng dùng  
         RULE  BR-11-02  Out-of-tolerance PHẢI kích hoạt CAPA, không được đóng WO nếu chưa có CAPA  Workflow condition: fail → CAPA mandatory  
         RULE  BR-11-03  Certificate hiệu chuẩn phải từ lab được công nhận (ISO 17025 hoặc cơ quan kiểm định VN)  Lab accreditation field trong WO  
         EXCEPTION   Không có lab nội bộ → gửi ra ngoài: WO status = "Sent to External Lab"  External lab tracking với estimated return date  
         WHO   WHO HTM 2025 §6.4.3 "Calibration = baseline measurement, adjustment, verification, documentation"  4-step calibration log field trong WO  
         QMS   ISO 9001 §7.1.5 "Monitoring and measuring resources – calibration"  Calibration cert linkage, alert, audit trail  
         QMS   ISO 9001 §10.2 "Nonconformity and corrective action"  CAPA workflow gắn với calibration fail record  
     
   
  


 
 
   
      IMM-12  
     
       Bảo trì Khắc phục (Corrective Maintenance) 
       Incident triage · Escalation · RCA · SLA tracking · Recovery management 
     
   

   
   
     1 · Process Map (BPMN Style) 
     
       
         START 
         Sự cố xảy ra / Báo cáo từ user 
         Khoa phòng 
       
       → 
       
         1 
         Tiếp nhận & triage sự cố (P1/P2/P3/P4) 
         Workshop / Hotline 
       
       → 
       
         2 
         Tạo CM Incident WO + gán priority 
         Workshop 
       
       → 
       
         3 
         Assign KTV & thực hiện corrective action 
         Workshop Manager 
       
       → 
       
         GW-1 
         Giải quyết được nội bộ? 
         KT trưởng 
       
       → 
       
         4 
         Kiểm tra sau sửa & xác nhận phục hồi 
         KTV / Khoa phòng 
       
       → 
       
         GW-2 
         RCA cần thiết? 
         KT trưởng 
       
       → 
       
         END 
         WO closed · SLA recorded · RCA filed 
         CMMS 
       
     
     
       
         ⚠ 
          Escalation path:  GW-1 = No → Escalate NCC/bên ngoài, SLA clock continues. P1 (thiết bị cấp cứu) response SLA = 2h, resolution SLA = 8h. P2 = 4h/24h. P3 = 24h/72h. P4 = 72h/7 ngày. 
       
     
   

   
   
     2 · Actor & Role 
     
        Actor  Vai trò  Quyền  Trách nhiệm  
        Nhân viên khoa phòng  Báo sự cố  Submit Service Request  Mô tả hiện tượng, cung cấp Asset ID  
        Workshop (triage team)  Tiếp nhận & triage  Create CM WO, set priority  Phân loại mức độ khẩn cấp, tạo WO  
        KTV HTM  Thực hiện CM  Execute WO, update status  Sửa chữa, ghi nhận action, test thiết bị  
        KT trưởng  Kiểm soát & leo thang  Escalate, Approve RCA  Quyết định escalation, phê duyệt RCA  
        Tổ HC-QLCL  RCA + CAPA owner  Create/manage RCA, CAPA  Điều tra nguyên nhân gốc, đề xuất hành động  
        PTP Khối 2  SLA oversight  Dashboard, override SLA  Theo dõi SLA, chỉ đạo xử lý sự cố P1  
     
   

   
   
     3 · Input / Output 
     
       
         INPUT 
         
            Đầu vào  Nguồn  
            Mô tả sự cố từ user  Khoa phòng  
            Asset ID bị ảnh hưởng  User / Asset lookup  
            Lịch sử sự cố trước  Asset Repair history  
            SLA matrix theo equipment criticality  SLA config master  
            Danh sách backup equipment  Asset inventory  
         
       
       
         OUTPUT 
         
            Đầu ra  DocType  
            CM Incident Work Order   Asset Repair  (type=Corrective)  
            SLA response/resolution time log   Asset Repair.response_time, resolution_time   
            RCA report   Quality Inspection / custom RCA DocType   
            CAPA record (nếu cần)   CAPA linked to RCA   
            Downtime record cho thiết bị   Asset Activity  (type=Downtime)  
            MTTR, SLA compliance KPI  KPI-DASH-IMMIS-12  
         
       
     
   

   
   
     4 · User Stories (INVEST) 
     
       🔵  US-12-01:  Với tư cách là  Workshop , tôi muốn  hệ thống tự động tính SLA breach time và gửi cảnh báo khi sắp vi phạm SLA  để  đảm bảo phản hồi kịp thời với thiết bị ưu tiên cao . 
       ✅ SP: 8 
     
     
       🔵  US-12-02:  Với tư cách là  Tổ HC-QLCL , tôi muốn  tạo RCA record gắn với CM WO và theo dõi trạng thái hành động khắc phục  để  ngăn tái phát sự cố tương tự . 
       ✅ SP: 5 
     
     
       🔵  US-12-03:  Với tư cách là  Khoa phòng , tôi muốn  nhận cập nhật tự động về tiến trình sửa chữa thiết bị của mình  để  chủ động điều chỉnh hoạt động lâm sàng khi thiết bị dừng . 
       ✅ SP: 3 
     
   

   
     5 · Acceptance Criteria (Gherkin) 
      Scenario: Triage sự cố P1 và SLA tracking 
 Given  Khoa ICU báo máy thở bị lỗi lúc 14:30
 When  Workshop tạo CM WO và gán Priority = P1
 Then  SLA response_deadline = 14:30 + 2h = 16:30
 And  SLA resolution_deadline = 14:30 + 8h = 22:30
 And  Alert gửi đến KT trưởng và PTP Khối 2 ngay lập tức
 And  Notification cảnh báo 30 phút trước khi breach SLA response 

      Scenario: Tạo RCA khi sự cố tái diễn 
 Given  Asset ID XYZ có 3 CM WO cùng fault type trong 6 tháng
 When  KT trưởng đóng CM WO lần thứ 3
 Then  Hệ thống hiển thị cảnh báo "Chronic Failure – RCA Recommended"
 And  Tạo liên kết đến 3 WO trước để phục vụ RCA
 And  Tổ HC-QLCL nhận notification để mở RCA record 
   

   
   
     6 · Business Rules + 7 · Exception + 8-9 · WHO/QMS 
     
        Loại  Nội dung  Kiểm soát / Reference  
         RULE  BR-12-01  P1 (life-critical device) phải có response ≤ 2h, resolution ≤ 8h  SLA config per equipment criticality class  
         RULE  BR-12-02  WO P1 không thể close nếu chưa có xác nhận "Return to Service" từ khoa phòng  Workflow: require department sign-off cho P1  
         RULE  BR-12-03  Sự cố tái phát ≥ 3 lần cùng fault → bắt buộc RCA  Chronic failure detection + mandatory RCA flag  
         EXCEPTION   Không có backup device khi P1 dừng → cần điều chuyển thiết bị khoa khác  Link sang IMM-13 Asset Movement khẩn  
         WHO   WHO Maintenance §6.2 "Corrective maintenance: restore functionality, minimize downtime, MTTR tracking"  MTTR = WO created → WO closed + return to service  
         WHO   WHO HTM 2025 – "Efficient response required; heavy reliance on CM not recommended"  Chronic failure alert → trigger replacement review  
         QMS   ISO 9001 §10.2 "Nonconformity and corrective action – RCA, CAPA"  RCA DocType linked to CM WO, CAPA lifecycle management  
         QMS   ISO 9001 §8.5.1 "Control of production – availability of equipment"  Downtime tracking, equipment availability KPI  
     
   
  


 
 
   
     
       Wave 1 — Cross-Module Summary Matrix 
       DocType mapping · ERPNext native vs. custom · Dependency chain 
     
   

   
     DocType Mapping — Existing vs. Required 
     
        Module  DocType ERPNext Native  Cần bổ sung field  Custom DocType mới  Lý do custom  
       
          IMM-04  
         Asset, Asset Category, Asset Movement, Location 
         Asset: commissioning_status, installation_date, initial_inspection_result, asset_qr_code 
         Asset Commissioning (child checklist) 
         ERPNext không có initial inspection checklist template theo asset category 
       
       
          IMM-05  
         File attachment on Asset 
         Asset: document_status, cert_expiry_date 
         Asset Document (phân loại: pháp lý/kỹ thuật/chứng nhận, expiry, version) 
         Cần theo dõi hiệu lực từng loại tài liệu riêng biệt, không chỉ lưu file 
       
       
          IMM-08  
         Asset Maintenance, Asset Maintenance Log, Asset Maintenance Task 
         Asset Maintenance: pm_checklist_template, pm_compliance_flag, overdue_flag 
         Maintenance Checklist Template (per asset category) 
         ERPNext Maintenance Task chưa đủ cấu trúc checklist theo model 
       
       
          IMM-09  
         Asset Repair (có sẵn items child table, repair_cost) 
         Asset Repair: source_pm_wo, firmware_version_before, firmware_version_after, mttr 
         Firmware Change Request 
         Change control firmware là nghiệp vụ riêng, cần approval workflow độc lập 
       
       
          IMM-11  
         Asset Maintenance Log (dùng type=Calibration) 
         Asset: calibration_due_date, calibration_status, calibration_cert_expiry; Maintenance Log: calibration_result, tolerance_pass 
         CAPA Record (nếu chưa có trong ERPNext Quality module) 
         Lookback period & clinical impact assessment là field đặc thù y tế 
       
       
          IMM-12  
         Asset Repair (dùng làm CM Incident WO) 
         Asset Repair: incident_priority, sla_response_deadline, sla_resolution_deadline, response_time_actual, rca_required 
         RCA Record (gắn với Asset Repair), Downtime Log (Asset Activity extension) 
         SLA tracking và RCA lifecycle cần workflow riêng, không có sẵn trong ERPNext core 
       
     
   

   
     Module Dependency Chain 
     
        Module  Phụ thuộc vào  Cung cấp cho  Trigger point  
        IMM-04  IMM-03 (PO/Asset spec)  IMM-05 (tạo asset để gắn hồ sơ), IMM-08 (tạo PM schedule sau commissioning)  Asset tạo xong → tự trigger IMM-05 checklist + IMM-08 first schedule  
        IMM-05  IMM-04 (asset phải tồn tại)  IMM-04 GW-2 (release gate), IMM-08, IMM-09, IMM-11, IMM-12  Document expire → alert, non-compliant → block release nếu cần  
        IMM-08  IMM-04 (asset active), IMM-05 (service manual)  IMM-09 (PM fail → CM), IMM-12 (PM fail → incident)  PM due date → auto WO; PM fail → CM WO  
        IMM-09  IMM-08 (PM source WO), IMM-12 (incident trigger)  IMM-11 (sau CM cần re-calibrate), IMM-15 (spare part consumption)  Repair complete → return to service or flag for re-calibration  
        IMM-11  IMM-04 (baseline), IMM-09 (post-repair)  IMM-12 (CAPA), IMM-05 (cert storage)  Calibration fail → CAPA; Pass → update cert expiry  
        IMM-12  IMM-08/09 (fail triggers), khoa phòng (incident report)  IMM-09 (repair action), IMM-11 (post-repair calibration), IMM-13 (chronic failure → replacement)  Incident open → SLA clock start; chronic fail → RCA  
     
   

   
     Tổng hợp Business Rule Priority 
     
        Module  Rule Critical nhất  Risk nếu bỏ qua  
        IMM-04  BR-04-03: Không release nếu còn NC chưa đóng  Thiết bị lỗi đi vào vận hành lâm sàng  
        IMM-05  BR-05-01: Số ĐK lưu hành bắt buộc trước release  Vi phạm NĐ 98/2021, rủi ro pháp lý  
        IMM-08  BR-08-02: CM WO phải reference PM WO gốc  Mất truy nguyên, không phân tích PM-CM correlation  
        IMM-09  BR-09-02: Firmware phải qua approval  Update không kiểm soát → lỗi lâm sàng  
        IMM-11  BR-11-02: Fail calibration → CAPA bắt buộc  Kết quả đo sai ảnh hưởng chẩn đoán/điều trị  
        IMM-12  BR-12-01: P1 SLA ≤ 2h response  Thiết bị cấp cứu dừng lâu → rủi ro bệnh nhân  
     
   
 

  

 
   AssetCore · BA Analysis Wave 1 · v1.0 · 2025 
   6 Modules: IMM-04 · IMM-05 · IMM-08 · IMM-09 · IMM-11 · IMM-12 
   WHO HTM + ISO 9001 + NĐ 98/2021 + ERPNext/Frappe 
 

 
 
