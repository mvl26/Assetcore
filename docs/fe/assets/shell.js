/* AssetCore Shell — dynamic per-persona sidebar via localStorage.
   Mỗi page set <meta name="module-id" content="..."> trong <head>;
   script này đọc localStorage.persona + meta module-id rồi build sidebar/topbar.
*/
(function () {
  'use strict';

  // ─── Module catalog (icon + label + relative href from /common, /00-XXX, etc.)
  // Path uses {p} placeholder which is replaced with the prefix to docs/fe root.
  var MODULES = {
    'qr-scan':            ['heroicons:qr-code',                  'Quét QR / Barcode',      '{p}/common/qr-scan.html'],
    'assets':             ['heroicons:cube',                     'Thiết bị y tế',          '{p}/00-master-data/assets-list.html'],
    'suppliers':          ['heroicons:truck',                    'Nhà cung cấp',           '{p}/00-master-data/suppliers-list.html'],
    'device-models':      ['heroicons:tag',                      'Dòng máy / model',       '{p}/00-master-data/device-models-list.html'],
    'locations':          ['heroicons:map-pin',                  'Vị trí & phòng ban',     '{p}/00-master-data/locations-list.html'],
    'service-contracts':  ['heroicons:document-text',            'Hợp đồng dịch vụ',       '{p}/00-master-data/service-contracts-list.html'],
    'asset-transfers':    ['heroicons:arrows-right-left',        'Điều chuyển thiết bị',   '{p}/00-master-data/asset-transfers-list.html'],
    'needs':              ['heroicons:clipboard-document-list',  'Đề xuất nhu cầu',        '{p}/01-needs/needs-list.html'],
    'plans':              ['heroicons:calendar-days',            'Kế hoạch mua sắm',       '{p}/01-needs/plans-list.html'],
    'tech-specs':         ['heroicons:document-chart-bar',       'Thông số kỹ thuật',      '{p}/02-tech-spec/tech-specs-list.html'],
    'vendor-eval':        ['heroicons:check-badge',              'Đánh giá NCC',           '{p}/03-procurement/vendor-evaluations-list.html'],
    'avl':                ['heroicons:trophy',                   'NCC được duyệt (AVL)',   '{p}/03-procurement/avl-list.html'],
    'decisions':          ['heroicons:hand-thumb-up',            'Quyết định mua sắm',     '{p}/03-procurement/decisions-list.html'],
    'purchases':          ['heroicons:shopping-cart',            'Đơn mua hàng (PO)',      '{p}/03-procurement/purchases-list.html'],
    'commissioning':      ['heroicons:wrench-screwdriver',       'Lắp đặt & nghiệm thu',   '{p}/04-commissioning/commissioning-list.html'],
    'documents':          ['heroicons:folder',                   'Hồ sơ thiết bị',         '{p}/05-document/documents-list.html'],
    'training':           ['heroicons:academic-cap',             'Chương trình đào tạo',   '{p}/06-training/programs-list.html'],
    'sessions':           ['heroicons:user-group',               'Buổi đào tạo',           '{p}/06-training/sessions-list.html'],
    'competencies':       ['heroicons:identification',           'Năng lực kỹ thuật viên', '{p}/06-training/competencies-list.html'],
    'pm':                 ['heroicons:calendar',                 'Bảo trì định kỳ (PM)',   '{p}/08-pm/pm-list.html'],
    'cm':                 ['heroicons:wrench',                   'Sửa chữa (CM)',          '{p}/09-repair/repair-list.html'],
    'firmware':           ['heroicons:cpu-chip',                 'Thay đổi firmware',      '{p}/09-repair/firmware-list.html'],
    'calibration':        ['heroicons:scale',                    'Hiệu chuẩn',             '{p}/11-calibration/calibration-list.html'],
    'incidents':          ['heroicons:exclamation-triangle',     'Sự cố thiết bị',         '{p}/12-incident/incidents-list.html'],
    'rca':                ['heroicons:magnifying-glass',         'Phân tích nguyên nhân',  '{p}/12-incident/rca-list.html'],
    'inventory':          ['heroicons:chart-pie',                'Tổng quan tồn kho',      '{p}/15-inventory/inventory-dashboard.html'],
    'spare-parts':        ['heroicons:cog-6-tooth',              'Danh mục phụ tùng',      '{p}/15-inventory/spare-parts-list.html'],
    'allocations':        ['heroicons:arrow-up-tray',            'Cấp phát phụ tùng',      '{p}/15-inventory/allocations-list.html'],
    'cycle-counts':       ['heroicons:chart-bar-square',         'Kiểm kê chu kỳ',         '{p}/15-inventory/cycle-counts-list.html'],
    'compliance-rules':   ['heroicons:document-check',           'Quy tắc tuân thủ',       '{p}/16-compliance/rules-list.html'],
    'findings':           ['heroicons:flag',                     'Vi phạm tuân thủ',       '{p}/16-compliance/findings-list.html'],
    'capa':               ['heroicons:shield-check',             'CAPA',                   '{p}/16-compliance/capa-list.html'],
    'audits':             ['heroicons:document-magnifying-glass','Audit nội bộ',           '{p}/16-compliance/audits-list.html'],
    'scorecard':          ['heroicons:trophy',                   'Scorecard tuân thủ',     '{p}/16-compliance/scorecard.html'],
    'mr':                 ['heroicons:user-circle',              'Management Review',      '{p}/16-compliance/mr-list.html'],
    'audit-trail':        ['heroicons:lock-closed',              'Nhật ký hệ thống',       '{p}/common/audit-trail.html'],
    'users':              ['heroicons:users',                    'Quản lý người dùng',     '{p}/common/users-list.html'],
    'roles':              ['heroicons:key',                      'Phân quyền role',        '{p}/common/role-admin.html'],
    'sla':                ['heroicons:clock',                    'Chính sách SLA',         '{p}/common/sla-list.html'],
  };

  // ─── 8 personas
  var PERSONAS = {
    'opsmgr':   { name: 'Trần Thị Mai',    title: 'Trưởng phòng VT-TTBYT', initials: 'TM', color: '#0E6FFF',
      groups: [
        ['TÀI SẢN', ['assets','device-models','suppliers','locations','service-contracts','asset-transfers']],
        ['MUA SẮM', ['needs','plans','tech-specs','vendor-eval','avl','decisions','purchases']],
        ['HỒ SƠ', ['documents']],
        ['BẢO TRÌ', ['pm','cm','calibration','incidents','rca']],
        ['TUÂN THỦ', ['compliance-rules','findings','capa','audits','scorecard','mr']],
        ['VẬN HÀNH', ['audit-trail','sla']],
      ]},
    'workshop': { name: 'Lê Quốc Hùng',    title: 'Trưởng xưởng kỹ thuật', initials: 'LH', color: '#0891B2',
      groups: [
        ['TÀI SẢN', ['assets','device-models','locations']],
        ['LẮP ĐẶT', ['commissioning']],
        ['ĐÀO TẠO & NĂNG LỰC', ['training','sessions','competencies']],
        ['BẢO TRÌ', ['pm','cm','firmware','calibration']],
        ['SỰ CỐ', ['incidents','rca']],
        ['KHO PHỤ TÙNG', ['spare-parts','allocations']],
      ]},
    'tech':     { name: 'Phạm Văn Đức',    title: 'Kỹ thuật viên',         initials: 'PĐ', color: '#16A34A',
      groups: [
        ['CÔNG VIỆC', ['qr-scan']],
        ['LỆNH CÔNG VIỆC', ['pm','cm','calibration']],
        ['SỰ CỐ', ['incidents']],
        ['PHỤ TÙNG', ['allocations']],
        ['TRA CỨU', ['assets']],
      ]},
    'clinical': { name: 'BS. Nguyễn Thị Lan', title: 'Trưởng khoa lâm sàng', initials: 'NL', color: '#7C3AED',
      groups: [
        ['NHU CẦU', ['needs']],
        ['BÁO CÁO SỰ CỐ', ['incidents']],
        ['NGHIỆM THU & BÀN GIAO', ['commissioning']],
      ]},
    'doc':      { name: 'Vũ Thị Hà',        title: 'Cán bộ hồ sơ',          initials: 'VH', color: '#475569',
      groups: [
        ['TÀI SẢN & NCC', ['assets','device-models','suppliers','service-contracts']],
        ['MUA SẮM & NGHIỆM THU', ['purchases','commissioning']],
        ['HỒ SƠ', ['documents']],
        ['TRA CỨU', ['audit-trail']],
      ]},
    'store':    { name: 'Đỗ Văn Tâm',       title: 'Thủ kho phụ tùng',      initials: 'ĐT', color: '#B45309',
      groups: [
        ['KHO PHỤ TÙNG', ['inventory','spare-parts','allocations','cycle-counts']],
        ['NHẬN HÀNG', ['purchases']],
      ]},
    'qa':       { name: 'Hoàng Minh Châu', title: 'Cán bộ QA',             initials: 'HC', color: '#DC2626',
      groups: [
        ['SỰ CỐ & RCA', ['incidents','rca']],
        ['HIỆU CHUẨN', ['calibration']],
        ['TUÂN THỦ', ['compliance-rules','findings','capa','audits','scorecard','mr']],
        ['TRA CỨU', ['assets','audit-trail']],
      ]},
    'admin':    { name: 'Ngô Hải Sơn',     title: 'Quản trị viên IT',      initials: 'NS', color: '#0F172A',
      groups: [
        ['NGƯỜI DÙNG & QUYỀN', ['users','roles']],
        ['DỮ LIỆU NỀN', ['assets','device-models','locations']],
        ['CẤU HÌNH', ['sla']],
        ['AUDIT', ['audit-trail']],
      ]},
  };

  var ORDER = ['opsmgr','workshop','tech','clinical','doc','store','qa','admin'];

  // ─── Helpers — pure DOM API, no innerHTML
  function el(tag, opts) {
    var n = document.createElement(tag);
    if (!opts) return n;
    if (opts.cls) n.className = opts.cls;
    if (opts.id) n.id = opts.id;
    if (opts.text) n.textContent = opts.text;
    if (opts.href) n.setAttribute('href', opts.href);
    if (opts.style) n.setAttribute('style', opts.style);
    if (opts.title) n.setAttribute('title', opts.title);
    return n;
  }

  function iconEl(name, size) {
    var s = size || 18;
    var i = document.createElement('iconify-icon');
    i.setAttribute('icon', name);
    i.setAttribute('style', 'font-size:' + s + 'px;vertical-align:-3px');
    return i;
  }

  function clearChildren(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  // Compute prefix from current path back to docs/fe root
  function getPrefix() {
    var path = window.location.pathname;
    // Count subdirectories under docs/fe to get relative ../ prefix
    var marker = '/docs/fe/';
    var idx = path.indexOf(marker);
    if (idx < 0) return '.';
    var rest = path.substring(idx + marker.length);
    // Count '/' in rest (excluding final file)
    var depth = rest.split('/').length - 1;
    if (depth <= 0) return '.';
    var parts = [];
    for (var i = 0; i < depth; i++) parts.push('..');
    return parts.join('/');
  }

  function currentPersona() {
    var p = localStorage.getItem('ac_persona');
    if (p && PERSONAS[p]) return p;
    return 'opsmgr';
  }

  function setPersona(p) {
    if (!PERSONAS[p]) return;
    localStorage.setItem('ac_persona', p);
    // Navigate to that persona's dashboard
    var prefix = getPrefix();
    window.location.href = prefix + '/common/dashboard-' + p + '.html';
  }
  window.acSetPersona = setPersona;

  function getModuleId() {
    var meta = document.querySelector('meta[name="module-id"]');
    return meta ? meta.getAttribute('content') : '';
  }

  // ─── Build sidebar nav
  function buildSidebar(persona, moduleId, prefix) {
    var p = PERSONAS[persona];
    var nav = document.querySelector('.sidebar nav');
    if (!nav) return;
    clearChildren(nav);

    // Dashboard link
    var dash = el('a', {
      cls: 'nav-item' + (moduleId === 'dashboard' ? ' active' : ''),
      href: prefix + '/common/dashboard-' + persona + '.html',
    });
    var icSpan = el('span', { cls: 'ic' });
    icSpan.appendChild(iconEl('heroicons:home'));
    var lblSpan = el('span', { cls: 'lbl', text: 'Bảng điều khiển' });
    dash.appendChild(icSpan);
    dash.appendChild(lblSpan);
    nav.appendChild(dash);

    // Group items
    p.groups.forEach(function (gr) {
      var label = gr[0];
      var mids = gr[1];
      var glabel = el('div', { cls: 'nav-group-label', text: label });
      nav.appendChild(glabel);
      mids.forEach(function (mid) {
        var m = MODULES[mid];
        if (!m) return;
        var iconName = m[0], modLabel = m[1], hrefTpl = m[2];
        var href = hrefTpl.replace('{p}', prefix);
        var a = el('a', {
          cls: 'nav-item' + (mid === moduleId ? ' active' : ''),
          href: href,
        });
        var ic = el('span', { cls: 'ic' });
        ic.appendChild(iconEl(iconName));
        var lb = el('span', { cls: 'lbl', text: modLabel });
        a.appendChild(ic);
        a.appendChild(lb);
        nav.appendChild(a);
      });
    });

    // Side head title
    var sideHead = document.querySelector('.sidebar .side-head span');
    if (sideHead) sideHead.textContent = p.title;
  }

  // ─── Build topbar persona pill + dropdown
  function buildPersonaPill(persona, prefix) {
    var p = PERSONAS[persona];
    var pill = document.querySelector('.persona-pill');
    if (!pill) return;
    clearChildren(pill);

    var meta = el('div', { cls: 'meta' });
    var b = el('b', { text: p.title });
    var span = el('span', { text: p.name });
    meta.appendChild(b);
    meta.appendChild(span);

    var avatar = el('div', {
      cls: 'avatar',
      style: 'background:' + p.color,
      text: p.initials,
    });

    var chev = el('span', { style: 'color:#fff;display:inline-flex' });
    chev.appendChild(iconEl('heroicons:chevron-down', 14));

    pill.appendChild(meta);
    pill.appendChild(avatar);
    pill.appendChild(chev);

    pill.onclick = function (e) {
      e.stopPropagation();
      var menu = document.getElementById('personaMenu');
      if (menu) menu.classList.toggle('show');
    };

    // Build dropdown menu
    var menu = document.getElementById('personaMenu');
    if (!menu) return;
    clearChildren(menu);

    var hdr = el('div', {
      style: 'padding:10px 14px;border-bottom:1px solid var(--color-neutral-300);' +
        'font-size:11px;font-weight:600;color:var(--color-neutral-600);' +
        'text-transform:uppercase;letter-spacing:.04em',
      text: 'Chọn vai trò',
    });
    menu.appendChild(hdr);

    ORDER.forEach(function (pid) {
      var per = PERSONAS[pid];
      var isCur = pid === persona;
      var row = el('a', {
        href: '#',
        style: 'display:flex;align-items:center;gap:10px;padding:10px 12px;' +
          'text-decoration:none;color:var(--color-neutral-900);' +
          'background:' + (isCur ? 'rgba(14,111,255,.12)' : 'transparent'),
      });
      row.onclick = function (e) {
        e.preventDefault();
        setPersona(pid);
      };
      var av = el('span', {
        style: 'width:30px;height:30px;border-radius:50%;background:' + per.color +
          ';color:#fff;display:grid;place-items:center;font-weight:700;font-size:12px',
        text: per.initials,
      });
      var pmeta = el('div', { style: 'flex:1;min-width:0' });
      var title = el('div', {
        style: 'font-size:13px;font-weight:600',
        text: per.title,
      });
      var nameDiv = el('div', {
        style: 'font-size:11px;color:var(--color-neutral-600)',
        text: per.name,
      });
      pmeta.appendChild(title);
      pmeta.appendChild(nameDiv);
      row.appendChild(av);
      row.appendChild(pmeta);
      if (isCur) {
        var check = el('span', { style: 'color:#16A34A;display:inline-flex' });
        check.appendChild(iconEl('heroicons:check', 14));
        row.appendChild(check);
      }
      menu.appendChild(row);
    });
  }

  // ─── Update home brand link
  function updateBrandLink(persona, prefix) {
    var brand = document.querySelector('.brand');
    if (brand) brand.setAttribute('href', prefix + '/common/dashboard-' + persona + '.html');
  }

  function init() {
    var persona = currentPersona();
    var moduleId = getModuleId();
    var prefix = getPrefix();
    buildSidebar(persona, moduleId, prefix);
    buildPersonaPill(persona, prefix);
    updateBrandLink(persona, prefix);

    // Close dropdown when clicking outside
    document.addEventListener('click', function () {
      var menu = document.getElementById('personaMenu');
      if (menu) menu.classList.remove('show');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
