# Shared Skills Bridge — Prompt Engineering 规范

> 参考 Anthropic Prompt Engineering 最佳实践，结合本项目架构与开发历史制定。

---

## 1. 核心原则

### 1.1 明确性优先（Clarity First）

每一个 prompt 必须包含 **Context → Task → Format → Constraints** 四要素，缺一不可。

| 要素 | 说明 | 本项目示例 |
|------|------|-----------|
| **Context** | 模型当前角色与背景 | "你是 `shared-skills-bridge` 的代码审查者，熟悉 TDD 和标准库优先原则" |
| **Task** | 具体要完成的动作 | "为 `bidirectional.py` 的 `_discover_additions` 函数编写单元测试" |
| **Format** | 期望的输出格式 | "输出 Python 代码块，包含测试类和方法，使用 `unittest` 框架" |
| **Constraints** | 限制与禁忌 | "禁止使用第三方库，仅使用 `pathlib` 和 `tempfile`" |

### 1.2 分隔符规范（Delimiters）

使用 XML 标签包裹输入内容，避免指令与数据混淆。

```
<context>
你正在 review 以下代码模块。
</context>

<code>
{{待审查的代码}}
</code>

<requirements>
- 使用 Python 3.11+ 类型注解
- 异常处理必须捕获具体类型，禁止裸 `except Exception`
- 遵循 SRP：每个函数不超过 20 行核心逻辑
</requirements>

<task>
指出代码中的 3 个可改进点，按优先级排序，并为最高优先级的问题提供重构后的代码。
</task>
```

### 1.3 思维链（Chain of Thought）

复杂任务必须要求模型**先思考、后输出**，使用 `<thinking>` 标签。

```
<task>
为 `adapter.py` 新增一个平台适配器（Platform.CURSOR）。
</task>

<instructions>
1. 首先在 <thinking> 中分析：Cursor 平台与 Kimi/Hermes 的语法差异
2. 然后在 <implementation> 中输出具体代码
3. 最后在 <tests> 中输出对应的单元测试
</instructions>
```

### 1.4 少样本学习（Few-shot）

为重复性任务提供 1-3 个标准示例，锚定输出风格。

---

## 2. 模块级 Prompt 模板

### 2.1 模型层（`src/models.py`）

**适用场景**：新增数据模型、解析器扩展、frontmatter 字段支持。

```
<role>
你是 `shared-skills-bridge` 的数据模型设计师。
项目约束：Python 3.11+，零第三方依赖，使用 `pathlib.Path` 处理路径。
</role>

<existing_code>
{{当前 models.py 中 parse_frontmatter 及相关辅助函数}}
</existing_code>

<task>
扩展 frontmatter 解析器，支持新的 YAML 标量类型：多行折叠字符串 `>`。
</task>

<format>
- 输出形式：一个完整的 `_parse_xxx` 辅助函数 + 在 `parse_frontmatter` 中的调用点
- 必须包含 docstring，说明输入输出和边界行为
- 必须处理 BOM 前缀和空内容
</format>

<example>
输入：
---
description: >
  This is a long description
  that spans multiple lines
  but should be folded into one.
---

输出：
{"description": "This is a long description that spans multiple lines but should be folded into one."}
</example>

<thinking>
请分析 `>` 与 `|` 的区别：
- `|` 保留换行（当前已实现）
- `>` 将换行替换为空格（需要新实现）

然后输出实现代码。
</thinking>
```

### 2.2 扫描器（`src/scanner.py`）

**适用场景**：目录扫描规则调整、新增验证逻辑、性能优化。

```
<role>
你是文件系统扫描模块的开发者。所有路径操作必须使用 `pathlib.Path`。
</role>

<current_behavior>
`scan_skills(source_dir)` 扫描 `source_dir` 的直接子目录，
如果子目录包含 `SKILL.md` 且 frontmatter 有 `name` 和 `description`，则生成 Skill 对象。
</current_behavior>

<task>
新增支持：允许 `.skill/` 后缀的隐藏目录（如 `git-commit-guide.skill/`）也被识别为合法 skill 包。
</task>

<constraints>
- 不要破坏现有行为（普通目录仍需支持）
- 扫描结果仍需按 `name` 排序
- 如果同时存在 `my-skill/` 和 `my-skill.skill/`，优先取前者并记录 warning
</constraints>

<output>
先输出 <analysis> 说明你的设计决策，
然后输出 <code> 包含修改后的 `scan_skills` 函数和新增测试用例。
</output>
```

### 2.3 适配器（`src/adapter.py`）

**适用场景**：新增平台适配器、扩展现有适配规则、语法映射调整。

