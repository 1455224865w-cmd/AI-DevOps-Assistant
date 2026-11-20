# 开发

```bash
pip install -e ".[dev]"
pytest
```

测试日志包含口令、GitHub token 和 `rm -rf /`。测试会替换 `subprocess.run`，一旦被调用就失败。
