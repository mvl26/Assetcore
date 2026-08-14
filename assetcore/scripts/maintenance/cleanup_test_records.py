"""Remove _Test fixtures that leak into UI (violates assetcore-test R-1)."""
import frappe


def run():
    # Drop _Test Model IMM06
    for m in frappe.get_all("IMM Device Model", filters={"model_name": ["like", "%_Test%"]}, fields=["name"]):
        try:
            frappe.delete_doc("IMM Device Model", m.name, force=True, ignore_permissions=True)
            print(f"Deleted Device Model {m.name}")
        except Exception as e:
            print(f"Cannot delete {m.name}: {e}")

    # Fix Drager → Dräger in model names
    for m in frappe.get_all("IMM Device Model", filters={"model_name": ["like", "%Drager%"]}, fields=["name", "model_name"]):
        new_name = m.model_name.replace("Drager", "Dräger")
        frappe.db.set_value("IMM Device Model", m.name, "model_name", new_name)
        print(f"Renamed {m.name} -> {new_name}")

    # AC Asset names
    for a in frappe.get_all("AC Asset", filters={"asset_name": ["like", "%Drager%"]}, fields=["name", "asset_name"]):
        new_name = a.asset_name.replace("Drager", "Dräger")
        frappe.db.set_value("AC Asset", a.name, "asset_name", new_name)
        print(f"Renamed asset {a.name} -> {new_name}")

    frappe.db.commit()
    print("DONE")
