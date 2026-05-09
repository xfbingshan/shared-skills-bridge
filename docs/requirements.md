# Shared Skills Bridge — 需求文档

## 1. 项目背景

用户同时使用两个 AI Agent 工具：
- **VS Code Kimi Code CLI**：skills 存放在 `~/.kimi/skills/`（扁平结构 `skill-name/SKILL.md`）
- **Hermes Agent**：skills 存放在 `~/.hermes/skills/`（分类结构 `category/skill-name/SKILL.md`）

两者核心格式高度相似（均为 `SKILL.md` + YAML frontmatter），但目录结构和部分特性存在差异。本项目旨在建立一个**共享 skills 桥接系统**，让用户只需维护一份 skills 源码，即可同步到两个平台使用。

## 2. 功能需求

### FR-001 Skill 扫描（Scan）
系统应能递归扫描共享 skills 源目录，发现所有合法的 skill 包。
- 输入：源目录路径
- 判定规则：包含 `SKILL.md` 且 frontmatter 有 `name` 和 `description` 的目录
- 输出：Skill 元数据列表（name, description, path, resources）

### FR-002 格式适配（Adapt）
系统应能对 skill 内容进行必要的格式适配，使同一份源码兼容不同平台。
- Hermes → Kimi：清理 `${HERMES_SKILL_DIR}`、`${HERMES_SESSION_ID}`、`!`cmd`` 等 Hermes 特有语法
- Kimi → Hermes：内容原样保留（Hermes 原生支持读取）
- 资源目录映射：`assets/`、`scripts/`、`references/` 等子目录原样复制

### FR-003 安装到 Kimi（Install to Kimi）
系统应能将共享 skills 安装到 Kimi Code CLI 的 skills 目录。
- 目标路径优先级：`~/.config/agents/skills/` > `~/.kimi/skills/`
- 目录结构保持扁平（`skill-name/SKILL.md`）
- 支持覆盖安装（--force）和只安装新增（默认）

### FR-004 安装到 Hermes（Install to Hermes）
系统应能将共享 skills 安装到 Hermes Agent 的 skills 目录。
- 目标路径：`~/.hermes/skills/shared/`（统一归入 shared category）
- 目录结构：`shared/skill-name/SKILL.md`
- 同时支持配置 Hermes `external_dirs` 指向共享源目录（零拷贝模式）

### FR-005 双模式安装（Copy vs. Link）
系统应支持两种安装模式：
- **copy 模式**（默认）：将 skill 文件复制到目标目录，用户可独立修改
- **link 模式**：创建符号链接或 junction，修改源目录即时生效

### FR-006 同步检测（Sync Check）
系统应能检测源目录与目标目录之间的差异（新增、修改），并报告待同步项。

### FR-007 双向同步（Bidirectional Sync）
系统应支持从两端向共享源反向同步：
- 当用户在 Hermes 侧直接创建新 skill 时，自动检测并复制到 `shared-skills/`，再正向安装到 Kimi
- 当用户在 Kimi 侧直接创建新 skill 时，自动检测并复制到 `shared-skills/`，再正向安装到 Hermes
- 通过基线文件（`.hermes-baseline.json` / `.kimi-baseline.json`）区分"用户新增"与"官方内置"

### FR-008 基线管理（Baseline）
系统应能记录两端当前的 skills 状态作为"已知基线"：
- 首次运行时自动建立基线（将现有 skills 标记为已知）
- 支持手动更新基线（`--update-baseline`）
- 基线文件与 skills 目录共存，格式为 JSON

### FR-009 定时任务（Scheduler）
系统应支持配置操作系统级定时任务，实现自动同步：
- **Windows**：`schtasks.exe`（任务计划程序）
- **macOS**：`launchd`（用户级 Agent）
- **Linux**：`cron`（用户 crontab）
- 支持自定义同步间隔（默认 5 分钟，最小 1 分钟）
- 支持安装、卸载、状态查询

### FR-010 示例 Skill 模板
项目应内置至少一个示例 skill，展示最佳实践。

## 3. 非功能需求

### NFR-001 跨平台
- 支持 Windows（当前环境）、macOS、Linux
- Windows 下符号链接使用 junction 或目录符号链接
- 定时任务机制按平台自动分发

### NFR-002 无外部依赖（标准库优先）
- 仅使用 Python 标准库
- 降低部署成本，避免虚拟环境冲突

### NFR-003 可测试性
- 所有核心模块需可单元测试
- 使用临时目录替代真实用户目录进行测试
- 跨平台模块通过 mock 测试

### NFR-004 Git 版本管理
- 所有开发产出纳入 git 版本控制
- 遵循小步提交原则

### NFR-005 错误处理
- 不静默吞掉所有异常（避免 `except Exception: pass`）
- 捕获具体异常类型（`OSError`、`UnicodeDecodeError` 等）
- 安装失败时返回明确的错误状态

## 4. 约束条件

- Python >= 3.11（与 Hermes 保持一致）
- 不得修改 Kimi Code CLI 或 Hermes Agent 的源代码
- 不得依赖任何第三方 Python 包
- 定时任务无需管理员权限（用户级任务）