```
<role>
你是跨平台 skill 内容适配专家。当前已支持 Hermes（原生）和 Kimi（清理语法）。
适配规则通过 `_ADAPTERS: dict[Platform, Callable]` 策略模式注册。
</role>

<current_adapters>
Hermes: 原样透传
Kimi:   替换 ${HERMES_SKILL_DIR} → 绝对路径
        删除 ${HERMES_SESSION_ID}
        替换 !`cmd` → [shell: cmd]
</current_adapters>

<task>
为 `Platform.CURSOR` 实现适配器 `_adapt_for_cursor`。
已知 Cursor 平台与 Kimi 工具集高度相似，但使用 `${CURSOR_SKILL_DIR}` 作为路径变量。
</task>

<requirements>
1. 遵循 OCP：仅注册新适配器，不修改 `adapt_skill_content()` 的路由逻辑
2. 复用 Kimi 适配器的现有逻辑（shell 占位符替换等）
3. 处理 `${CURSOR_SKILL_DIR}` → 绝对路径的替换
4. 在 <thinking> 中说明你的复用策略（继承？组合？还是直接调用？）
</requirements>

<output_format>
- <thinking>: 设计分析
- <code>: 完整的 `_adapt_for_cursor` 函数 + 注册代码 + 测试用例
</output_format>
```

### 2.4 安装器（`src/installer.py`）

**适用场景**：安装逻辑扩展、差异检测增强、新安装模式。

```
<role>
你是跨平台文件安装模块的开发者。当前支持 COPY 和 LINK 两种 InstallMode。
</role>

<task>
新增 `InstallMode.HARDLINK`（硬链接模式）。
</task>

<constraints>
- Windows 下使用 `os.link()`，失败时优雅降级为 COPY 并打印 warning
- 硬链接不支持跨设备，必须处理 `OSError: [Errno 18] Invalid cross-device link`
- 必须为新模式添加 `InstallResult.HARDLINKED`
- 更新 `check_sync`，硬链接模式下比较 inode 或文件内容判断差异
</constraints>

<step_by_step>
请按以下顺序输出：
1. <analysis>: 硬链接与符号链接的差异，以及为什么需要它
2. <code>: 修改后的 installer.py 片段
3. <tests>: 使用 `tempfile` 和 `unittest.mock` 的测试代码
</step_by_step>
```

### 2.5 双向同步（`src/bidirectional.py`）

**适用场景**：基线策略调整、新增同步方向、冲突解决机制。

```
<role>
你是双向同步系统设计师。当前使用 `.hermes-baseline.json` / `.kimi-baseline.json`
记录"已知"官方 skills，新发现的 skills 视为用户新增。
</role>

<scenario>
用户反馈：双向同步时，如果用户在 Hermes 侧**修改**了已有的 skill（不是新增），
当前系统不会检测到变化，导致修改丢失。
</scenario>

<task>
设计一个方案，使双向同步能够检测到已有 skill 的**内容变更**并回写共享源。
</task>

<constraints>
- 不能破坏现有的"新增检测"逻辑
- 避免过度同步（频繁修改同一个 skill 不应导致反复回写）
- 标准库优先，不得引入 hashlib 以外的额外依赖
- 考虑性能：skills 目录下可能有 50+ 个 skill
</constraints>

<output>
<thinking>
分析以下方案的优劣：
A. 比较 SKILL.md 的修改时间戳
B. 比较 SKILL.md 的 SHA256 哈希
C. 比较整个目录的递归哈希
D. 引入一个单独的变更追踪文件
</thinking>

<recommendation>
推荐方案 + 理由（一句话）
</recommendation>

<implementation>
最小可行实现（MVP）的代码片段
</implementation>
</output>
```

### 2.6 定时任务（`src/scheduler.py`）

**适用场景**：新增 OS 后端、调度策略调整、任务状态查询增强。

```
<role>
你是跨平台系统任务调度开发者。当前后端：Windows(schtasks)、macOS(launchd)、Linux(cron)。
</role>

<task>
为 Windows 后端新增 `get_scheduler_info()` 的详细输出：
解析 `schtasks /Query /TN SkillsBridgeSync /FO LIST /V` 的结果，
提取 `Next Run Time`、`Last Run Time`、`Last Run Result`。
</task>

<input_example>
Folder: \
TaskName:                             SkillsBridgeSync
Next Run Time:                        5/10/2026 3:55:00 AM
Last Run Time:                        5/10/2026 3:50:00 AM
Last Run Result:                      0
</input_example>

<output>
<parser_code>: 纯字符串解析函数，返回 dict
<test_code>: 使用示例字符串的单元测试（mock subprocess）
</output>

<constraint>
- 不得使用正则表达式（按项目历史，优先用字符串 split）
- 处理字段缺失或格式变化时的健壮性
</constraint>
```

### 2.7 CLI（`scripts/install.py`）

**适用场景**：新增命令行参数、重构命令路由、改进错误输出。

