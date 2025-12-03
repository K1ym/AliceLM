/**
 * API 客户端
 * Axios 实例和拦截器配置
 */

import axios from "axios"

export const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
})

// 请求拦截器 - 添加认证 token
client.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// 响应拦截器 - 处理 401 未授权
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      // 排除登录和注册页面的 401
      const isAuthPage = window.location.pathname.includes("/login") || 
                         window.location.pathname.includes("/register")
      if (!isAuthPage) {
        localStorage.removeItem("token")
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  }
)

export default client
