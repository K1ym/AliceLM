/**
 * 认证 API
 */

import { client } from "./client"
import type { UserInfo } from "./types"

export const authApi = {
  login: (email: string, password: string) =>
    client.post("/auth/login", { email, password }),
  
  register: (email: string, password: string, username: string) =>
    client.post("/auth/register", { email, password, username }),
  
  me: () => client.get<UserInfo>("/auth/me"),
  
  logout: () => client.post("/auth/logout"),
  
  updateProfile: (data: { username?: string }) =>
    client.put<UserInfo>("/auth/profile", data),
  
  changePassword: (currentPassword: string, newPassword: string) =>
    client.put("/auth/password", { 
      current_password: currentPassword, 
      new_password: newPassword 
    }),
}
