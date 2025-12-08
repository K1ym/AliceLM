# AliceLM Agent Guidelines

## Review guidelines

### 代码质量
- 检查是否有未处理的异常（裸 `except Exception`）
- 确保使用 `alice.errors` 中定义的错误类型
- 检查 async/await 是否正确使用

### 安全性
- 不要在日志中打印敏感信息（API Key、密码、token）
- 验证所有 API 端点都有认证中间件
- 检查 SQL 注入风险

### 架构规范
- 数据模型使用 `source_type` + `source_id`，不要用 `bvid`
- LLM 实例通过 `ControlPlane` 获取，不要直接实例化
- 配置从 `config/base/` 读取

### 测试要求
- 新增功能必须有对应测试
- 测试使用 `pytest.mark.asyncio` 标记异步测试
- Mock 外部依赖（LLM、网络请求）

### 命名规范
- 函数名：`snake_case`
- 类名：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`
- 文件名：`snake_case.py`

## Task guidelines

### 代码生成
- 遵循项目现有的代码风格
- 新增文件放在正确的目录结构下
- 添加类型注解

### 重构任务
- 保持向后兼容（除非明确说明是破坏性变更）
- 更新相关测试
- 更新文档
