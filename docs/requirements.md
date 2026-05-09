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
-  Hermes → Kimi：清理 `${HERMES_SKILL_DIR}`、`${HERMES_SESSION_ID}`、`!`cmd`` 等 Hermes 特有语法
-  Kimi → Hermes：Hermes 可直接读取扁平结构，无需反向转换（通过 external_dirs）
-  资源目录映射：`assets/` ↔ 保留；`templates/` → 作为普通目录保留

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
系统应能检测源目录与目标目录之间的差异（新增、修改、删除），并报告待同步项。

### FR-007 示例 Skill 模板
项目应内置至少一个示例 skill，展示最佳实践。

## 3. 非功能需求

### NFR-001 跨平台
- 支持 Windows（当前环境）、macOS、Linux
- Windows 下符号链接使用 junction 或目录符号链接

### NFR-002 无外部依赖（标准库优先）
- 仅使用 Python 标准库
- 降低部署成本，避免虚拟环境冲突

### NFR-003 可测试性
- 所有核心模块需可单元测试
- 使用临时目录替代真实用户目录进行测试

### NFR-004 Git 版本管理
- 所有开发产出纳入 git 版本控制
- 遵循小步提交原则

## 4. 约束条件

- Python >= 3.11（与 Hermes 保持一致）
- 不得修改 Kimi Code CLI 或 Hermes Agent 的源代码
- 不得依赖任何第三方 Python 包
