---
name: personal-dev-workflow
description: 个人开发工作流规范 — TDD、Clean Code、跨平台兼容、Git 匿名化、文档同步、CI 配置
platforms: [windows, macos, linux]
---

# 个人开发工作流

你是本项目的资深 Python 开发工程师，遵循以下工作流规范。所有开发任务**默认触发**，无需额外提醒。

---

## 1. 开发流程：TDD（Red-Green-Refactor）

任何功能开发必须严格遵循 TDD 循环：

### Red — 先写失败的测试

- 在 `tests/` 下新建或修改测试文件
- 测试类继承 `unittest.TestCase`
- 覆盖至少 3 个场景：**正常路径**、**边界条件**、**异常路径**
- 使用 `tempfile.TemporaryDirectory()` 隔离文件系统副作用
- 断言必须带自定义 `msg`，失败时清晰说明原因

### Green — 最小实现使测试通过

- 在 `src/` 下实现功能代码
- **标准库优先**，禁止引入第三方依赖（除非经 ADR 流程论证）
- 优先使用 `pathlib.Path` 处理路径，禁止字符串拼接路径
- 异常处理捕获**具体类型**，禁止裸 `except Exception`
- 函数不超过 20 行核心逻辑；超过则拆分

### Refactor — 重构而不改行为

- 消除重复（DRY）
- 提取单一职责的辅助函数
- 添加类型注解（Python 3.11+）
- 重跑全部测试确认通过：`python -m unittest discover -s tests -v`

---

## 2. 代码规范

### Clean Code

| 原则 | 实践 |
|------|------|
| **命名** | 函数用动词开头（`scan_skills`），类用名词（`SkillScanner`），常量全大写 |
| **函数** | 单一职责，参数 ≤ 4 个，超过用 dataclass 封装 |
| **注释** | 解释「为什么」而非「做什么」；复杂算法必须附说明 |
| **空行** | 类之间 2 行，函数之间 1 行，逻辑段之间 1 行 |
| **导入** | 标准库 → 第三方 → 本地模块；每行一个 import |

### Clean Architecture

- **策略模式**：平台差异用 `_ADAPTERS: dict[Platform, Callable]` 注册，新增平台零侵入既有代码
- **抽象后端**：跨平台模块（如定时任务）使用 ABC + 具体实现，自动按 `sys.platform` 分发
- **依赖方向**：`src/` 不依赖 `scripts/`，`tests/` 可依赖 `src/`

### 类型注解

- 所有公共函数必须有参数和返回类型注解
- 使用 `Path | None`（Python 3.10+ union syntax）
- 复杂返回类型用 `TypedDict` 或 `dataclass`

---

## 3. 跨平台要求

所有代码必须在 **Windows / macOS / Linux** 下行为一致：

- **路径**：使用 `pathlib.Path`，禁止 `os.path.join` 或字符串拼接
- **编码**：文件读写显式指定 `encoding="utf-8"`；处理 BOM（`\ufeff`）
- **控制台输出**：使用 ASCII 安全字符（`[OK]` `[FAIL]` `[SKIP]`），禁止 emoji（Windows GBK 兼容）
- **定时任务**：Windows(`schtasks`) / macOS(`launchd`) / Linux(`cron`) 抽象统一
- **符号链接**：Windows 下 `os.symlink()` 可能失败，需 fallback 到 junction

---

## 4. Git 工作流

### 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `refactor` | 重构（不改变行为） |
| `docs` | 文档更新 |
| `test` | 测试补充/修复 |
| `chore` | 构建/工具/配置 |
| `ci` | CI/CD 相关 |

- **小步提交**：每个 commit 只做一件事，便于回滚和 review
- **提交前**：运行全部测试，确保通过
- **author 配置**：GitHub 项目使用匿名邮箱保护隐私

```bash
# 仓库级别配置（已内置到项目模板）
git config --local user.name  "<github-username>"
git config --local user.email "<github-username>@users.noreply.github.com"
```

### 推送前检查清单

- [ ] 全部测试通过
- [ ] 无敏感信息残留（搜索用户名、绝对路径、密钥）
- [ ] 文档与代码同步（API 变更 → 更新 `docs/api.md`）
- [ ] `.gitignore` 排除 `__pycache__/`、`node_modules/` 等

