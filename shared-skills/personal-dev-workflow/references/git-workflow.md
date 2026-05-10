# Git 工作流指南

## 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

| 类型 | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(scheduler): add Linux cron backend` |
| `fix` | Bug 修复 | `fix(models): handle UTF-8 BOM in frontmatter` |
| `refactor` | 重构 | `refactor(adapter): extract strategy pattern` |
| `docs` | 文档 | `docs(api): add scanner module docs` |
| `test` | 测试 | `test(installer): add force mode coverage` |
| `chore` | 杂项 | `chore(gitignore): add node_modules` |
| `ci` | CI/CD | `ci: add multi-platform test matrix` |

### Subject 规则

- 不超过 50 个字符
- 使用祈使语气（"add" 而非 "added"）
- 首字母小写（专有名词除外）
- 末尾不加句号

### Body 规则

- 每行不超过 72 个字符
- 解释「为什么」和「做什么」
- 列出关键变更点（bullet list）

## 小步提交

每个 commit 只做一件事：

```bash
# ❌ 错误：混合多个变更
git commit -m "feat + fix docs"

# ✅ 正确：拆分提交
git add src/models.py tests/test_models.py
git commit -m "feat(models): add frontmatter list parsing"

git add docs/api.md
git commit -m "docs(api): document parse_frontmatter list support"
```

## 匿名邮箱配置

### 项目级别（推荐）

```bash
cd project-root
git config --local user.name  "xfbingshan"
git config --local user.email "xfbingshan@users.noreply.github.com"
```

### 全局级别（所有仓库默认）

```bash
git config --global user.name  "xfbingshan"
git config --global user.email "xfbingshan@users.noreply.github.com"
```

### 验证

```bash
git config --local --list | grep user
git log --format="%an <%ae>" -1
```

## 推送前检查

```bash
# 1. 测试
python -m unittest discover -s tests -v

# 2. 敏感信息扫描
grep -r "<USERNAME>\|<USERNAME>\|<EMAIL>" --include="*.py" --include="*.md" --include="*.toml" .

# 3. 文档同步检查
# - API 变更 → docs/api.md
# - 架构变更 → docs/design.md
# - 发版 → CHANGELOG.md

# 4. 提交

git push
```

## 历史重写（仅必要时）

如果历史 commit 暴露了敏感信息：

```bash
# 替换全部历史 author
$env:FILTER_BRANCH_SQUELCH_WARNING=1
git filter-branch --env-filter '
    export GIT_AUTHOR_NAME="xfbingshan"
    export GIT_AUTHOR_EMAIL="xfbingshan@users.noreply.github.com"
    export GIT_COMMITTER_NAME="xfbingshan"
    export GIT_COMMITTER_EMAIL="xfbingshan@users.noreply.github.com"
' --tag-name-filter cat -- --all

# 清理备份
git update-ref -d refs/original/refs/heads/master
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```
