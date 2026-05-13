"""Create Market Benchmark records and Link-in Risk Assessments for all 3 Tech Specs."""
import frappe


def run():
    frappe.set_user("Administrator")

    # Market Benchmarks per Tech Spec
    mb_data = [
        {
            "spec_ref": "TS-26-00007",
            "candidates": [
                {"manufacturer": "Mindray", "model": "BeneView T9", "country": "China",
                 "spec_match_pct": 95, "price_estimate": 320000000, "price_source": "Vendor Quote",
                 "support_tier": "Tier1", "local_partner": "Công ty TNHH Mindray Việt Nam", "in_avl": 1,
                 "notes": "Phổ biến tại VN, phụ tùng sẵn có, đào tạo online — báo giá Q4/2025"},
                {"manufacturer": "Philips", "model": "IntelliVue MX550", "country": "Netherlands",
                 "spec_match_pct": 92, "price_estimate": 450000000, "price_source": "Vendor Quote",
                 "support_tier": "Tier1", "local_partner": "Công ty TNHH Philips Việt Nam", "in_avl": 1,
                 "notes": "Tích hợp tốt với PACS, hỗ trợ HL7 — báo giá Q3/2025"},
                {"manufacturer": "GE Healthcare", "model": "CARESCAPE B850", "country": "USA",
                 "spec_match_pct": 88, "price_estimate": 520000000, "price_source": "Web",
                 "support_tier": "Tier2", "local_partner": "GE Vietnam Representative", "in_avl": 0,
                 "notes": "Cần nhập khẩu trực tiếp, thời gian giao hàng 12-16 tuần"},
            ]
        },
        {
            "spec_ref": "TS-26-00008",
            "candidates": [
                {"manufacturer": "Philips", "model": "EPIQ 7", "country": "Netherlands",
                 "spec_match_pct": 97, "price_estimate": 1850000000, "price_source": "Vendor Quote",
                 "support_tier": "Tier1", "local_partner": "Công ty TNHH Philips Việt Nam", "in_avl": 1,
                 "notes": "Phù hợp hoàn toàn spec, hỗ trợ DICOM đầy đủ — báo giá Q1/2026"},
                {"manufacturer": "GE Healthcare", "model": "Logiq E10", "country": "USA",
                 "spec_match_pct": 90, "price_estimate": 1650000000, "price_source": "Vendor Quote",
                 "support_tier": "Tier1", "local_partner": "Công ty TNHH GE Healthcare VN", "in_avl": 1,
                 "notes": "Probe đa dạng, đào tạo tại chỗ — báo giá Q4/2025"},
                {"manufacturer": "Siemens Healthineers", "model": "Acuson Sequoia", "country": "Germany",
                 "spec_match_pct": 85, "price_estimate": 2100000000, "price_source": "Other",
                 "support_tier": "Tier2", "local_partner": "Siemens VN Healthcare Division", "in_avl": 0,
                 "notes": "Chất lượng cao nhưng giá vượt ngân sách kế hoạch — list price 2025"},
            ]
        },
        {
            "spec_ref": "TS-26-00009",
            "candidates": [
                {"manufacturer": "Dräger", "model": "Evita V500", "country": "Germany",
                 "spec_match_pct": 98, "price_estimate": 980000000, "price_source": "Vendor Quote",
                 "support_tier": "Tier1", "local_partner": "Công ty TNHH Dräger Medical Vietnam", "in_avl": 1,
                 "notes": "Đáp ứng toàn bộ spec kỹ thuật, có sẵn kỹ thuật viên được đào tạo — báo giá Q1/2026"},
                {"manufacturer": "Hamilton Medical", "model": "C6", "country": "Switzerland",
                 "spec_match_pct": 93, "price_estimate": 1100000000, "price_source": "Vendor Quote",
                 "support_tier": "Tier2", "local_partner": "Meditronic Vietnam Co., Ltd", "in_avl": 1,
                 "notes": "Công nghệ tiên tiến, chi phí bảo trì cao hơn — báo giá Q3/2025"},
                {"manufacturer": "GE Healthcare", "model": "CARESCAPE R860", "country": "USA",
                 "spec_match_pct": 87, "price_estimate": 1050000000, "price_source": "Web",
                 "support_tier": "Tier2", "local_partner": "GE Vietnam Representative", "in_avl": 0,
                 "notes": "Phụ tùng nhập khẩu, thời gian sửa chữa dài — list price từ website 2025"},
            ]
        },
    ]

    for data in mb_data:
        spec_ref = data["spec_ref"]
        # Check if MB already exists for this spec
        existing = frappe.db.get_value("IMM Market Benchmark", {"spec_ref": spec_ref}, "name")
        if existing:
            print(f"  MB exists for {spec_ref}: {existing}")
            # Update tech spec benchmark_ref
            frappe.db.set_value("IMM Tech Spec", spec_ref, {
                "benchmark_ref": existing,
                "candidate_count": len(data["candidates"]),
            })
            frappe.db.commit()
            continue

        mb = frappe.new_doc("IMM Market Benchmark")
        mb.spec_ref = spec_ref
        for c in data["candidates"]:
            mb.append("candidates", c)
        mb.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Created MB: {mb.name} for {spec_ref} — {mb.recommended_candidate}")

    # Verify
    mbs = frappe.db.sql("SELECT name, spec_ref, workflow_state FROM `tabIMM Market Benchmark`", as_dict=True)
    print(f"\nMarket Benchmarks ({len(mbs)}):")
    for mb in mbs:
        print(f"  {mb['name']} → spec_ref={mb['spec_ref']}")

    specs = frappe.db.sql("SELECT name, workflow_state, benchmark_ref, candidate_count FROM `tabIMM Tech Spec`", as_dict=True)
    print(f"\nTech Specs ({len(specs)}):")
    for ts in specs:
        print(f"  {ts['name']} state={ts['workflow_state']} benchmark_ref={ts['benchmark_ref']} candidates={ts['candidate_count']}")

    print("\nDone.")
