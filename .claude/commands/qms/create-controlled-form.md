---
description: Create a controlled form (BM document) specification for AssetCore
---

Create a **controlled form (Biểu mẫu / BM)** for: `$ARGUMENTS`

**Output:**

**1. Form Header**

```text
Document Number: BM-<module>-<sequence>
Form Title: <Vietnamese>
Version: 1.0
Related SOP: PR-<module>-<sequence>
```

**2. Field Specification**

For each field on the form:

| # | Field Label (VI) | Field Type | Required | Validation Rule | Maps to DocType Field |
| --- | --- | --- | --- | --- | --- |
| 1 | ... | Text/Date/Select/Signature | Yes/No | VR-XX | <fieldname> |

**3. Signature Block**

Who must sign, in what order (creator → reviewer → approver).

**4. System Implementation**

Map this form to the AssetCore DocType that captures the same data:

- Which DocType represents this form?
- Which fields match exactly?
- What is auto-filled by the system vs. manually entered?
- Is a PDF printout required? (if yes, note the print format needed)

**5. Revision Control**

How is this form revised? Who approves the revision? What triggers a new version?
