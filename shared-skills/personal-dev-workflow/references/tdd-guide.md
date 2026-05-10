# TDD 开发指南

## Red-Green-Refactor 循环详解

### Phase 1: Red（编写失败的测试）

1. **确定测试范围**：只测试 public API，不测试 private 实现细节
2. **命名规范**：`test_<行为>_<条件>`，如 `test_scan_skills_empty_dir_returns_empty_list`
3. **边界覆盖**：
   - 空输入 / 空集合
   - 最小有效输入
   - 异常类型（文件不存在、权限不足、编码错误）
   - 并发/竞态（如适用）
4. **隔离副作用**：使用 `tempfile`、`unittest.mock`、`MonkeyPatch`

### Phase 2: Green（最小实现）

1. 先让测试通过，**不考虑代码优雅**
2. 可以硬编码返回值，只要测试通过
3. 标记 TODO：重构前不得提交

### Phase 3: Refactor（重构）

1. 消除重复
2. 提取辅助函数（SRP）
3. 重命名提高可读性
4. 添加类型注解
5. 重跑全部测试确认通过

## 测试文件模板

```python
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.scanner import scan_skills


class TestScanner(unittest.TestCase):
    """Test skill scanner."""

    def test_empty_dir_returns_empty_list(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = scan_skills(Path(tmpdir))
            self.assertEqual(result, [], msg="Empty dir should yield empty list")

    def test_skips_non_skill_directories(self) -> None:
        """Directories without SKILL.md are silently skipped."""
        ...

    def test_valid_skill_with_frontmatter(self) -> None:
        """Directory with valid SKILL.md produces Skill object."""
        ...
```

## 反模式

- ❌ 一个测试验证多个行为
- ❌ 测试依赖外部文件/网络
- ❌ 测试顺序相关（每个测试必须独立）
- ❌ 忽略失败测试直接提交
