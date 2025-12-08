# Auth API

> 认证 API - 用户注册、登录、个人信息管理

**Base Path**: `/api/v1/auth`

---

## 概览

Auth API 处理用户认证，使用 JWT Token 进行身份验证。

---

## 端点列表

| 方法 | 端点 | 描述 | 认证 |
|------|------|------|------|
| POST | `/login` | 用户登录 | ❌ |
| POST | `/register` | 用户注册 | ❌ |
| GET | `/me` | 获取当前用户 | ✅ |
| POST | `/logout` | 登出 | ✅ |
| PUT | `/profile` | 更新个人信息 | ✅ |
| PUT | `/password` | 修改密码 | ✅ |

---

## POST /login

用户登录，获取 JWT Token。

### 请求

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

### 响应

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 错误响应

```json
{
  "detail": "邮箱或密码错误"
}
```

---

## POST /register

用户注册。

### 请求

```json
{
  "email": "newuser@example.com",
  "username": "新用户",
  "password": "password123"
}
```

### 响应

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 错误响应

```json
{
  "detail": "该邮箱已被注册"
}
```

---

## GET /me

获取当前用户信息。

### 请求头

```
Authorization: Bearer <token>
```

### 响应

```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "用户昵称",
  "tenant_id": 1,
  "created_at": "2024-12-01T10:00:00"
}
```

---

## POST /logout

登出（客户端应删除本地 Token）。

### 响应

```json
{
  "message": "已登出"
}
```

---

## PUT /profile

更新个人信息。

### 请求

```json
{
  "username": "新昵称"
}
```

### 响应

```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "新昵称",
  "tenant_id": 1,
  "created_at": "2024-12-01T10:00:00"
}
```

---

## PUT /password

修改密码。

### 请求

```json
{
  "current_password": "oldpassword",
  "new_password": "newpassword123"
}
```

### 响应

```json
{
  "message": "密码修改成功"
}
```

### 错误响应

```json
{
  "detail": "当前密码错误"
}
```

---

## 前端使用建议

### Token 存储

```typescript
// 登录后存储 Token
const login = async (email: string, password: string) => {
  const response = await authApi.login({ email, password });
  localStorage.setItem('token', response.access_token);
  localStorage.setItem('token_expires', Date.now() + response.expires_in * 1000);
};

// 检查 Token 是否过期
const isTokenValid = () => {
  const expires = localStorage.getItem('token_expires');
  return expires && Date.now() < parseInt(expires);
};
```

### 请求拦截器

```typescript
// Axios 拦截器
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 处理
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

## Token 说明

| 属性 | 值 |
|------|-----|
| 算法 | HS256 |
| 有效期 | 24 小时 |
| 刷新 | 过期后需重新登录 |

### Token Payload

```json
{
  "sub": "1",
  "exp": 1733400000,
  "iat": 1733313600
}
```

| 字段 | 说明 |
|------|------|
| sub | 用户 ID |
| exp | 过期时间（Unix 时间戳） |
| iat | 签发时间 |
