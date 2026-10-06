/**
 * Router configuration — react-router-dom v7
 * M3 3.1: 3 页面 /home /signals /settings + Layout
 *
 * 使用 createBrowserRouter（react-router-dom v7 强制）
 * 根路由 element: <Layout /> + children: 3 routes
 */
import { createBrowserRouter } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { SignalsPage } from './pages/SignalsPage'
import { SettingsPage } from './pages/SettingsPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'home', element: <HomePage /> },
      { path: 'signals', element: <SignalsPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
])
