# Shared Skills Bridge — 设计文档

## 1. 架构概览

![Architecture Overview](d2/architecture.svg)

## 2. 模块划分

| 模块 | 文件 | 职责 |
|------|------|------|
| **models** | `src/models.py` | Skill 数据模型、frontmatter 解析、平台/模式枚举 |
| **scanner** | `src/scanner.py` | 扫描目录，发现合法 skill 包 |
| **adapter** | `src/adapter.py` | Skill 内容适配（策略模式，按平台分发） |
| **installer** | `src/installer.py` | 安装/同步逻辑（复制、链接、差异检测） |
| **bidirectional** | `src/bidirectional.py` | 双向同步：扫描两端新增，回写共享源 |
| **scheduler** | `src/scheduler.py` | 跨平台定时任务（抽象后端 + Win/macOS/Linux 实现） |
| **cli** | `scripts/install.py` | 命令行入口，路由到各 handler |

## 3. 数据模型

```python
@dataclass
class Skill:
    name: str
    description: str
    source_dir: Path
    resources: list[str]
    frontmatter: dict[str, Any]

class Platform(Enum):
    KIMI = "kimi"
    HERMES = "hermes"

class InstallMode(Enum):
    COPY = "copy"
    LINK = "link"

class InstallResult(Enum):
    COPIED = "copied"
    LINKED = "linked"
    SKIPPED = "skipped"
    ERROR = "error"
```

## 4. 核心流程

### 4.1 扫描流程
![Scan Flow](d2/scan-flow.svg)

### 4.2 正向安装流程
![Install Flow](d2/install-flow.svg)

### 4.3 双向同步流程
![Bidirectional Flow](d2/bidirectional-flow.svg)

### 4.4 差异检测流程
![Check Flow](d2/check-flow.svg)

## 5. 平台适配策略

### Adapter 策略模式
```python
_ADAPTERS: dict[Platform, Callable] = {
    Platform.KIMI: _adapt_for_kimi,
    Platform.HERMES: _adapt_for_hermes,
}
```

| 源内容 | Kimi 适配 | Hermes 适配 |
|--------|-----------|-------------|
| `${HERMES_SKILL_DIR}` | 替换为绝对路径 | 原样保留 |
| `${HERMES_SESSION_ID}` | 删除 | 原样保留 |
| `` !`cmd` `` | 替换为 `[shell: cmd]` | 原样保留 |
| `platforms: [linux]` | 保留（Kimi 忽略未知字段） | 保留并解析 |

## 6. 定时任务架构

### 抽象后端
```python
class SchedulerBackend(ABC):
    @abstractmethod
    def install(self, source_dir, interval_minutes, target) -> bool: ...
    @abstractmethod
    def uninstall(self) -> bool: ...
    @abstractmethod
    def is_installed(self) -> bool: ...
    @abstractmethod
    def get_info(self) -> dict: ...
```

### 平台实现
| 平台 | 后端类 | 机制 | 用户权限 |
|------|--------|------|---------|
| Windows | `WindowsScheduler` | `schtasks.exe` | 普通用户 |
| macOS | `MacOSScheduler` | `launchd` plist | 普通用户 |
| Linux | `LinuxCronScheduler` | `crontab` | 普通用户 |

## 7. 目录结构

```
shared-skills-bridge/
├── docs/
│   ├── requirements.md
│   ├── design.md
│   └── api.md
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── scanner.py
│   ├── adapter.py
│   ├── installer.py
│   ├── bidirectional.py
│   └── scheduler.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py          (9 tests)
│   ├── test_scanner.py         (9 tests)
│   ├── test_adapter.py         (7 tests)
│   ├── test_installer.py       (10 tests)
│   ├── test_bidirectional.py   (10 tests)
│   ├── test_bidirectional_kimi.py  (7 tests)
│   ├── test_scheduler.py       (12 tests)
│   ├── test_scheduler_crossplatform.py  (13 tests)
│   └── test_integration.py     (5 tests)
├── scripts/
│   └── install.py
├── shared-skills/
│   ├── git-commit-guide/
│   ├── clean-code/
│   ├── clean-architecture/
│   └── karpathy-guidelines/
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

## 8. 命令行接口设计

```bash
# 正向同步
python scripts/install.py --source ./shared-skills --target kimi
python scripts/install.py --source ./shared-skills --target hermes
python scripts/install.py --source ./shared-skills --target both --force

# 双向同步
python scripts/install.py --source ./shared-skills --target both --bidirectional

# 差异检查
python scripts/install.py --source ./shared-skills --target both --check

# 基线管理
python scripts/install.py --update-baseline

# 定时任务
python scripts/install.py --install-scheduler --source ./shared-skills --interval 5
python scripts/install.py --uninstall-scheduler
python scripts/install.py --scheduler-status
```

## 9. 测试策略（TDD）

采用 **Red-Green-Refactor** 循环：

1. **models**：frontmatter 解析（BOM、多行、列表、标量）
2. **scanner**：空目录、合法 skill、缺少字段、非目录项
3. **adapter**：策略模式、变量替换、shell 占位符
4. **installer**：copy/link、差异检测、force/skip
5. **bidirectional**：基线创建、新增检测、shared 排除、反向复制
6. **scheduler**：跨平台 mock（schtasks/launchctl/crontab）
7. **integration**：端到端验证完整同步流程

## 10. 设计决策（ADR）

### ADR-001：标准库优先
**背景**：降低部署成本，避免依赖冲突。  
**决策**：仅使用 Python 标准库。  
**影响**：自己实现了 frontmatter 解析器（而非用 PyYAML），但功能足够覆盖 skill 场景。

### ADR-002：扁平共享源结构
**背景**：Kimi 使用扁平结构，Hermes 使用分类结构。  
**决策**：共享源采用 Kimi 的扁平结构（最简公分母），Hermes 安装时归入 `shared/` category。  
**影响**：Hermes 侧会出现一个 `shared` category，但避免了复杂的双向目录映射。

### ADR-003：基线机制而非白名单
**背景**：需要区分"官方内置 skills"和"用户新增 skills"。  
**决策**：首次运行时记录当前所有 skills 为"基线"，后续新增的视为用户 skills。  
**影响**：用户安装官方 skills 后需手动 `--update-baseline`，但无需维护硬编码白名单。

### ADR-004：Linux 使用 cron 而非 systemd
**背景**：Linux 定时任务可选 cron 或 systemd timer。  
**决策**：使用 cron（用户级 crontab）。  
**影响**：更轻量、兼容性更好（WSL、老旧发行版），但精度为分钟级（足够）。
