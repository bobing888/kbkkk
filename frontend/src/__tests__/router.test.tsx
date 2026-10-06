/**
 * Router tests — react-router-dom v7 BrowserRouter routing
 * M3 3.1: 3 页面路由 /home /signals /settings + Layout 玻璃导航栏
 *
 * TDD 铁律：先红后绿
 * - test_router_renders_home_at_root
 * - test_router_navigates_to_signals
 * - test_router_navigates_to_settings
 * - test_router_layout_has_glass_navbar
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { router } from '../router'
import { Layout } from '../components/Layout'
import { HomePage } from '../pages/HomePage'
import { SignalsPage } from '../pages/SignalsPage'
import { SettingsPage } from '../pages/SettingsPage'

// ─── 用真实 router 测试 ──────────────────────────────────────────────

describe('Router — 3 页面路由配置', () => {
  it('根路径 / 渲染 HomePage', () => {
    const memRouter = createMemoryRouter(router.routes, { initialEntries: ['/'] })
    render(<RouterProvider router={memRouter} />)
    // HomePage 有 data-testid="home-page"
    expect(screen.getByTestId('home-page')).toBeInTheDocument()
  })

  it('导航到 /signals 渲染 SignalsPage', () => {
    const memRouter = createMemoryRouter(router.routes, { initialEntries: ['/signals'] })
    render(<RouterProvider router={memRouter} />)
    expect(screen.getByTestId('signals-page')).toBeInTheDocument()
  })

  it('导航到 /settings 渲染 SettingsPage', () => {
    const memRouter = createMemoryRouter(router.routes, { initialEntries: ['/settings'] })
    render(<RouterProvider router={memRouter} />)
    expect(screen.getByTestId('settings-page')).toBeInTheDocument()
  })

  it('Layout 有玻璃导航栏', () => {
    const routes = [
      { path: '/', Component: HomePage },
    ]
    const memRouter = createMemoryRouter([
      {
        path: '/',
        element: <Layout />,
        children: routes,
      },
    ], { initialEntries: ['/'] })
    render(<RouterProvider router={memRouter} />)
    // Layout 有 data-testid="glass-navbar"
    expect(screen.getByTestId('glass-navbar')).toBeInTheDocument()
  })
})
