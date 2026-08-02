/**
 * 统一 HTTP 客户端
 *
 * fetchWithAuth     — 带 Bearer token 的 JSON 请求
 * fetchWithAuthForm — 带 Bearer token 的 multipart/form-data 请求（文件上传）
 *
 * token 从 localStorage 读取（由 auth.ts 的 setToken/clearToken 管理）。
 * 401 响应时自动清除 token（下次操作会跳转登录）。
 */

import { getToken } from './auth'

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken()
  const base: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}
  if (extra) {
    Object.assign(base, extra)
  }
  return base
}

export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = authHeaders({
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  })
  const r = await fetch(url, { ...options, headers })
  if (r.status === 401) {
    // token 失效，清除本地 token（页面重新加载会触发登录跳转）
    const { clearToken } = await import('./auth')
    clearToken()
  }
  return r
}

/**
 * multipart/form-data 上传专用（不设 Content-Type，浏览器自动添加 boundary）
 */
export async function fetchWithAuthForm(
  url: string,
  body: FormData
): Promise<Response> {
  const headers = authHeaders()
  const r = await fetch(url, { method: 'POST', headers, body })
  if (r.status === 401) {
    const { clearToken } = await import('./auth')
    clearToken()
  }
  return r
}
