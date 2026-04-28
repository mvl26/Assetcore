# Before Writing Documentation Checklist

Run before creating or updating any document in `docs/`.

## 1. Document Classification

Confirm which type this is:

- **BA doc** (`docs/requirements/`): requirement, user story, acceptance criteria
- **Sprint doc** (`docs/sprints/`): UAT script, sprint plan, RTM
- **Architecture doc** (`docs/architecture/`): system design, data model, integration
- **QMS doc** (`docs/qms/`): SOP (PR), Work Instruction (WI), Form spec (BM)

## 2. QMS Documents (Controlled)

If this is a PR, WI, or BM document:

- [ ] Document number assigned (e.g., PR-05-01)
- [ ] Version set to 1.0 (or incremented if revision)
- [ ] Owner and approver roles listed
- [ ] Regulatory basis cited (ISO clause / NĐ98 article)
- [ ] Revision history table included

## 3. Accuracy

- [ ] All DocType names match actual Frappe DocTypes
- [ ] All API endpoints verified against current `assetcore/api/` code
- [ ] All workflow states match current Frappe Workflow definitions
- [ ] Role names match exactly: CMMS Admin, Biomed Engineer, HTM Technician, Workshop Head, Tổ HC-QLCL

## 4. CLAUDE.md

- [ ] If a new architectural pattern is documented, update `CLAUDE.md` section 17
- [ ] If new domain terms introduced, add to `CLAUDE.md` section 16
- [ ] Keep CLAUDE.md under 200 lines — move detail to `docs/`
