# 路线

## 远程仓库

- 仓库：https://github.com/1455224865w-cmd/AI-DevOps-Assistant
- `main` 已推送初始提交 `4a065cb`。
- CI 工作流是 `.github/workflows/ci.yml`，只安装项目并运行 `pytest`。
- 首次推送的运行已成功：https://github.com/1455224865w-cmd/AI-DevOps-Assistant/actions/runs/44689661344
- Milestone「0.2 下一步」跟踪下面三个 Issue：
  - #1 只读拉取失败的 GitHub Actions 日志
  - #2 按证据关联相似失败
  - #3 在隔离工作区生成修复任务
## 已完成：0.1.0

GitHub Actions 日志分类、脱敏、文件和测试定位、未验证建议、诊断历史。

## 下一步

1. 用只读 GitHub 权限拉取指定失败作业的日志。Token 不写日志。
2. 把相似失败关联起来，仍然区分证据和推测。
3. 生成修复任务。代码修改只能发生在独立工作区，并且先跑测试。

## 暂不做

自动合并 PR、自动部署、执行日志中的命令。
