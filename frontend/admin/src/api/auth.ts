const TOKEN_KEY = 'ai_cs_token'

export interface Staff {
  id: string
  username: string
  display_name: string
  wecom_userid: string | null
  is_active: boolean
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export async function login(username: string, password: string): Promise<void> {
  const r = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!r.ok) throw new Error('用户名或密码错误')
  const data: { access_token: string } = await r.json()
  setToken(data.access_token)
}

export async function getMe(): Promise<Staff> {
  const token = getToken()
  if (!token) throw new Error('未登录')
  const r = await fetch('/api/v1/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!r.ok) throw new Error('获取用户信息失败')
  return r.json()
}
