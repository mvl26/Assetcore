// Copyright (c) 2026, AssetCore Team and contributors
// IMM-04 Dashboard — Installation & Commissioning

frappe.pages["imm04-dashboard"].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "IMM-04 — Dashboard Lắp đặt Thiết bị",
		single_column: true
	});

	// Mount HTML template
	$(wrapper).find(".layout-main-section").html(frappe.render_template("imm04_dashboard", {}));

	const dash = new IMM04Dashboard(wrapper, page);
	dash.init();
};

// ──────────────────────────────────────────────
// STATE CONFIG
// ──────────────────────────────────────────────

const STATE_BADGE = {
	"Draft_Reception":    { label: "Draft",          cls: "badge-secondary" },
	"Pending_Doc_Verify": { label: "Chờ hồ sơ",      cls: "badge-info" },
	"To_Be_Installed":    { label: "Sẵn sàng lắp",   cls: "badge-primary" },
	"Installing":         { label: "Đang lắp",        cls: "badge-warning" },
	"Identification":     { label: "Định danh",       cls: "badge-warning" },
	"Initial_Inspection": { label: "Kiểm tra",        cls: "badge-warning" },
	"Non_Conformance":    { label: "Sự cố NC",        cls: "badge-danger" },
	"Clinical_Hold":      { label: "Clinical Hold",   cls: "badge-danger" },
	"Re_Inspection":      { label: "Tái kiểm",        cls: "badge-warning" },
	"Clinical_Release":   { label: "Đã phát hành",    cls: "badge-success" },
	"Return_To_Vendor":   { label: "Trả hãng",        cls: "badge-dark" }
};

const PAGE_SIZE = 20;

// ──────────────────────────────────────────────
// DASHBOARD CLASS
// ──────────────────────────────────────────────

class IMM04Dashboard {

	constructor(wrapper, page) {
		this.$w = $(wrapper);
		this.page = page;
		this.current_page = 0;
		this.filters = {};
	}

	init() {
		this._bind_events();
		this.load_kpis();
		this.load_list();
		this.load_nc_alerts();
	}

	// ── KPI CARDS ──────────────────────────────

	load_kpis() {
		frappe.call({
			method: "assetcore.api.get_dashboard_stats",
			callback: (r) => {
				if (!r.message) return;
				const d = r.message;

				this._set_kpi("kpi-pending", d.pending_count ?? "—");
				this._set_kpi("kpi-hold", d.hold_count ?? "—");
				this._set_kpi("kpi-nc-open", d.open_nc_count ?? "—");
				this._set_kpi("kpi-released", d.released_this_month ?? "—");
				this._set_kpi("kpi-overdue", d.overdue_sla ?? "—");

				// Highlight nếu có vấn đề
				if ((d.hold_count ?? 0) > 0) {
					this.$w.find("#kpi-hold").addClass("kpi-alert-pulse");
				}
				if ((d.open_nc_count ?? 0) > 0) {
					this.$w.find("#kpi-nc-open").addClass("kpi-alert-pulse");
				}
			}
		});
	}

	_set_kpi(id, value) {
		this.$w.find(`#${id} .kpi-value`).text(value);
	}

	// ── COMMISSIONING LIST ─────────────────────

