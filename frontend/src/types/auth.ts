export interface FrappeUser {
  name: string
  full_name: string
  email: string
  roles: string[]
}

export interface AuthSession {
  user: FrappeUser
  csrf_token: string
}

export interface LoginPayload {
  usr: string
  pwd: string
}

export interface LoginResponse {
  message: string
  home_page?: string
  full_name?: string
}
