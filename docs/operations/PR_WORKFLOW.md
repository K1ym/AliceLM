# PR 工作流指南

## 开发流程

```bash
# 1. 从 main 创建功能分支
git checkout main
git checkout -b feature/功能名称

# 2. 开发并提交
git add .
git commit -m "feat: 功能描述"

# 3. 推送分支
git push origin feature/功能名称

# 4. 在 GitHub 创建 PR
# 5. 在 PR 评论中输入 @codex review 触发 review
```

## Codex Review 使用

1. 创建 PR 后，在评论中输入：
   ```
   @codex review
   ```

2. Codex 会回复 👀 表示开始 review

3. Review 完成后会留下评论，和人类 reviewer 一样

### 特殊指令

```
@codex review for security      # 重点检查安全问题
@codex review for performance   # 重点检查性能
@codex fix this                 # 让 Codex 自动修复
```

## 分支命名规范

| 类型 | 前缀 | 示例 |
|------|------|------|
| 新功能 | `feature/` | `feature/multi-source` |
| Bug 修复 | `fix/` | `fix/download-error` |
| 重构 | `refactor/` | `refactor/api-schema` |

## Review 规则配置

项目根目录的 `AGENTS.md` 定义了 Codex review 的规则。

