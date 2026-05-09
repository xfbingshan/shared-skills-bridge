# Shared Skills Bridge

让 **VS Code Kimi Code CLI** 和 **Hermes Agent** 共享同一套 Skills。

## 背景

| 工具 | Skills 目录结构 | 特性 |
|------|----------------|------|
| Kimi Code CLI | `~/.kimi/skills/skill-name/SKILL.md` | 扁平结构 |
| Hermes Agent | `~/.hermes/skills/category/skill-name/SKILL.md` | 分类结构，支持 `${HERMES_SKILL_DIR}`、`!`cmd`` |

两者核心格式相同（`SKILL.md` + YAML frontmatter），但目录层级和部分语法存在差异。本项目提供**扫描 → 适配 → 安装**的完整桥接能力。

## 特性

- 🔍 **自动扫描** — 递归发现共享目录中的合法 skill 包
- 🔄 **内容适配** — 安装到 Kimi 时自动清理 Hermes 特有语法（`${HERMES_SKILL_DIR}`、`!`cmd``）
- 📋 **差异检测** — `--check` 模式预览待同步项，不实际修改
- 🔗 **双模式安装** — `copy`（复制，可独立修改）或 `link`（符号链接，即时同步）
- 🪟 **跨平台** — 支持 Windows（junction 回退）、macOS、Linux
- 🔄 **双向同步** — 在 Hermes 或 Kimi 中新增 skill，自动同步到另一端
- ⏰ **定时任务** — 内置跨平台定时同步（Windows schtasks / macOS launchd / Linux cron）
- 🧪 **TDD 开发** — 全模块单元测试 + 集成测试覆盖

## 快速开始

### 1. 准备共享 Skills 源目录

```
shared-skills/
├── git-commit-guide/           ← 一个 skill 包
│   ├── SKILL.md                ← 必需：frontmatter + Markdown 指令
│   └── references/             ← 可选：参考文档
│       └── conventional-commits-spec.md
└── my-other-skill/
    ├── SKILL.md
    └── scripts/
        └── helper.py
```

### 2. 手动同步命令

```bash
# 安装到 Kimi Code CLI
python scripts/install.py --source ./shared-skills --target kimi

# 安装到 Hermes Agent
python scripts/install.py --source ./shared-skills --target hermes

# 同时安装到两者
python scripts/install.py --source ./shared-skills --target both

# 双向同步（扫描两端新增 → 共享源 → 全平台）
python scripts/install.py --source ./shared-skills --target both --bidirectional

# 仅检查差异（不安装）
python scripts/install.py --source ./shared-skills --target both --check

# 强制覆盖已有 skill
python scripts/install.py --source ./shared-skills --target both --force

# 使用符号链接（修改源目录即时生效）
python scripts/install.py --source ./shared-skills --target both --mode link

# 更新基线（安装官方 skill 后运行）
python scripts/install.py --update-baseline
```

### 3. 一键定时任务（自动同步，跨平台）

```bash
# 安装自动同步任务（每 5 分钟，默认）
python scripts/install.py --install-scheduler --source ./shared-skills

# 自定义间隔（每 10 分钟）
python scripts/install.py --install-scheduler --source ./shared-skills --interval 10

# 查看定时任务状态
python scripts/install.py --scheduler-status

# 卸载定时任务
python scripts/install.py --uninstall-scheduler
```

| 平台 | 定时任务机制 | 权限要求 |
|------|-------------|---------|
| **Windows** | `schtasks.exe` | 普通用户 |
| **macOS** | `launchd` (~/Library/LaunchAgents/) | 普通用户 |
| **Linux** | `cron` (用户 crontab) | 普通用户 |

安装后，系统会每 N 分钟自动执行 `--bidirectional` 同步，您在**任意一端**新增 skill 都会自动传播到另一端。

### 4. 验证安装

- **Kimi**: 打开 VS Code → Kimi Code，询问与 skill 相关的问题，观察是否触发
- **Hermes**: 运行 `hermes skills list`，查看 shared category 下是否出现

## 项目结构

```
shared-skills-bridge/
├── docs/
│   ├── requirements.md         # 需求文档
│   └── design.md               # 设计文档
├── src/
│   ├── __init__.py
│   ├── models.py               # Skill 数据模型 + frontmatter 解析
│   ├── scanner.py              # 扫描共享目录
│   ├── adapter.py              # 内容适配（Hermes → Kimi）
│   ├── installer.py            # 安装/同步/差异检测
│   ├── bidirectional.py        # 双向同步（基线跟踪）
│   └── scheduler.py            # 跨平台定时任务（Win/macOS/Linux）
├── tests/
│   ├── __init__.py
│   ├── test_models.py          # 9 个测试
│   ├── test_scanner.py         # 9 个测试
│   ├── test_adapter.py         # 7 个测试
│   ├── test_installer.py       # 10 个测试
│   ├── test_bidirectional.py   # 10 个测试
│   ├── test_bidirectional_kimi.py  # 7 个测试
│   ├── test_scheduler.py       # 12 个测试
│   ├── test_scheduler_crossplatform.py  # 13 个测试
│   └── test_integration.py     # 5 个集成测试
├── scripts/
│   └── install.py              # CLI 入口
├── shared-skills/              # 示例共享 skills
│   └── git-commit-guide/
├── pyproject.toml
└── README.md
```

## 运行测试

```bash
# 运行全部测试
python -m unittest discover -s tests -v

# 运行单个模块
python -m unittest tests.test_scanner -v
```

## 兼容性说明

### 格式层面 ✅ 高度兼容

- `SKILL.md` 文件名一致
- Frontmatter `name` + `description` 一致
- Markdown 指令格式一致
- `scripts/`、`references/` 等资源目录通用

### 内容层面 ⚠️ 需注意

| 类型 | 兼容性 | 说明 |
|------|--------|------|
| **纯知识型 skill** | ✅ 完美 | 如编码规范、设计模式、最佳实践 |
| **工具调用型 skill** | ⚠️ 需适配 | Kimi 的 `WriteFile` / `Shell` 与 Hermes 的工具名可能不同 |
| **Hermes 特有语法** | ✅ 已处理 | `${HERMES_SKILL_DIR}`、`!`cmd`` 安装到 Kimi 时自动清理 |

## 设计决策

1. **标准库优先** — 零第三方依赖，降低部署成本
2. **扁平源目录** — 共享源采用 Kimi 的扁平结构（最简公分母），Hermes 安装时归入 `shared/` category
3. **单向适配** — 仅对 Kimi 做内容清理，Hermes 原生支持读取扁平结构（通过 `external_dirs`）
4. **渐进披露** — `--check` 先预览再安装，避免意外覆盖
5. **基线跟踪** — 双向同步通过 `.hermes-baseline.json` / `.kimi-baseline.json` 识别用户新增 skill

## License

MIT
