# File Tree: assetcore

**Generated:** 4/24/2026, 8:47:03 AM
**Root Path:** `/home/hoangviet/frappe-bench/apps/assetcore`

```
├── 📁 .claude
│   ├── 📁 commands
│   │   ├── 📁 ba
│   │   │   ├── 📝 build-traceability-matrix.md
│   │   │   ├── 📝 draft-requirement.md
│   │   │   ├── 📝 review-gap-analysis.md
│   │   │   ├── 📝 write-acceptance-criteria.md
│   │   │   └── 📝 write-user-story.md
│   │   ├── 📁 dev
│   │   │   ├── 📝 build-workflow.md
│   │   │   ├── 📝 generate-api-contract.md
│   │   │   ├── 📝 implement-validation-rule.md
│   │   │   ├── 📝 scaffold-doctype.md
│   │   │   └── 📝 write-test-case.md
│   │   ├── 📁 pm
│   │   │   ├── 📝 backlog-prioritization.md
│   │   │   ├── 📝 risk-review.md
│   │   │   └── 📝 sprint-breakdown.md
│   │   └── 📁 qms
│   │       ├── 📝 build-audit-trail-check.md
│   │       ├── 📝 create-controlled-form.md
│   │       ├── 📝 draft-sop.md
│   │       └── 📝 map-qms-document.md
│   ├── 📁 hooks
│   │   ├── 📝 before-closing-task.md
│   │   ├── 📝 before-coding.md
│   │   ├── 📝 before-merging.md
│   │   └── 📝 before-writing-docs.md
│   ├── 📁 skills
│   │   ├── 📁 asset-lifecycle-designer
│   │   │   ├── 📝 SKILL.md
│   │   │   └── 📝 examples.md
│   │   ├── 📁 dashboard-spec-writer
│   │   │   ├── 📝 SKILL.md
│   │   │   └── 📝 examples.md
│   │   ├── 📁 erpnext-doctype-designer
│   │   │   ├── 📝 SKILL.md
│   │   │   └── 📝 examples.md
│   │   └── 📁 qms-mapper
│   │       ├── 📝 SKILL.md
│   │       └── 📝 examples.md
│   ├── 📝 CLAUDE.md
│   ├── ⚙️ settings.json
│   └── ⚙️ settings.local.json
├── 📁 assetcore
│   ├── 📁 .claude
│   │   └── ⚙️ settings.json
│   ├── 📁 api
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 auth.py
│   │   ├── 🐍 dashboard.py
│   │   ├── 🐍 depreciation.py
│   │   ├── 🐍 imm00.py
│   │   ├── 🐍 imm01.py
│   │   ├── 🐍 imm02.py
│   │   ├── 🐍 imm03.py
│   │   ├── 🐍 imm04.py
│   │   ├── 🐍 imm05.py
│   │   ├── 🐍 imm06.py
│   │   ├── 🐍 imm07.py
│   │   ├── 🐍 imm08.py
│   │   ├── 🐍 imm09.py
│   │   ├── 🐍 imm11.py
│   │   ├── 🐍 imm12.py
│   │   ├── 🐍 imm13.py
│   │   ├── 🐍 imm14.py
│   │   ├── 🐍 inventory.py
│   │   ├── 🐍 layout.py
│   │   └── 🐍 user_profile.py
│   ├── 📁 assetcore
│   │   ├── 📁 doctype
│   │   │   ├── 📁 ac_asset
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_asset.json
│   │   │   │   ├── 🐍 ac_asset.py
│   │   │   │   └── 🐍 test_ac_asset.py
│   │   │   ├── 📁 ac_asset_category
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_asset_category.json
│   │   │   │   ├── 🐍 ac_asset_category.py
│   │   │   │   └── 🐍 test_ac_asset_category.py
│   │   │   ├── 📁 ac_asset_downtime_log
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_asset_downtime_log.json
│   │   │   │   └── 🐍 ac_asset_downtime_log.py
│   │   │   ├── 📁 ac_authorized_technician
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_authorized_technician.json
│   │   │   │   ├── 🐍 ac_authorized_technician.py
│   │   │   │   └── 🐍 test_ac_authorized_technician.py
│   │   │   ├── 📁 ac_department
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_department.json
│   │   │   │   ├── 🐍 ac_department.py
│   │   │   │   └── 🐍 test_ac_department.py
│   │   │   ├── 📁 ac_location
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_location.json
│   │   │   │   ├── 🐍 ac_location.py
│   │   │   │   └── 🐍 test_ac_location.py
│   │   │   ├── 📁 ac_spare_part
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_spare_part.json
│   │   │   │   └── 🐍 ac_spare_part.py
│   │   │   ├── 📁 ac_spare_part_stock
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_spare_part_stock.json
│   │   │   │   └── 🐍 ac_spare_part_stock.py
│   │   │   ├── 📁 ac_stock_movement
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_stock_movement.json
│   │   │   │   └── 🐍 ac_stock_movement.py
│   │   │   ├── 📁 ac_stock_movement_item
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_stock_movement_item.json
│   │   │   │   └── 🐍 ac_stock_movement_item.py
│   │   │   ├── 📁 ac_supplier
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_supplier.json
│   │   │   │   ├── 🐍 ac_supplier.py
│   │   │   │   └── 🐍 test_ac_supplier.py
│   │   │   ├── 📁 ac_user_certification
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_user_certification.json
│   │   │   │   └── 🐍 ac_user_certification.py
│   │   │   ├── 📁 ac_user_profile
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_user_profile.json
│   │   │   │   └── 🐍 ac_user_profile.py
│   │   │   ├── 📁 ac_user_role
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_user_role.json
│   │   │   │   └── 🐍 ac_user_role.py
│   │   │   ├── 📁 ac_warehouse
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ ac_warehouse.json
│   │   │   │   └── 🐍 ac_warehouse.py
│   │   │   ├── 📁 archive_document_entry
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ archive_document_entry.json
│   │   │   │   └── 🐍 archive_document_entry.py
│   │   │   ├── 📁 asset_archive_record
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ asset_archive_record.json
│   │   │   │   └── 🐍 asset_archive_record.py
│   │   │   ├── 📁 asset_commissioning
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── 📄 asset_commissioning.js
│   │   │   │   ├── ⚙️ asset_commissioning.json
│   │   │   │   └── 🐍 asset_commissioning.py
│   │   │   ├── 📁 asset_document
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── 📄 asset_document.js
│   │   │   │   ├── ⚙️ asset_document.json
│   │   │   │   └── 🐍 asset_document.py
│   │   │   ├── 📁 asset_lifecycle_event
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ asset_lifecycle_event.json
│   │   │   │   ├── 🐍 asset_lifecycle_event.py
│   │   │   │   └── 🐍 test_asset_lifecycle_event.py
│   │   │   ├── 📁 asset_qa_non_conformance
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── 📄 asset_qa_non_conformance.js
│   │   │   │   ├── ⚙️ asset_qa_non_conformance.json
│   │   │   │   └── 🐍 asset_qa_non_conformance.py
│   │   │   ├── 📁 asset_repair
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ asset_repair.json
│   │   │   │   └── 🐍 asset_repair.py
│   │   │   ├── 📁 asset_transfer
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ asset_transfer.json
│   │   │   │   └── 🐍 asset_transfer.py
│   │   │   ├── 📁 commissioning_checklist
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ commissioning_checklist.json
│   │   │   │   └── 🐍 commissioning_checklist.py
│   │   │   ├── 📁 commissioning_document_record
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ commissioning_document_record.json
│   │   │   │   └── 🐍 commissioning_document_record.py
│   │   │   ├── 📁 daily_operation_log
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ daily_operation_log.json
│   │   │   │   └── 🐍 daily_operation_log.py
│   │   │   ├── 📁 decommission_checklist_item
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ decommission_checklist_item.json
│   │   │   │   └── 🐍 decommission_checklist_item.py
│   │   │   ├── 📁 decommission_request
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ decommission_request.json
│   │   │   │   └── 🐍 decommission_request.py
│   │   │   ├── 📁 document_request
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ document_request.json
│   │   │   │   └── 🐍 document_request.py
│   │   │   ├── 📁 expiry_alert_log
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ expiry_alert_log.json
│   │   │   │   └── 🐍 expiry_alert_log.py
│   │   │   ├── 📁 firmware_change_request
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ firmware_change_request.json
│   │   │   │   └── 🐍 firmware_change_request.py
│   │   │   ├── 📁 handover_record
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ handover_record.json
│   │   │   │   └── 🐍 handover_record.py
│   │   │   ├── 📁 imm_asset_calibration
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ imm_asset_calibration.json
│   │   │   │   └── 🐍 imm_asset_calibration.py
│   │   │   ├── 📁 imm_audit_trail
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ imm_audit_trail.json
│   │   │   │   ├── 🐍 imm_audit_trail.py
│   │   │   │   └── 🐍 test_imm_audit_trail.py
│   │   │   ├── 📁 imm_calibration_measurement
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ imm_calibration_measurement.json
│   │   │   │   └── 🐍 imm_calibration_measurement.py
│   │   │   ├── 📁 imm_calibration_schedule
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ imm_calibration_schedule.json
│   │   │   │   └── 🐍 imm_calibration_schedule.py
│   │   │   ├── 📁 imm_capa_record
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ imm_capa_record.json
│   │   │   │   ├── 🐍 imm_capa_record.py
│   │   │   │   └── 🐍 test_imm_capa_record.py
│   │   │   ├── 📁 imm_device_model
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ imm_device_model.json
│   │   │   │   ├── 🐍 imm_device_model.py
│   │   │   │   └── 🐍 test_imm_device_model.py
│   │   │   ├── 📁 imm_device_spare_part
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ imm_device_spare_part.json
│   │   │   │   ├── 🐍 imm_device_spare_part.py
│   │   │   │   └── 🐍 test_imm_device_spare_part.py
│   │   │   ├── 📁 imm_sla_policy
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ imm_sla_policy.json
│   │   │   │   ├── 🐍 imm_sla_policy.py
│   │   │   │   └── 🐍 test_imm_sla_policy.py
│   │   │   ├── 📁 incident_report
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ incident_report.json
│   │   │   │   ├── 🐍 incident_report.py
│   │   │   │   └── 🐍 test_incident_report.py
│   │   │   ├── 📁 needs_assessment
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── 📄 needs_assessment.js
│   │   │   │   ├── ⚙️ needs_assessment.json
│   │   │   │   ├── 🐍 needs_assessment.py
│   │   │   │   └── 🐍 test_needs_assessment.py
│   │   │   ├── 📁 pm_checklist_item
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ pm_checklist_item.json
│   │   │   │   └── 🐍 pm_checklist_item.py
│   │   │   ├── 📁 pm_checklist_result
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ pm_checklist_result.json
│   │   │   │   └── 🐍 pm_checklist_result.py
│   │   │   ├── 📁 pm_checklist_template
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ pm_checklist_template.json
│   │   │   │   └── 🐍 pm_checklist_template.py
│   │   │   ├── 📁 pm_schedule
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ pm_schedule.json
│   │   │   │   └── 🐍 pm_schedule.py
│   │   │   ├── 📁 pm_task_log
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ pm_task_log.json
│   │   │   │   └── 🐍 pm_task_log.py
│   │   │   ├── 📁 pm_work_order
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ pm_work_order.json
│   │   │   │   └── 🐍 pm_work_order.py
│   │   │   ├── 📁 procurement_plan
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ procurement_plan.json
│   │   │   │   └── 🐍 procurement_plan.py
│   │   │   ├── 📁 procurement_plan_item
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ procurement_plan_item.json
│   │   │   │   └── 🐍 procurement_plan_item.py
│   │   │   ├── 📁 purchase_order_request
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ purchase_order_request.json
│   │   │   │   └── 🐍 purchase_order_request.py
│   │   │   ├── 📁 repair_checklist
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ repair_checklist.json
│   │   │   │   └── 🐍 repair_checklist.py
│   │   │   ├── 📁 required_document_type
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ required_document_type.json
│   │   │   │   └── 🐍 required_document_type.py
│   │   │   ├── 📁 service_contract
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ service_contract.json
│   │   │   │   └── 🐍 service_contract.py
│   │   │   ├── 📁 service_contract_asset
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ service_contract_asset.json
│   │   │   │   └── 🐍 service_contract_asset.py
│   │   │   ├── 📁 spare_parts_used
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ spare_parts_used.json
│   │   │   │   └── 🐍 spare_parts_used.py
│   │   │   ├── 📁 technical_specification
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ technical_specification.json
│   │   │   │   └── 🐍 technical_specification.py
│   │   │   ├── 📁 training_session
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ training_session.json
│   │   │   │   └── 🐍 training_session.py
│   │   │   ├── 📁 training_trainee
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ training_trainee.json
│   │   │   │   └── 🐍 training_trainee.py
│   │   │   ├── 📁 vendor_evaluation
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ vendor_evaluation.json
│   │   │   │   └── 🐍 vendor_evaluation.py
│   │   │   ├── 📁 vendor_evaluation_item
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ vendor_evaluation_item.json
│   │   │   │   └── 🐍 vendor_evaluation_item.py
│   │   │   └── 🐍 __init__.py
│   │   ├── 📁 workflow
│   │   │   ├── ⚙️ ac_asset_lifecycle_workflow.json
│   │   │   ├── ⚙️ imm_04_workflow.json
│   │   │   └── ⚙️ imm_05_document_workflow.json
│   │   └── 🐍 __init__.py
│   ├── 📁 doctype
│   │   ├── 📁 archive_document_entry
│   │   ├── 📁 asset_archive_record
│   │   ├── 📁 daily_operation_log
│   │   ├── 📁 decommission_checklist_item
│   │   ├── 📁 decommission_request
│   │   ├── 📁 handover_record
│   │   ├── 📁 needs_assessment
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── ⚙️ needs_assessment.json
│   │   │   └── 🐍 needs_assessment.py
│   │   ├── 📁 procurement_plan
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── ⚙️ procurement_plan.json
│   │   │   └── 🐍 procurement_plan.py
│   │   ├── 📁 procurement_plan_item
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── ⚙️ procurement_plan_item.json
│   │   │   └── 🐍 procurement_plan_item.py
│   │   ├── 📁 purchase_order_request
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── ⚙️ purchase_order_request.json
│   │   │   └── 🐍 purchase_order_request.py
│   │   ├── 📁 training_session
│   │   └── 📁 training_trainee
│   ├── 📁 fixtures
│   │   ├── 🐍 __init__.py
│   │   ├── ⚙️ imm00_custom_fields.json
│   │   ├── ⚙️ imm_sla_policy.json
│   │   └── ⚙️ role.json
│   ├── 📁 imm_planning
│   │   ├── 📁 doctype
│   │   │   ├── 📁 technical_specification
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ technical_specification.json
│   │   │   │   └── 🐍 technical_specification.py
│   │   │   ├── 📁 vendor_evaluation
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   ├── ⚙️ vendor_evaluation.json
│   │   │   │   └── 🐍 vendor_evaluation.py
│   │   │   ├── 📁 vendor_evaluation_item
│   │   │   │   ├── 🐍 __init__.py
│   │   │   │   └── ⚙️ vendor_evaluation_item.json
│   │   │   └── 🐍 __init__.py
│   │   ├── 📁 fixtures
│   │   └── 🐍 __init__.py
│   ├── 📁 integrations
│   │   └── 🐍 __init__.py
│   ├── 📁 patches
│   │   ├── 📁 v3_0
│   │   │   ├── 🐍 001_migrate_from_v2.py
│   │   │   └── 🐍 __init__.py
│   │   └── 🐍 __init__.py
│   ├── 📁 reports
│   │   └── 🐍 __init__.py
│   ├── 📁 repositories
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 asset_repo.py
│   │   ├── 🐍 base.py
│   │   ├── 🐍 calibration_repo.py
│   │   ├── 🐍 commissioning_repo.py
│   │   ├── 🐍 document_repo.py
│   │   ├── 🐍 pm_repo.py
│   │   ├── 🐍 repair_repo.py
│   │   └── 🐍 user_profile_repo.py
│   ├── 📁 scripts
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 seed_inventory.py
│   │   └── 🐍 seed_pm_cm_data.py
│   ├── 📁 services
│   │   ├── 📁 shared
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 constants.py
│   │   │   ├── 🐍 errors.py
│   │   │   └── 🐍 permissions.py
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 auth_service.py
│   │   ├── 🐍 imm00.py
│   │   ├── 🐍 imm02.py
│   │   ├── 🐍 imm03.py
│   │   ├── 🐍 imm04.py
│   │   ├── 🐍 imm05.py
│   │   ├── 🐍 imm06.py
│   │   ├── 🐍 imm07.py
│   │   ├── 🐍 imm08.py
│   │   ├── 🐍 imm09.py
│   │   ├── 🐍 imm11.py
│   │   ├── 🐍 imm12.py
│   │   ├── 🐍 imm13.py
│   │   ├── 🐍 imm14.py
│   │   └── 🐍 inventory.py
│   ├── 📁 tests
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 check_capa.py
│   │   ├── 🐍 check_schema.py
│   │   ├── 🐍 debug_delete.py
│   │   ├── 🐍 hard_reset_assets.py
│   │   ├── 🐍 hard_reset_modules.py
│   │   ├── 🐍 inspect_meta.py
│   │   ├── 🐍 patch_uat_data.py
│   │   ├── 🐍 seed_imm04_uat_v2.py
│   │   ├── 🐍 seed_imm11_uat.py
│   │   ├── 🐍 seed_uat.py
│   │   ├── 🐍 test_imm00.py
│   │   ├── 🐍 uat_crud.py
│   │   ├── 🐍 uat_imm05.py
│   │   ├── 🐍 uat_imm08.py
│   │   ├── 🐍 uat_imm09.py
│   │   └── 🐍 uat_imm11.py
│   ├── 📁 utils
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 email.py
│   │   ├── 🐍 helpers.py
│   │   ├── 🐍 lifecycle.py
│   │   ├── 🐍 pagination.py
│   │   └── 🐍 response.py
│   ├── 📁 workflows
│   │   └── 🐍 __init__.py
│   ├── 📁 www
│   │   └── 🐍 __init__.py
│   ├── 🐍 __init__.py
│   ├── 🐍 api.py
│   ├── 🐍 hooks.py
│   ├── 📄 modules.txt
│   ├── 📄 patches.txt
│   ├── 🐍 permissions.py
│   ├── 🐍 tasks.py
│   └── 🐍 uat_test.py
├── 📁 docs
│   ├── 📁 WHO
│   │   ├── 📝 WHO - Computerized maintenance management system.md
│   │   ├── 📝 WHO - Decommissioning medical devices.md
│   │   ├── 📝 WHO - Introduction to medical equipment inventory management.md
│   │   ├── 📝 WHO - Inventory and maintenance 2025.md
│   │   ├── 📝 WHO - Medical device donations considerations for solicitation and provision.md
│   │   ├── 📝 WHO - Medical equipment maintenance programme overview.md
│   │   ├── 📝 WHO - Needs assessment for medical devices.md
│   │   └── 📝 WHO - Procurement process resource guide.md
│   ├── 📁 architecture
│   │   ├── 🌐 AssetCore_Wave1_BA_Analysis.html
│   │   └── 📝 AssetCore_Wave1_Module_Analysis.md
│   ├── 📁 archive
│   │   ├── 📁 architecture
│   │   │   ├── 📝 01_PM_Technical_Architecture.md
│   │   │   ├── 📝 02_Design_Review_Report.md
│   │   │   ├── 📝 AssetCore_BA_Analysis.md
│   │   │   ├── 📝 Huong_dan_Claude_Code_IT.md
│   │   │   ├── 📝 IMM-04_Dashboard_UI_Design.md
│   │   │   ├── 📝 IMM-04_ERD_Logic.md
│   │   │   ├── 📝 IMM-04_ERPNext_Mapping_Strategy.md
│   │   │   ├── 📝 IMM-04_Event_Model.md
│   │   │   ├── 📝 IMM-04_Form_UI_Design.md
│   │   │   ├── 📝 IMM-04_Hardened_Review_Report.md
│   │   │   ├── 📝 IMM-04_Permission_Matrix.md
│   │   │   ├── 📝 IMM-04_Screen_Map.md
│   │   │   ├── 📝 IMM-04_UI_Action_Design.md
│   │   │   ├── 📝 IMM-04_UI_Architecture.md
│   │   │   ├── 📝 IMM-04_UI_Backend_Integration.md
│   │   │   ├── 📝 IMM-04_UI_UX_Expert_Review.md
│   │   │   ├── 📝 IMM-04_UI_Wireframe_Prototype.md
│   │   │   ├── 📝 IMM-04_Validation_Rules.md
│   │   │   ├── 📝 Master_List_QMS.md
│   │   │   └── 📝 QA_Reply_ND1.md
│   │   ├── 📁 ba
│   │   │   ├── 📝 IMM-04_Scope_Analysis.md
│   │   │   └── 📝 SOP_ALL.md
│   │   ├── 📁 compliance
│   │   │   ├── 📝 01_Asset_Commissioning_System_Rules.md
│   │   │   ├── 📝 IMM-04_Go_NoGo_Memo.md
│   │   │   ├── 📝 IMM-04_Hardened_Design_Summary.md
│   │   │   ├── 📝 IMM-04_Issue_Triage.md
│   │   │   ├── 📝 IMM-04_Master_UAT_Package.md
│   │   │   ├── 📝 IMM-04_QMS_Audit_Report.md
│   │   │   ├── 📝 IMM-04_QMS_Checklist_Audit.md
│   │   │   └── 📝 IMM-04_UAT_Entry_Criteria.md
│   │   ├── 📁 data-model
│   │   │   ├── 📝 01_Asset_Reception_DocType.md
│   │   │   ├── 📝 02_Maintenance_Work_Order_DocType.md
│   │   │   ├── 📝 IMM-04_DocType_Design.md
│   │   │   └── 📝 doctypes.md
│   │   ├── 📁 product
│   │   │   ├── 📝 IMM-04_Acceptance_Package.md
│   │   │   ├── 📝 IMM-04_Dashboard_KPI_Alerts.md
│   │   │   ├── 📝 IMM-04_Installation_and_Initial_Inspection.md
│   │   │   └── 📝 IMM-04_Master_Deliverable.md
│   │   ├── 📁 root
│   │   │   ├── 📝 IMM-05_Readiness_Audit.md
│   │   │   ├── 📝 IMM-05_Stakeholder_Decisions.md
│   │   │   ├── 📝 UAT_Integrated_IMM04_05.md
│   │   │   └── 📝 UI_READINESS_AUDIT.md
│   │   ├── 📁 sprints
│   │   │   ├── 📝 IMM-04_Build_Plan.md
│   │   │   ├── 📝 IMM-04_CRP_Script.md
│   │   │   ├── 📝 IMM-04_Configuration_Guide.md
│   │   │   ├── 📝 IMM-04_Master_Test_Data.md
│   │   │   ├── 📝 IMM-04_Sandbox_Round1.md
│   │   │   ├── 📝 IMM-04_Simulation_And_Test_Dataset.md
│   │   │   ├── 📝 IMM-04_Simulation_Log.md
│   │   │   ├── 📝 IMM-04_Source_Code.md
│   │   │   ├── 📝 IMM-04_Test_Suite.md
│   │   │   ├── 📝 IMM-04_Traceability_Matrix.md
│   │   │   └── 📝 IMM-04_UAT_Script.md
│   │   └── 📁 workflows
│   │       ├── 📝 01_Asset_Reception_and_Commissioning.md
│   │       ├── 📝 02_Maintenance_Work_Order_Workflow.md
│   │       ├── 📝 IMM-04_State_Machine.md
│   │       └── 📝 IMM-04_Workflow_States.md
│   ├── 📁 assetcore-bootstrap
│   │   ├── 📝 AssetCore_Production_Readiness_Analysis.md
│   │   ├── 📝 CLAUDE.md
│   │   ├── 📝 Ho_so_kien_truc_IMMIS.md
│   │   ├── 📝 MASTER_PROMPT_CLAUDE_CODE.md
│   │   ├── 📝 README.md
│   │   ├── 📝 WHO_Architecture_Gap_Analysis.md
│   │   ├── 📝 data-dictionary.md
│   │   ├── 📝 role-permission-matrix.md
│   │   └── 📝 workflow-map.md
│   ├── 📁 imm-00
│   │   ├── 📝 IMM-00_API_Interface.md
│   │   ├── 📝 IMM-00_Functional_Specs.md
│   │   ├── 📝 IMM-00_Inventory_Design.md
│   │   ├── 📝 IMM-00_Module_Overview.md
│   │   ├── 📝 IMM-00_Setup_Guide.md
│   │   ├── 📝 IMM-00_Technical_Design.md
│   │   └── 📝 IMM-00_UI_UX_Guide.md
│   ├── 📁 imm-01
│   │   ├── 📝 IMM-01_API_Interface.md
│   │   ├── 📝 IMM-01_Functional_Specs.md
│   │   ├── 📝 IMM-01_Module_Overview.md
│   │   ├── 📝 IMM-01_Technical_Design.md
│   │   ├── 📝 IMM-01_UAT_Script.md
│   │   └── 📝 IMM-01_UI_UX_Guide.md
│   ├── 📁 imm-02
│   │   ├── 📝 IMM-02_API_Interface.md
│   │   ├── 📝 IMM-02_Functional_Specs.md
│   │   ├── 📝 IMM-02_Module_Overview.md
│   │   ├── 📝 IMM-02_Technical_Design.md
│   │   ├── 📝 IMM-02_UAT_Script.md
│   │   └── 📝 IMM-02_UI_UX_Guide.md
│   ├── 📁 imm-03
│   │   ├── 📝 IMM-03_API_Interface.md
│   │   ├── 📝 IMM-03_Functional_Specs.md
│   │   ├── 📝 IMM-03_Module_Overview.md
│   │   ├── 📝 IMM-03_Technical_Design.md
│   │   ├── 📝 IMM-03_UAT_Script.md
│   │   └── 📝 IMM-03_UI_UX_Guide.md
│   ├── 📁 imm-04
│   │   ├── 📝 IMM-04_API_Interface.md
│   │   ├── 📝 IMM-04_Functional_Specs.md
│   │   ├── 📝 IMM-04_Module_Overview.md
│   │   ├── 📝 IMM-04_Technical_Design.md
│   │   ├── 📝 IMM-04_UAT_Script.md
│   │   ├── 📝 IMM-04_UAT_Script_v2.md
│   │   └── 📝 IMM-04_UI_UX_Guide.md
│   ├── 📁 imm-05
│   │   ├── 📝 IMM-05_API_Interface.md
│   │   ├── 📝 IMM-05_Functional_Specs.md
│   │   ├── 📝 IMM-05_Module_Overview.md
│   │   ├── 📝 IMM-05_Technical_Design.md
│   │   ├── 📝 IMM-05_UAT_Script.md
│   │   └── 📝 IMM-05_UI_UX_Guide.md
│   ├── 📁 imm-06
│   │   ├── 📝 IMM-06_API_Interface.md
│   │   ├── 📝 IMM-06_Functional_Specs.md
│   │   ├── 📝 IMM-06_Module_Overview.md
│   │   ├── 📝 IMM-06_Technical_Design.md
│   │   ├── 📝 IMM-06_UAT_Script.md
│   │   └── 📝 IMM-06_UI_UX_Guide.md
│   ├── 📁 imm-07
│   │   ├── 📝 IMM-07_API_Interface.md
│   │   ├── 📝 IMM-07_Functional_Specs.md
│   │   ├── 📝 IMM-07_Module_Overview.md
│   │   ├── 📝 IMM-07_Technical_Design.md
│   │   ├── 📝 IMM-07_UAT_Script.md
│   │   └── 📝 IMM-07_UI_UX_Guide.md
│   ├── 📁 imm-08
│   │   ├── 📝 IMM-08_API_Interface.md
│   │   ├── 📝 IMM-08_Functional_Specs.md
│   │   ├── 📝 IMM-08_Module_Overview.md
│   │   ├── 📝 IMM-08_Technical_Design.md
│   │   ├── 📝 IMM-08_UAT_Script.md
│   │   └── 📝 IMM-08_UI_UX_Guide.md
│   ├── 📁 imm-09
│   │   ├── 📝 IMM-09_API_Interface.md
│   │   ├── 📝 IMM-09_Functional_Specs.md
│   │   ├── 📝 IMM-09_Module_Overview.md
│   │   ├── 📝 IMM-09_Technical_Design.md
│   │   ├── 📝 IMM-09_UAT_Script.md
│   │   └── 📝 IMM-09_UI_UX_Guide.md
│   ├── 📁 imm-11
│   │   ├── 📝 IMM-11_API_Interface.md
│   │   ├── 📝 IMM-11_Functional_Specs.md
│   │   ├── 📝 IMM-11_Module_Overview.md
│   │   ├── 📝 IMM-11_Technical_Design.md
│   │   ├── 📝 IMM-11_UAT_Script.md
│   │   └── 📝 IMM-11_UI_UX_Guide.md
│   ├── 📁 imm-12
│   │   ├── 📝 IMM-12_API_Interface.md
│   │   ├── 📝 IMM-12_Functional_Specs.md
│   │   ├── 📝 IMM-12_Module_Overview.md
│   │   ├── 📝 IMM-12_Technical_Design.md
│   │   ├── 📝 IMM-12_UAT_Script.md
│   │   └── 📝 IMM-12_UI_UX_Guide.md
│   ├── 📁 imm-13
│   │   ├── 📝 IMM-13_API_Interface.md
│   │   ├── 📝 IMM-13_Functional_Specs.md
│   │   ├── 📝 IMM-13_Module_Overview.md
│   │   ├── 📝 IMM-13_Technical_Design.md
│   │   ├── 📝 IMM-13_UAT_Script.md
│   │   └── 📝 IMM-13_UI_UX_Guide.md
│   ├── 📁 imm-14
│   │   ├── 📝 IMM-14_API_Interface.md
│   │   ├── 📝 IMM-14_Functional_Specs.md
│   │   ├── 📝 IMM-14_Module_Overview.md
│   │   ├── 📝 IMM-14_Technical_Design.md
│   │   ├── 📝 IMM-14_UAT_Script.md
│   │   └── 📝 IMM-14_UI_UX_Guide.md
│   ├── 📁 res
│   │   ├── 📝 3Tier_Developer_Guide_2026-04-20.md
│   │   ├── 📝 Architecture_3Tier_Refactor_2026-04-20.md
│   │   ├── 📝 AssetCore_DocTypes_Audit_2026-04-19.md
│   │   ├── 📝 Auth_Account_Design_2026-04-20.md
│   │   ├── 📝 BE_Readiness_Audit_2026-04-18.md
│   │   ├── 📝 Frontend_Router_Navigation_Map.md
│   │   ├── 📝 IMM-00_Entity_Coverage_Analysis.md
│   │   ├── 📝 IMM-00_UAT_Gap_Analysis.md
│   │   ├── 📝 IMM-00_v3_Compatibility_Analysis.md
│   │   ├── 📝 Module_Business_Flows_2026-04-19.md
│   │   ├── 📝 Notification_Setup_Guide.md
│   │   ├── 📝 Wave1_Foundation_Readiness_2026-04-19.md
│   │   └── 📝 Wave1_Review_2026-04-19.md
│   ├── 📁 wave2
│   │   ├── 📝 IMM-01_02_03_BA_Business_Analysis.md
│   │   ├── 📝 IMM-01_02_03_ERPNext_Mapping_Strategy.md
│   │   ├── 📝 IMM-01_02_03_Final_Sanity_Check_and_Patch.md
│   │   ├── 📝 IMM-01_02_03_Technical_Design.md
│   │   ├── 📝 Sync_State_Final_Wave2_Phase1.md
│   │   ├── 📝 Sync_State_Step1.md
│   │   └── 📝 Sync_State_Step2.md
│   ├── 📝 AssetCore_DocType_Architecture.md
│   └── 📝 ERPNext_Core_Analysis_AssetCore_Inheritance.md
├── 📁 frontend
│   ├── 📁 .claude
│   │   └── ⚙️ settings.local.json
│   ├── 📁 src
│   │   ├── 📁 api
│   │   │   ├── 📄 auth.ts
│   │   │   ├── 📄 axios.ts
│   │   │   ├── 📄 helpers.ts
│   │   │   ├── 📄 imm00.ts
│   │   │   ├── 📄 imm01.ts
│   │   │   ├── 📄 imm02.ts
│   │   │   ├── 📄 imm03.ts
│   │   │   ├── 📄 imm04.ts
│   │   │   ├── 📄 imm05.ts
│   │   │   ├── 📄 imm06.ts
│   │   │   ├── 📄 imm08.ts
│   │   │   ├── 📄 imm09.ts
│   │   │   ├── 📄 imm11.ts
│   │   │   ├── 📄 imm12.ts
│   │   │   ├── 📄 inventory.ts
│   │   │   ├── 📄 layout.ts
│   │   │   └── 📄 userProfile.ts
│   │   ├── 📁 assets
│   │   │   └── 🎨 main.css
│   │   ├── 📁 components
│   │   │   ├── 📁 asset
│   │   │   │   └── 📄 AssetDowntimeWidget.vue
│   │   │   ├── 📁 common
│   │   │   │   ├── 📄 AppHeader.vue
│   │   │   │   ├── 📄 AppLayout.vue
│   │   │   │   ├── 📄 AppSidebar.vue
│   │   │   │   ├── 📄 AppTopBar.vue
│   │   │   │   ├── 📄 ApprovalModal.vue
│   │   │   │   ├── 📄 BaseModal.vue
│   │   │   │   ├── 📄 BasePagination.vue
│   │   │   │   ├── 📄 LinkInfoCard.vue
│   │   │   │   ├── 📄 LinkSearch.vue
│   │   │   │   ├── 📄 LoadingSpinner.vue
│   │   │   │   ├── 📄 RouteErrorBoundary.vue
│   │   │   │   ├── 📄 SkeletonLoader.vue
│   │   │   │   ├── 📄 SmartSelect.vue
│   │   │   │   ├── 📄 StatusBadge.vue
│   │   │   │   └── 📄 VendorScoringTable.vue
│   │   │   ├── 📁 imm04
│   │   │   │   ├── 📄 AssetDashboard.vue
│   │   │   │   ├── 📄 BaselineTestTable.vue
│   │   │   │   ├── 📄 CommissioningForm.vue
│   │   │   │   ├── 📄 DocumentChecklist.vue
│   │   │   │   ├── 📄 QRLabel.vue
│   │   │   │   └── 📄 WorkflowActions.vue
│   │   │   └── 📁 imm05
│   │   │       ├── 📄 DocumentRequestModal.vue
│   │   │       ├── 📄 DocumentRow.vue
│   │   │       └── 📄 ExemptModal.vue
│   │   ├── 📁 composables
│   │   │   ├── 📄 useAssets.ts
│   │   │   ├── 📄 useDashboard.ts
│   │   │   ├── 📄 usePagination.ts
│   │   │   ├── 📄 usePermissions.ts
│   │   │   ├── 📄 useSidebar.ts
│   │   │   ├── 📄 useToast.ts
│   │   │   └── 📄 useWorkflow.ts
│   │   ├── 📁 constants
│   │   │   ├── 📄 labels.ts
│   │   │   └── 📄 roles.ts
│   │   ├── 📁 directives
│   │   │   └── 📄 permission.ts
│   │   ├── 📁 layouts
│   │   │   ├── 📄 AuthLayout.vue
│   │   │   └── 📄 DefaultLayout.vue
│   │   ├── 📁 router
│   │   │   └── 📄 index.ts
│   │   ├── 📁 services
│   │   │   ├── 📄 frappeResource.ts
│   │   │   └── 📄 http.ts
│   │   ├── 📁 stores
│   │   │   ├── 📄 auth.ts
│   │   │   ├── 📄 commissioning.ts
│   │   │   ├── 📄 imm00.ts
│   │   │   ├── 📄 imm01.ts
│   │   │   ├── 📄 imm02.ts
│   │   │   ├── 📄 imm03.ts
│   │   │   ├── 📄 imm05Store.ts
│   │   │   ├── 📄 imm06.ts
│   │   │   ├── 📄 imm08.ts
│   │   │   ├── 📄 imm09.ts
│   │   │   └── 📄 useMasterDataStore.ts
│   │   ├── 📁 types
│   │   │   ├── 📄 auth.ts
│   │   │   ├── 📄 common.ts
│   │   │   ├── 📄 imm00.ts
│   │   │   ├── 📄 imm04.ts
│   │   │   ├── 📄 imm05.ts
│   │   │   ├── 📄 imm08.ts
│   │   │   ├── 📄 imm09.ts
│   │   │   └── 📄 inventory.ts
│   │   ├── 📁 utils
│   │   │   ├── 📄 docUtils.ts
│   │   │   └── 📄 labels.ts
│   │   ├── 📁 views
│   │   │   ├── 📄 AssetCreateView.vue
│   │   │   ├── 📄 AssetDetailView.vue
│   │   │   ├── 📄 AssetEditView.vue
│   │   │   ├── 📄 AssetListView.vue
│   │   │   ├── 📄 AssetTransferCreateView.vue
│   │   │   ├── 📄 AssetTransferDetailView.vue
│   │   │   ├── 📄 AssetTransferListView.vue
│   │   │   ├── 📄 AuditTrailListView.vue
│   │   │   ├── 📄 CAPADetailView.vue
│   │   │   ├── 📄 CAPAListView.vue
│   │   │   ├── 📄 CMChecklistView.vue
│   │   │   ├── 📄 CMCreateView.vue
│   │   │   ├── 📄 CMDashboardView.vue
│   │   │   ├── 📄 CMDiagnoseView.vue
│   │   │   ├── 📄 CMMttrView.vue
│   │   │   ├── 📄 CMPartsView.vue
│   │   │   ├── 📄 CMWorkOrderDetailView.vue
│   │   │   ├── 📄 CMWorkOrderListView.vue
│   │   │   ├── 📄 CalibrationCreateView.vue
│   │   │   ├── 📄 CalibrationDashboard.vue
│   │   │   ├── 📄 CalibrationDetailView.vue
│   │   │   ├── 📄 CalibrationListView.vue
│   │   │   ├── 📄 CalibrationScheduleListView.vue
│   │   │   ├── 📄 ChangePasswordView.vue
│   │   │   ├── 📄 CommissioningCreateView.vue
│   │   │   ├── 📄 CommissioningDetailView.vue
│   │   │   ├── 📄 CommissioningListView.vue
│   │   │   ├── 📄 CommissioningNCView.vue
│   │   │   ├── 📄 CommissioningTimelineView.vue
│   │   │   ├── 📄 DailyLogCreateView.vue
│   │   │   ├── 📄 DailyOperationDashboard.vue
│   │   │   ├── 📄 DashboardView.vue
│   │   │   ├── 📄 DepreciationView.vue
│   │   │   ├── 📄 DeviceModelFormView.vue
│   │   │   ├── 📄 DeviceModelListView.vue
│   │   │   ├── 📄 DocumentCreateView.vue
│   │   │   ├── 📄 DocumentDetailView.vue
│   │   │   ├── 📄 DocumentManagement.vue
│   │   │   ├── 📄 DocumentRequestListView.vue
│   │   │   ├── 📄 FirmwareCrListView.vue
│   │   │   ├── 📄 HandoverCreateView.vue
│   │   │   ├── 📄 HandoverDetailView.vue
│   │   │   ├── 📄 HandoverListView.vue
│   │   │   ├── 📄 ImmisHubView.vue
│   │   │   ├── 📄 IncidentCreateView.vue
│   │   │   ├── 📄 IncidentDetailView.vue
│   │   │   ├── 📄 IncidentListView.vue
│   │   │   ├── 📄 InventoryDashboardView.vue
│   │   │   ├── 📄 LoginView.vue
│   │   │   ├── 📄 NeedsAssessmentCreateView.vue
│   │   │   ├── 📄 NeedsAssessmentDetailView.vue
│   │   │   ├── 📄 NeedsAssessmentListView.vue
│   │   │   ├── 📄 NotFoundView.vue
│   │   │   ├── 📄 PMCalendarView.vue
│   │   │   ├── 📄 PMDashboardView.vue
│   │   │   ├── 📄 PMWorkOrderCreateView.vue
│   │   │   ├── 📄 PMWorkOrderDetailView.vue
│   │   │   ├── 📄 PMWorkOrderListView.vue
│   │   │   ├── 📄 PORCreateView.vue
│   │   │   ├── 📄 PORDetailView.vue
│   │   │   ├── 📄 PORListView.vue
│   │   │   ├── 📄 PlanningDashboardView.vue
│   │   │   ├── 📄 PmScheduleListView.vue
│   │   │   ├── 📄 PmTemplateListView.vue
│   │   │   ├── 📄 ProcurementPlanCreateView.vue
│   │   │   ├── 📄 ProcurementPlanDetailView.vue
│   │   │   ├── 📄 ProcurementPlanListView.vue
│   │   │   ├── 📄 ProfileView.vue
│   │   │   ├── 📄 ReferenceDataView.vue
│   │   │   ├── 📄 RegisterView.vue
│   │   │   ├── 📄 ServiceContractCreateView.vue
│   │   │   ├── 📄 ServiceContractDetailView.vue
│   │   │   ├── 📄 ServiceContractListView.vue
│   │   │   ├── 📄 SlaPolicyListView.vue
│   │   │   ├── 📄 SparePartDetailView.vue
│   │   │   ├── 📄 SparePartListView.vue
│   │   │   ├── 📄 StockLevelView.vue
│   │   │   ├── 📄 StockMovementCreateView.vue
│   │   │   ├── 📄 StockMovementDetailView.vue
│   │   │   ├── 📄 StockMovementListView.vue
│   │   │   ├── 📄 SupplierFormView.vue
│   │   │   ├── 📄 SupplierListView.vue
│   │   │   ├── 📄 TechnicalSpecCreateView.vue
│   │   │   ├── 📄 TechnicalSpecDetailView.vue
│   │   │   ├── 📄 TechnicalSpecListView.vue
│   │   │   ├── 📄 UnauthorizedView.vue
│   │   │   ├── 📄 UserProfileFormView.vue
│   │   │   ├── 📄 UserProfileListView.vue
│   │   │   ├── 📄 VendorEvaluationCreateView.vue
│   │   │   ├── 📄 VendorEvaluationDetailView.vue
│   │   │   ├── 📄 VendorEvaluationListView.vue
│   │   │   └── 📄 WarehouseListView.vue
│   │   ├── 📄 App.vue
│   │   ├── 📄 main.ts
│   │   └── 📄 vite-env.d.ts
│   ├── 🌐 index.html
│   ├── ⚙️ package-lock.json
│   ├── ⚙️ package.json
│   ├── 📄 postcss.config.js
│   ├── 📄 tailwind.config.js
│   ├── ⚙️ tsconfig.json
│   ├── ⚙️ tsconfig.node.json
│   └── 📄 vite.config.ts
├── 📁 scripts
│   └── 🐍 seed_pm_cm_data.py
├── ⚙️ .gitignore
├── 📝 CLAUDE.md
├── 📝 README.md
├── 📄 requirements.txt
└── 🐍 setup.py
```

---
*Generated by FileTree Pro Extension*