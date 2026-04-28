# Before Coding Checklist

Run this checklist before writing any new feature code for AssetCore.

## 1. Requirement Confirmed

- [ ] The requirement is in `docs/sprints/` or confirmed in this conversation
- [ ] Module (IMM-XX) and actor identified
- [ ] Regulatory basis known (ISO clause / NĐ98 article), or explicitly N/A

## 2. Design First (Not UI First)

- [ ] Lifecycle event defined: what state does the asset transition to?
- [ ] DocType identified: which record captures this action?
- [ ] Workflow states mapped before writing any controller code
- [ ] No UI component started before backend contract is defined

## 3. No Core Modifications

- [ ] Confirmed: not modifying any ERPNext core DocType
- [ ] Using Custom Fields or new DocTypes only

## 4. Service Layer

- [ ] Business logic goes in `assetcore/services/` — NOT in controller or API
- [ ] Controller only: validate + fire service
- [ ] API only: parse input + call service + return `_ok`/`_err`

## 5. Audit Trail Planned

- [ ] Every state transition will create a Lifecycle Event record
- [ ] `track_changes = 1` on the DocType
- [ ] Approval/rejection requires documented actor + timestamp

## 6. Test Written First (TDD)

- [ ] At least one test case written before implementation
- [ ] Happy path and one failure case identified

If any box is unchecked, resolve it before coding.
