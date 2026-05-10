# 跨平台开发注意事项

## 路径处理

```python
# ✅ 正确
from pathlib import Path
skill_dir = Path.home() / ".kimi" / "skills" / skill_name

# ❌ 错误
import os
skill_dir = os.path.join(os.path.expanduser("~"), ".kimi", "skills", skill_name)
```

**教训**：`re.sub()` 的 replacement 字符串中，Windows 反斜杠路径会被解释为转义序列。使用 `lambda m: path_str` 替代。

## 编码

```python
# ✅ 正确
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 处理 BOM
if content.startswith("\ufeff"):
    content = content[1:]
```

**教训**：PowerShell `Set-Content` 默认写 UTF-8 BOM，解析器必须处理。

## 控制台输出

```python
# ✅ 正确（Windows GBK 兼容）
print("[OK]   Installation complete")
print("[FAIL] Permission denied")

# ❌ 错误
print("✅ Installation complete")
print("❌ Permission denied")
```

## 符号链接

```python
import os

try:
    os.symlink(source, target)
except OSError:
    # Windows 非管理员可能失败，fallback 到 junction
    import subprocess
    subprocess.run(["mklink", "/J", str(target), str(source)], check=True)
```

## 定时任务

| OS | 机制 | 权限 |
|----|------|------|
| Windows | `schtasks.exe` | 普通用户 |
| macOS | `launchd` plist | 普通用户 |
| Linux | `cron` (用户 crontab) | 普通用户 |

抽象层：使用 `SchedulerBackend(ABC)` + 平台自动分发。

## Python 路径

```python
# ✅ 正确
import sys
python_exe = sys.executable

# ❌ 错误
import platform
python_exe = platform.python_executable()  # AttributeError!
```
