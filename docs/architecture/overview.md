# 架构

分类器是一组有名字的文本规则。每条命中保留证据片段。没有命中时结果是 `unknown`。

脱敏在分类之前运行。命令行只被收集进 `untrusted_commands`。模块不调用 `subprocess`。

历史记录放在 SQLite。CI 提供方以后做成独立解析器，不把 GitLab 或 Jenkins 的格式塞进 GitHub Actions 规则。
