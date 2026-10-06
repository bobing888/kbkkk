/**
 * Main Layout — 应用壳
 * M3 3.1: 玻璃导航栏 + <Outlet/>
 *
 * 玻璃导航栏：GlassCard + GlassSegmented
 * 底部占位安全区（iOS safe-area）
 */
import { Outlet, useLocation, Link } from 'react-router-dom'
import { GlassCard } from './ui/GlassCard'
import { GlassSegmented } from './ui/GlassSegmented'
import type { SegmentedOption } from './ui/GlassSegmented'

const NAV_OPTIONS: SegmentedOption<'home' | 'signals' | 'settings'>[] = [
  { value: 'home', label: 'K线' },
  { value: 'signals', label: '信号' },
  { value: 'settings', label: '设置' },
]

function getPathForNav(value: 'home' | 'signals' | 'settings'): string {
  return value === 'home' ? '/' : `/${value}`
}

function getNavFromPath(pathname: string): 'home' | 'signals' | 'settings' {
  if (pathname === '/' || pathname === '/home') return 'home'
  if (pathname.startsWith('/signals')) return 'signals'
  if (pathname.startsWith('/settings')) return 'settings'
  return 'home'
}

export function Layout() {
  const { pathname } = useLocation()
  const activeNav = getNavFromPath(pathname)

  return (
    <div className="min-h-screen bg-[var(--glass-bg-dark,#0d0e10)] flex flex-col">
      {/* 顶部玻璃导航栏 */}
      <nav
        data-testid="glass-navbar"
        className="sticky top-0 z-50 px-4 py-3"
      >
        <GlassCard padding="sm" className="max-w-2xl mx-auto">
          <div className="flex items-center gap-4">
            {/* Logo */}
            <div className="flex-shrink-0">
              <span className="text-base font-semibold text-[var(--accent,#f7931a)] tracking-tight">
                KBKKK
              </span>
            </div>

            {/* 导航 tabs — GlassSegmented */}
            <div className="flex-1 flex justify-center">
              <GlassSegmented
                options={NAV_OPTIONS}
                value={activeNav}
                onChange={(val) => {
                  const v = Array.isArray(val) ? val[0] : val
                  window.history.pushState({}, '', getPathForNav(v as 'home' | 'signals' | 'settings'))
                }}
                data-testid="nav-segmented"
              />
            </div>
          </div>
        </GlassCard>
      </nav>

      {/* 主内容区 */}
      <main className="flex-1 px-4 pb-6">
        <div className="max-w-2xl mx-auto">
          <Outlet />
        </div>
      </main>

      {/* 底部安全区 */}
      <div className="h-[env(safe-area-inset-bottom,0px)]" />
    </div>
  )
}