```
<role>
你是 CLI 设计师。当前 `main()` 使用命令路由表模式，
根据 argparse 参数分发给 `_handle_*` 系列处理器。
</role>

<task>
新增 `--dry-run` 全局参数：预览所有操作但不实际执行文件系统修改。
</task>

<behavior_spec>
- COPY → 只打印 "[DRY-RUN] Would copy: src → dst"
- LINK → 只打印 "[DRY-RUN] Would link: src → dst"
- 定时任务 → 只打印任务配置详情，不调用 schtasks/launchctl/crontab
- 差异检测 → 正常输出差异报告（本身不修改文件）
</behavior_spec>

<implementation_guide>
- 在 `_parse_args()` 中添加 `--dry-run` 参数
- 在 `install_skill()` 中通过新增参数或全局状态实现（ prefer 参数传递）
- 修改最少处理器数量，保持 OCP
</implementation_guide>

<output>
<diff>: 以 git diff 风格展示修改点
</output>
```

---

## 3. 横向 Prompt 模板

### 3.1 TDD 开发循环

```
<role>
你是 TDD 实践者。遵循 Red-Green-Refactor 循环。
项目使用 Python `unittest`，零第三方依赖。
</role>

<red_phase>
为以下功能编写**失败**的测试用例：
<feature>
{{功能描述}}
</feature>

约束：
- 至少覆盖 3 个边界场景（空输入、异常路径、正常路径）
- 使用 `tempfile.TemporaryDirectory` 隔离文件系统副作用
- 断言信息必须清晰（自定义 `msg` 参数）
</red_phase>

<green_phase>
现在编写**最小实现**使上述测试通过。
约束：
- 不要过度设计
- 优先使用标准库
- 如果需要用正则，先用字符串操作尝试
</green_phase>

<refactor_phase>
审查刚实现的代码，按以下清单检查：
- [ ] 是否有重复逻辑？
- [ ] 函数是否超过 20 行？
- [ ] 是否有裸 `except Exception`？
- [ ] 类型注解是否完整？
- [ ] 命名是否符合项目术语（Skill、Platform、InstallMode）？

输出 <refactoring_diff> 和改进说明。
</refactor_phase>
```

### 3.2 代码审查（Code Review）

```
<role>
你是资深 Python 代码审查者，遵循 Clean Code 和 Clean Architecture 原则。
</role>

<code_to_review>
{{待审查代码}}
</code_to_review>

<project_context>
- 项目：`shared-skills-bridge`（AI skill 跨平台同步工具）
- 约束：Python 3.11+，零第三方依赖
- 架构：策略模式（adapter）、抽象后端（scheduler）、基线跟踪（bidirectional）
- 历史教训：
  - Windows 路径转义曾导致 `re.sub` 的 bad escape 错误
  - PowerShell `Set-Content` 默认写 UTF-8 BOM，frontmatter 解析需处理
  - 裸 `except Exception` 曾静默吞掉 NameError/TypeError
</project_context>

<review_checklist>
请逐项审查并给出结论：

1. **正确性**：是否有逻辑错误？边界条件是否遗漏？
2. **健壮性**：异常处理是否捕获具体类型？资源是否妥善关闭？
3. **可维护性**：函数是否单一职责？命名是否自解释？
4. **可测试性**：依赖是否可注入？副作用是否隔离？
5. **兼容性**：Windows/macOS/Linux 行为是否一致？路径分隔符处理是否正确？
6. **性能**：是否有 O(n²) 或不必要的文件 I/O？

每个问题如存在，按 🔴（必须修复）/ 🟡（建议优化）/ 🟢（OK）标注。
</review_checklist>

<output>
<findings>
| 项 | 等级 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
</findings>

<refactored_code>
（仅当存在 🔴 问题时输出修复后的完整代码）
</refactored_code>
</output>
```

### 3.3 故障排查（Troubleshooting）

```
<role>
你是 `shared-skills-bridge` 的技术支持专家。用户遇到运行时问题，你需要诊断并给出解决方案。
</role>

<error_report>
<symptom>
{{用户描述的症状}}
</symptom>

<environment>
- OS: {{Windows/macOS/Linux}}
- Python: {{版本}}
- 触发命令: {{完整命令}}
</environment>

<logs>
{{相关日志或堆栈跟踪}}
</logs>
</error_report>

<troubleshooting_guide>
1. 在 <root_cause> 中分析最可能的根因（按概率排序 Top 3）
2. 在 <solution> 中为每个根因给出：
   - 验证命令（用户可执行以确认）
   - 修复步骤
   - 预防措施
3. 如果涉及已知问题，引用 docs/TROUBLESHOOTING.md 中的对应条目
</troubleshooting_guide>

<example_scenario>
症状：Windows 上执行 `--install-scheduler` 后，任务未出现在 schtasks 列表中
根因 Top 1：Python 路径包含空格，schtasks 的 `/TR` 参数未加引号
验证：`schtasks /Query /TN SkillsBridgeSync`
修复：检查 scheduler.py 第 X 行的命令组装逻辑
预防：使用列表传给 subprocess，而非字符串拼接
</example_scenario>
```

