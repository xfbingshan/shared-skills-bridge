# Shared Skills Bridge — API 文档

本文档描述各模块的公共接口。所有路径均使用 `pathlib.Path`。

---

## `src.models`

### `Skill`

```python
@dataclass
class Skill:
    name: str
    description: str
    source_dir: Path
    resources: list[str] = []
    frontmatter: dict[str, Any] = {}
```

**属性**：
- `skill_md_path: Path` — 返回 `source_dir / "SKILL.md"`

### `Platform` (Enum)

- `Platform.KIMI = "kimi"`
- `Platform.HERMES = "hermes"`

### `InstallMode` (Enum)

- `InstallMode.COPY = "copy"`
- `InstallMode.LINK = "link"`

### `parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]`

解析 Markdown 字符串中的 YAML frontmatter。

- **输入**：完整的 Markdown 内容（支持 UTF-8 BOM）
- **输出**：`(frontmatter_dict, body)`
- **支持的 YAML 特性**：标量字符串、引号字符串、列表 `[a, b]`、多行值 `|` / `>`

---

## `src.scanner`

### `scan_skills(source_dir: Path) -> List[Skill]`

扫描目录下的直接子目录，返回合法的 Skill 列表（按 name 排序）。

- **判定规则**：子目录包含 `SKILL.md`，且 frontmatter 中有非空的 `name` 和 `description`
- **异常处理**：读取失败时跳过该目录（不中断扫描）

---

## `src.adapter`

### `adapt_skill_content(content: str, platform: Platform, skill_dir: Path | None = None) -> str`

按目标平台适配 SKILL.md 内容。

| 平台 | 行为 |
|------|------|
| `Platform.HERMES` | 原样返回 |
| `Platform.KIMI` | 清理 `${HERMES_SKILL_DIR}`、`${HERMES_SESSION_ID}`、`!`cmd`` |

- **Raises**：`ValueError` 如果 platform 无注册适配器

---

## `src.installer`

### `resolve_target_dir(platform: Platform) -> Path`

返回默认目标目录：
- Kimi：`~/.config/agents/skills/`（回退 `~/.kimi/skills/`）
- Hermes：`~/.hermes/skills/shared/`

### `install_skill(skill, platform, mode=COPY, force=False, target_root=None) -> InstallResult`

安装单个 skill 到目标平台。

- **mode**：`InstallMode.COPY` 或 `InstallMode.LINK`
- **force**：为 `True` 时覆盖已存在的 skill
- **target_root**：覆盖默认目标目录（测试用）
- **返回**：`COPIED | LINKED | SKIPPED | ERROR`

### `check_sync(skills, platform, target_root=None) -> List[SyncDiff]`

比较源 skills 与已安装的 skills，返回差异列表。

- **Diff 状态**：`"ADD"`（目标不存在）、`"UPDATE"`（内容不同）

---

## `src.bidirectional`

### `discover_hermes_additions(hermes_skills_dir=None, baseline_path=None) -> List[Skill]`

扫描 Hermes skills 目录，返回基线建立后新增的 skills。

- **首次运行**：建立基线并返回空列表
- **排除项**：自动忽略 `shared/` 子目录

### `discover_kimi_additions(kimi_skills_dir=None, baseline_path=None) -> List[Skill]`

扫描 Kimi skills 目录，返回基线建立后新增的 skills。

### `sync_hermes_to_shared(additions, shared_source_dir) -> List[str]`

将 Hermes 侧新增 skills 复制到共享源目录。返回实际复制的 skill 名称列表。

### `sync_kimi_to_shared(additions, shared_source_dir) -> List[str]`

将 Kimi 侧新增 skills 复制到共享源目录。

### `update_baseline(hermes_skills_dir=None, baseline_path=None)`

更新 Hermes 基线到当前状态。用于安装官方 skills 后刷新"已知"列表。

### `update_kimi_baseline(kimi_skills_dir=None, baseline_path=None)`

更新 Kimi 基线到当前状态。

---

## `src.scheduler`

### `install_scheduler(source_dir, interval_minutes=5, target="both") -> bool`

创建操作系统级定时任务，自动执行 `--bidirectional` 同步。

- **跨平台**：Windows(schtasks) / macOS(launchd) / Linux(cron)
- **interval_minutes**：同步间隔（最小 1）
- **返回**：`True` 表示创建成功
- **Raises**：`RuntimeError` 在非支持平台上调用

### `uninstall_scheduler() -> bool`

移除定时任务。若任务不存在也返回 `True`（幂等）。

### `is_scheduler_installed() -> bool`

查询定时任务是否存在。

### `get_scheduler_info() -> dict`

返回定时任务元数据：
```python
{
    "installed": bool,
    "raw": str,              # 原始输出
    "interval_minutes": int | None,
}
```
