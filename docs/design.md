# Shared Skills Bridge — 设计文档

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    shared-skills/ (源目录)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ my-skill-1/  │  │ my-skill-2/  │  │ my-skill-3/  │      │
│  │  SKILL.md    │  │  SKILL.md    │  │  SKILL.md    │      │
│  │  scripts/    │  │  references/ │  │  assets/     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
   ┌─────────────────┐            ┌─────────────────┐
   │  Kimi Installer │            │ Hermes Installer│
   │  (copy/link)    │            │ (copy/external) │
   └────────┬────────┘            └────────┬────────┘
            ▼                               ▼
   ┌─────────────────┐            ┌─────────────────┐
   │ ~/.kimi/skills/ │            │ ~/.hermes/skills│
   │  (扁平结构)      │            │ /shared/        │
   └─────────────────┘            └─────────────────┘
```

## 2. 模块划分

| 模块 | 文件 | 职责 |
|------|------|------|
| **models** | `src/models.py` | Skill 数据模型、frontmatter 解析、平台枚举 |
| **scanner** | `src/scanner.py` | 扫描共享目录，发现合法 skill 包 |
| **adapter** | `src/adapter.py` | Skill 内容适配（清理平台特有语法） |
| **installer** | `src/installer.py` | 安装/同步逻辑（复制、链接、差异检测） |
| **cli** | `scripts/install.py` | 命令行入口，协调各模块 |

## 3. 数据模型

```python
@dataclass
class Skill:
    name: str
    description: str
    source_dir: Path          # 共享源目录中的路径
    resources: List[str]      # 子目录/文件列表
    frontmatter: dict         # 完整 frontmatter

class Platform(Enum):
    KIMI = "kimi"
    HERMES = "hermes"

class InstallMode(Enum):
    COPY = "copy"
    LINK = "link"
```

## 4. 核心流程

### 4.1 扫描流程
```
scan(source_dir) -> List[Skill]
  └─ 递归遍历 source_dir 下所有直接子目录
     └─ 若子目录包含 SKILL.md
        └─ 解析 frontmatter（提取 name, description）
           └─ 若 name 和 description 存在 → 生成 Skill 对象
```

### 4.2 安装流程（Copy 模式）
```
install(skills, platform, mode=COPY)
  ├─ Kimi: target = resolve_kimi_dir() / skill.name
  ├─ Hermes: target = resolve_hermes_dir() / "shared" / skill.name
  └─ 遍历每个 skill
     ├─ 若 mode == COPY:
     │   └─ shutil.copytree(source, target, dirs_exist_ok=True)
     │      └─ Kimi 模式：先经 adapter 清理内容
     └─ 若 mode == LINK:
        └─ os.symlink(source, target) 或 _win_symlink(source, target)
```

### 4.3 差异检测流程
```
check_sync(source_skills, platform)
  └─ 对比源目录与目标目录
     ├─ 源有目标无 → ADD
     ├─ 源有目标有且内容不同 → UPDATE
     └─ 源无目标有 → REMOVE (optional)
```

## 5. 平台适配策略

### Kimi 侧适配
| 源内容 | 适配动作 | 原因 |
|--------|----------|------|
| `${HERMES_SKILL_DIR}` | 替换为 skill 所在绝对路径 | Kimi 不支持该变量 |
| `${HERMES_SESSION_ID}` | 删除或替换为空字符串 | Kimi 无 session 概念 |
| `` !`cmd` `` | 替换为 `` `[cmd output]` `` 或保留标记 | 防止意外执行 |
| `platforms: [linux]` | 保留（Kimi 会忽略未知 frontmatter） | 无害 |

### Hermes 侧适配
- 无需内容转换，因为 Hermes 可直接读取扁平结构（通过 external_dirs）
- 若使用 Copy 模式，归入 `~/.hermes/skills/shared/` 下

## 6. 测试策略（TDD）

采用 **Red-Green-Refactor** 循环：

1. **Scanner 模块**：先写测试 `test_scanner.py`
   - 测试空目录返回空列表
   - 测试合法 skill 被正确解析
   - 测试缺少 frontmatter 的 skill 被跳过

2. **Adapter 模块**：先写测试 `test_adapter.py`
   - 测试模板变量替换
   - 测试内联 shell 标记处理
   - 测试无变化内容原样返回

3. **Installer 模块**：先写测试 `test_installer.py`
   - 测试 copy 到临时目录
   - 测试 link 创建（Windows junction）
   - 测试差异检测逻辑

4. **集成测试**：端到端验证完整流程

## 7. 目录结构

```
shared-skills-bridge/
├── docs/
│   ├── requirements.md
│   └── design.md
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── scanner.py
│   ├── adapter.py
│   └── installer.py
├── tests/
│   ├── __init__.py
│   ├── test_scanner.py
│   ├── test_adapter.py
│   └── test_installer.py
├── scripts/
│   └── install.py
├── shared-skills/
│   └── example-git-workflow/
│       ├── SKILL.md
│       └── references/
│           └── commit-message-template.md
├── pyproject.toml
└── README.md
```

## 8. 命令行接口设计

```bash
python scripts/install.py --source ./shared-skills --target kimis      # 安装到 Kimi
python scripts/install.py --source ./shared-skills --target hermes     # 安装到 Hermes
python scripts/install.py --source ./shared-skills --target both       # 安装到两者
python scripts/install.py --check                                      # 仅检查差异
python scripts/install.py --mode link                                  # 使用符号链接
python scripts/install.py --force                                      # 强制覆盖
```