	load_list() {
		const filters = this._build_filters();

		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Asset Commissioning",
				fields: [
					"name", "master_item", "vendor", "clinical_dept",
					"expected_installation_date", "workflow_state",
					"vendor_serial_no", "final_asset", "modified"
				],
				filters: filters,
				limit_start: this.current_page * PAGE_SIZE,
				limit_page_length: PAGE_SIZE,
				order_by: "modified desc"
			},
			callback: (r) => {
				this._render_list(r.message || []);
			}
		});
	}

	_build_filters() {
		const f = [];
		const state = this.$w.find("#filter-state").val();
		const dept  = this.$w.find("#filter-dept").val();
		const from  = this.$w.find("#filter-date-from").val();
		const to    = this.$w.find("#filter-date-to").val();

		if (state) f.push(["workflow_state", "=", state]);
		if (dept)  f.push(["clinical_dept", "like", `%${dept}%`]);
		if (from)  f.push(["expected_installation_date", ">=", from]);
		if (to)    f.push(["expected_installation_date", "<=", to]);

		return f;
	}

	_render_list(rows) {
		const tbody = this.$w.find("#commissioning-list");

		if (!rows.length) {
			tbody.html(`<tr><td colspan="9" class="text-center text-muted py-3">
				Không có dữ liệu phù hợp.
			</td></tr>`);
			return;
		}

		const html = rows.map(r => {
			const badge = STATE_BADGE[r.workflow_state] || { label: r.workflow_state, cls: "badge-secondary" };
			const date  = r.expected_installation_date
				? frappe.datetime.str_to_user(r.expected_installation_date) : "—";
			const asset_link = r.final_asset
				? `<a href="/app/asset/${r.final_asset}" target="_blank">${r.final_asset}</a>`
				: `<span class="text-muted">—</span>`;

			return `<tr class="comm-row" data-name="${r.name}">
				<td><a href="/app/asset-commissioning/${r.name}">${r.name}</a></td>
				<td>${r.master_item || "—"}</td>
				<td>${r.vendor || "—"}</td>
				<td>${r.clinical_dept || "—"}</td>
				<td>${date}</td>
				<td><span class="badge ${badge.cls}">${badge.label}</span></td>
				<td><code>${r.vendor_serial_no || "—"}</code></td>
				<td>${asset_link}</td>
				<td>
					<a href="/app/asset-commissioning/${r.name}"
						class="btn btn-xs btn-default">Xem</a>
				</td>
			</tr>`;
		}).join("");

		tbody.html(html);

		// Phân trang
		this.$w.find("#page-info").text(`Trang ${this.current_page + 1}`);
		this.$w.find("#btn-prev-page").prop("disabled", this.current_page === 0);
	}

	// ── NC ALERTS ─────────────────────────────

	load_nc_alerts() {
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Asset QA Non Conformance",
				fields: ["name", "ref_commissioning", "nc_type", "resolution_status", "modified"],
				filters: [["resolution_status", "=", "Open"], ["docstatus", "!=", 2]],
				limit_page_length: 10,
				order_by: "modified asc"
			},
			callback: (r) => {
				const ncs = r.message || [];
				if (!ncs.length) {
					this.$w.find("#nc-alert-panel").hide();
					return;
				}

				this.$w.find("#nc-alert-panel").show();
				const html = ncs.map(nc => `
					<div class="nc-alert-row">
						<span class="badge badge-danger">${nc.nc_type}</span>
						<a href="/app/asset-qa-non-conformance/${nc.name}">${nc.name}</a>
						<span class="text-muted mx-2">→</span>
						<a href="/app/asset-commissioning/${nc.ref_commissioning}">
							${nc.ref_commissioning}
						</a>
						<span class="nc-age text-muted ml-auto">
							${frappe.datetime.prettyDate(nc.modified)}
						</span>
					</div>
				`).join("");

				this.$w.find("#nc-alert-list").html(html);
			}
		});
	}

	// ── EVENTS ────────────────────────────────

	_bind_events() {
		// Tạo phiếu mới
		this.$w.find("#btn-new-commissioning").on("click", () => {
			frappe.new_doc("Asset Commissioning");
		});

		// Làm mới
		this.$w.find("#btn-refresh-dashboard").on("click", () => {
			this.current_page = 0;
			this.load_kpis();
			this.load_list();
			this.load_nc_alerts();
		});

		// Áp dụng filter
		this.$w.find("#btn-apply-filter").on("click", () => {
			this.current_page = 0;
			this.load_list();
		});

		// Phân trang
		this.$w.find("#btn-prev-page").on("click", () => {
			if (this.current_page > 0) {
				this.current_page--;
				this.load_list();
			}
		});

		this.$w.find("#btn-next-page").on("click", () => {
			this.current_page++;
			this.load_list();
		});

		// Enter trong filter dept
		this.$w.find("#filter-dept").on("keydown", (e) => {
			if (e.key === "Enter") {
				this.current_page = 0;
				this.load_list();
			}
		});
	}
}
