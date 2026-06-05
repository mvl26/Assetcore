// Shared vue-router mock — ROOT-CAUSE fix cho test-isolation pollution xuyên-file.
//
// VẤN ĐỀ GỐC (vong-17 ĐỎ, flake): nhiều file test hoist-mock `vue-router` với
// SHAPE useRoute KHÁC NHAU trong khi cùng static-import 1 SFC dùng chung
// (CMWorkOrderListView dùng useRoute().query, CMWorkOrderDetailView dùng
// useRouter().push). Vitest pool (forks) tái dùng worker → khi đổi thứ tự file
// (shuffle / scheduling khác mỗi vòng), SFC cache bind vào factory mock của FILE
// KHÁC đã "thắng" registry-race. Nếu factory thắng trả `useRoute: () => ({query:{}})`
// TĨNH (vd cmSlaClockStop, chỉ cần useRouter), thì file victim
// (cmListDrilldown set route.query.status) đọc query rỗng ⇒ assert fail HOẶC
// route undefined ⇒ crash `route.query`. Hướng leak đổi mỗi vòng → flake không
// xác định, "xanh isolation / đỏ full-suite".
//
// FIX: MỌI file dùng CHUNG factory này (full-shape: useRoute + useRouter +
// RouterLink). Dù factory của file nào "thắng" race, nó luôn ĐỒNG NHẤT và đọc
// route-state từ `globalThis` — TỒN TẠI XUYÊN bản-sao-module (isolate: true cấp
// mỗi file 1 copy module, nhưng globalThis là 1 instance/worker). → test set
// query qua setRouteQuery(), factory nào chạy cũng đọc cùng state ⇒ hết "mock
// nào thắng" → deterministic, hết pollution.
//
// KHÔNG phải Core Doc change — thuần test-harness defect (FE vitest isolation).
import { h } from 'vue'
import type { Slots } from 'vue'
import { vi } from 'vitest'
import type { Mock } from 'vitest'

type RouteQuery = Record<string, string>

// Store route-state trên globalThis để bất biến qua bản-sao-module giữa các file
// trong cùng worker (isolate duplicate module nhưng KHÔNG duplicate globalThis).
const G = globalThis as unknown as {
  __AC_ROUTE_QUERY__?: RouteQuery
  __AC_ROUTER_PUSH__?: Mock
}

/** Reset route-state về rỗng + push-spy mới — gọi trong beforeEach mỗi test. */
export function resetRouteMock(): void {
  G.__AC_ROUTE_QUERY__ = {}
  G.__AC_ROUTER_PUSH__ = vi.fn()
}

/** Đặt route.query mà view sẽ đọc (drill-down từ dashboard). */
export function setRouteQuery(q: RouteQuery): void {
  G.__AC_ROUTE_QUERY__ = { ...q }
}

/** Truy spy push() (vi.fn thật) để assert toHaveBeenCalledWith điều hướng. */
export function routerPushSpy(): Mock {
  if (!G.__AC_ROUTER_PUSH__) G.__AC_ROUTER_PUSH__ = vi.fn()
  return G.__AC_ROUTER_PUSH__
}

function serializeTo(to: unknown): string {
  if (typeof to === 'string') return to
  const t = (to ?? {}) as { path?: string; query?: RouteQuery }
  const path = t.path ?? ''
  const q = t.query ?? {}
  const qs = Object.entries(q).map(([k, v]) => `${k}=${String(v)}`).join('&')
  return qs ? `${path}?${qs}` : path
}

// RouterLink stub: serialize :to={path,query} → <a :href> (giống RouterLink thật)
// để test assert được href drill-target.
const RouterLinkStub = {
  name: 'RouterLink',
  props: { to: { type: [String, Object], default: '' } },
  setup(props: { to: unknown }, { slots }: { slots: Slots }) {
    return () => h('a', { href: serializeTo(props.to) }, slots.default ? slots.default() : [])
  },
}

/**
 * Factory dùng trong vi.mock('vue-router', vueRouterMockFactory).
 * Full-shape: useRoute (query live từ globalThis), useRouter (push spy),
 * RouterLink (serialize href). ĐỒNG NHẤT mọi file → race vô hại.
 */
export function vueRouterMockFactory() {
  return {
    useRoute: () => ({
      get query() { return G.__AC_ROUTE_QUERY__ ?? {} },
      params: {},
      path: '/',
    }),
    useRouter: () => ({ push: routerPushSpy() }),
    RouterLink: RouterLinkStub,
  }
}