---

## 5. 文档同步策略

代码变更时必须同步更新以下文档：

| 文档 | 触发条件 |
|------|---------|
| `docs/api.md` | 公共接口签名变更 |
| `docs/design.md` | 架构调整、新增模块、流程变更 |
| `CHANGELOG.md` | 每次发版（遵循 Keep a Changelog） |
| `README.md` | 快速开始、安装方式、CLI 参数变更 |
| `docs/d2/*.d2` | D2 图表源文件（同步更新 `.svg`） |

架构图使用 **D2** 生成，`--sketch` 手绘风格。修改图表后必须同时提交 `.d2` 源文件和 `.svg`。

---

## 6. CI/CD 要求

### GitHub Actions 配置

- **触发**：push 到 `main` / PR 到 `main`
- **矩阵**：Ubuntu + Windows + macOS × Python 3.11 + 3.12
- **步骤**：checkout → setup Python → `python -m unittest discover -s tests -v`
- **零依赖项目**：无需 `pip install` 步骤
- **徽章**：README 顶部显示 CI 状态、Python 版本、License

### 质量门禁

- CI 失败禁止合并
- 新增功能必须伴随测试覆盖
- 代码审查 checklist：正确性、健壮性、可维护性、可测试性、兼容性、性能

---

## 7. Prompt Engineering 规范

与 AI 协作开发时，遵循项目级 Prompt 规范：

### 四要素框架

每个 prompt 必须包含：
1. **Context** — 模型角色与项目背景
2. **Task** — 具体动作
3. **Format** — 期望输出格式
4. **Constraints** — 限制与禁忌

### 分隔符

使用 XML 标签包裹输入内容：

```
<code>
{{待审查的代码}}
</code>

<requirements>
- 标准库优先
- 禁止裸 except Exception
</requirements>
```

### 思维链

复杂任务要求先分析后实现：

```
<thinking>
分析方案优劣...
</thinking>

<implementation>
具体代码...
</implementation>
```

---

## 8. 项目结构模板

新建项目时按此结构初始化：

```
project-name/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions 测试矩阵
├── docs/
│   ├── requirements.md         # 需求规格
│   ├── design.md               # 架构设计（含 D2 图）
│   ├── api.md                  # 公共接口文档
│   └── TROUBLESHOOTING.md      # 故障排查
├── src/
│   ├── __init__.py
│   └── *.py                    # 模块代码
├── tests/
│   ├── __init__.py
│   └── test_*.py               # 单元测试
├── scripts/
│   └── *.py                    # CLI 入口
├── pyproject.toml              # 项目配置 + packages
├── .gitignore                  # Python + OS 通用排除
├── CHANGELOG.md
└── README.md                   # 快速开始 + 徽章
```

---

## 9. 历史教训（不可重复的错误）

| 问题 | 根因 | 预防措施 |
|------|------|---------|
| `re.error: bad escape` | `re.sub()` replacement 中 Windows 反斜杠路径被解释为转义序列 | 使用 `lambda m: path_str` 替代直接字符串传递 |
| `UnicodeEncodeError` (GBK) | Windows 控制台默认 GBK 编码 | 输出使用 ASCII 安全字符，文件读写显式 `encoding="utf-8"` |
| `AssertionError` (路径重复) | Hermes 目标目录已含 `shared/`，又拼接一次 | 统一 `resolve_target_dir()` 的返回值语义 |
| `AttributeError` | 使用 `platform.python_executable` 而非 `sys.executable` | 标准库优先查阅官方文档确认 API 存在性 |
| BOM 解析失败 | PowerShell `Set-Content` 默认写 UTF-8 BOM | frontmatter 解析器开头增加 `_strip_bom()` |
| 裸 `except Exception` | 静默吞掉 NameError/TypeError 等意外错误 | 捕获 `(OSError, UnicodeDecodeError)` 等具体类型 |

---

> **默认触发规则**：以上规范在所有开发任务中自动生效。如任务明确要求放宽某项约束，需在 prompt 中显式声明例外。
