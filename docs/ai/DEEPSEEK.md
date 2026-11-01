# DeepSeek 接入与本机验证

使用火山方舟兼容 Chat Completions 接口，模型标识为 `deepseek-v4-flash`。实际密钥只放在根目录 `.env`，不要提交。

```dotenv
MARKETING_AI_API_KEY=在本机填写
MARKETING_AI_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
MARKETING_AI_MODEL=deepseek-v4-flash
MARKETING_AI_TIMEOUT_SECONDS=60
MARKETING_AI_MAX_OUTPUT_TOKENS=2400
MARKETING_AI_THINKING=disabled
```

Coding Plan 的适用范围及额度应以账户当前套餐规则为准；上线前确认是否需要普通推理服务，不能只替换地址并假定订阅额度通用。`ark-code-latest` 会随控制台选择变化，不用于固定 DeepSeek。

`MARKETING_AI_THINKING` 为空时不发送额外参数，兼容原有提供方；支持 `enabled` / `disabled`，其他值报错且不发出请求。关闭额外思考可减少当前文字草稿场景的等待和推理输出。真实生成失败仍会明确报错，不伪装为模板成功。

2026-11-01 通过项目实际 AI 引擎，用合成课程资料验证方案、文案、复盘均为 `generation_mode=ai`。关闭额外思考后的单次测量分别约 5.9、3.1、4.3 秒；不是性能保证。没有真实商家资料或付费效果证明，未验证图像生成与视频成片。

本机 Python 3.10 无法安装仓库指定的 SQLAlchemy 2.1.6。启动脚本会检查 Python 3.12+；如项目内已有 `.artifacts/runtime/python312/python.exe` 便携环境则使用它。否则使用正常 `.venv`。便携环境不会随 Git 上传，其他成员仍需自行安装 Python 和依赖。
