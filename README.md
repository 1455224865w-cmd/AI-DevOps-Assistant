# AI DevOps Assistant

这个工具阅读 CI 日志，指出匹配到的失败类型、相关文件和未验证的修复方向。它不替代 GitHub Actions，也不根据日志自动改代码。

## 0.1.0 能做什么

- 识别测试、编译、检查器、依赖、Docker、超时和网络失败的常见文本模式。
- 匹配不到时返回 `unknown`，不编造根因。
- 提取 `文件:行号` 和 `FAILED` 测试名。
- 脱敏口令、GitHub token、云访问密钥和 Bearer。
- 收集日志里的 `rm`、`curl`、`bash` 等命令，但 `commands_executed` 始终是 `false`。
- 把诊断摘要存到本地 SQLite，便于回看。

## 限制

- 解析 GitHub Actions 和 GitLab CI 日志。Jenkins 仍返回未支持。GitLab 令牌 `glpat-` 会脱敏。分析过程不执行日志里的命令。
- 规则命中不是已经验证的根因。
- 没有仓库授权，不会主动拉取 Actions 日志。

## 本地运行

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn devops_assistant.api:app --reload
```

`POST /api/diagnoses` 的正文是 `log`、`provider` 和可选的 `repository`。不要提交真实密钥。

## 许可证

Apache-2.0。

## 语言和 Spring AI

默认语言是中文。请求带 `Accept-Language: en` 或 `?lang=en` 时，错误信息和工具说明返回英文。源码、SQL、日志原文不翻译。

Spring AI 不内嵌在本服务里。把 `spring-ai/pom-snippet.xml` 的 `spring-ai-starter-mcp-client` 加到 Spring AI 应用，连接配置由 `spring-ai/application-mcp.yml` 指向 Nacos，地址写在 `nacos/spring-mcp.yaml`。端点默认是 `/mcp`。本仓库的测试覆盖 MCP 的 initialize、tools/list 和 tools/call，不编译 Java。

## 配置

服务地址不写进镜像。设置 `NACOS_SERVER` 后，进程启动时读取 Nacos 中的服务配置，默认 dataId 见 `nacos/service.properties`。没有 Nacos 时使用 `APP_HOST`、`APP_PORT`、`APP_DATABASE` 和 `APP_LOCALE`。

Spring AI 的 MCP 地址放在 Nacos 的 `nacos/spring-mcp.yaml`。`spring-ai/application-mcp.yml` 只指向 Nacos，不写服务地址。

## 镜像

```bash
docker build -t ai-devops-assistant:local .
```

`main` 分支的 `.github/workflows/image.yml` 会把镜像推到 `ghcr.io/wangcheng-coder/ai-devops-assistant`。

## 页面

打开服务根路径 `/`。五个项目使用同一套版式：顶栏、左右两栏、中英文切换。页面只调用本服务已有的接口。