### 3.4 文档生成

```
<role>
你是技术文档工程师，负责为 `shared-skills-bridge` 维护文档一致性。
</role>

<source>
{{新增/修改的代码或功能}}
</source>

<task>
同步更新以下文档，保持与代码一致：
1. `docs/api.md` — 公共接口签名和说明
2. `docs/design.md` — 架构流程图（如新增模块，标注 TODO: D2 图）
3. `CHANGELOG.md` — 按 Keep a Changelog 格式记录
4. `README.md` — 如影响快速开始章节
</task>

<constraints>
- 文档中的路径必须使用相对路径
- 代码示例必须可直接运行（copy-paste ready）
- 中文文档使用简体中文，术语保留英文（如 Platform、Skill、frontmatter）
- D2 图表更新时，必须同时修改 `.d2` 源文件和 `.svg`
</constraints>

<output>
为每个文档输出 <diff> 风格的变更块。
</output>
```

---

## 4. 少样本示例库

### 4.1 Frontmatter 解析扩展

**用户输入**：
```
新增 frontmatter 字段 `platforms: [linux, macos]` 的支持
```

**期望输出**：
```python
# src/models.py

def _parse_scalar_value(value: str) -> str | list[str]:
    """Parse a YAML scalar value.

    Supports:
    - Plain strings: hello
    - Quoted strings: "hello world"
    - Lists: [a, b, c]
    """
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        # List parsing: [a, b, c] or ["a", "b"]
        inner = value[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in inner.split(","):
            item = item.strip().strip('"').strip("'")
            if item:
                items.append(item)
        return items
    return value.strip('"').strip("'")
```

### 4.2 策略模式扩展

**用户输入**：
```
新增 Platform.CURSOR 适配器
```

**期望输出**：
```python
# src/adapter.py

def _adapt_for_cursor(content: str, skill_dir: Path | None = None) -> str:
    """Adapt skill content for Cursor platform.

    Cursor uses the same tool syntax as Kimi, but with
    ${CURSOR_SKILL_DIR} instead of ${HERMES_SKILL_DIR}.
    """
    # Reuse Kimi logic for shell placeholders and session ID cleanup
    content = _adapt_for_kimi(content, skill_dir)
    # Replace Cursor-specific variable with absolute path
    if skill_dir is not None and "${CURSOR_SKILL_DIR}" in content:
        content = content.replace("${CURSOR_SKILL_DIR}", str(skill_dir))
    return content

_ADAPTERS[Platform.CURSOR] = _adapt_for_cursor
```

### 4.3 CLI Handler 扩展

**用户输入**：
```
新增 --export 命令，导出所有已安装 skill 的清单为 JSON
```

**期望输出**：
```python
# scripts/install.py

def _handle_export(args: argparse.Namespace) -> int:
    """Export installed skills manifest as JSON."""
    platforms = _resolve_platforms(args.target or "both")
    manifest: dict[str, list[dict[str, str]]] = {}
    for platform in platforms:
        skills = scan_skills(resolve_target_dir(platform))
        manifest[platform.value] = [
            {"name": s.name, "description": s.description}
            for s in skills
        ]
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0

# In main() routing:
if args.export:  return _handle_export(args)
```

---

## 5. 反模式清单（Anti-patterns to Avoid）

以下是在本项目中**禁止**的 prompt 写法：

| 反模式 | 错误示例 | 正确做法 |
|--------|---------|---------|
| **裸异常捕获** | "添加 try/except 处理错误" | "捕获 `(OSError, UnicodeDecodeError)`，禁止裸 `except Exception`" |
| **平台硬编码** | "如果是 Windows 就做 X" | "使用 `platform.system()` 或抽象后端模式" |
| **字符串路径** | "使用 `os.path.join`" | "使用 `pathlib.Path`" |
| **全局状态** | "设置一个全局变量" | "通过函数参数传递状态，或使用 dataclass" |
| **正则优先** | "用正则解析 frontmatter" | "先尝试字符串 split，正则作为兜底" |
| **第三方依赖** | "安装 PyYAML 来解析" | "使用标准库实现；如必须引入，需经 ADR 流程" |
| **emoji 输出** | "打印 ✓ 和 ✗" | "使用 ASCII 安全字符 `[OK]` `[FAIL]`（Windows GBK 兼容）" |

---

## 6. 版本与演进

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-10 | 初始版本，覆盖 7 个模块 + 4 个横向模板 |

当新增模块或架构重大调整时，同步更新本文档的模块级模板和少样本示例库。
