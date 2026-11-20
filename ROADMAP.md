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

0.1.1 已完成的部分写在变更记录里。仍未完成的是需要真实数据库或仍未替换存储的部分。

1. 用只读 GitHub 权限拉取指定失败作业的日志。Token 不写日志。
2. 把相似失败关联起来，仍然区分证据和推测。
3. 生成修复任务。代码修改只能发生在独立工作区，并且先跑测试。

## 暂不做

自动合并 PR、自动部署、执行日志中的命令。

## 0.1.2

借鉴 [FailureMemory](https://github.com/UnguisAI/failurememory) 的失败指纹：日志先脱敏，再去掉时间和提交号。指纹用于比较同一种失败，不触发重跑。

## 0.1.3

error 标注和失败指纹都来自脱敏后的日志。

## 0.1.4

error 标注用于分类。日志中的命令保持未执行。

## 0.1.5

历史归并可以从接口读取，命令仍然不执行。

## 0.1.6

Spring AI 通过 MCP 提交日志。命令不会被执行，密钥会从结果中去掉。
