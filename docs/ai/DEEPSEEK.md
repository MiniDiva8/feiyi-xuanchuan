# 接入 DeepSeek 官方 API

在 [DeepSeek 开放平台](https://platform.deepseek.com/) 创建 API 密钥。将根目录的 `.env.example` 复制为 `.env`，把真实密钥填入 `MARKETING_AI_API_KEY`。本地 `.env` 由 Git 忽略。

```dotenv
MARKETING_AI_API_KEY=在本机填写
MARKETING_AI_BASE_URL=https://api.deepseek.com
MARKETING_AI_MODEL=deepseek-flash
MARKETING_AI_TIMEOUT_SECONDS=60
MARKETING_AI_MAX_OUTPUT_TOKENS=2400
MARKETING_AI_THINKING=disabled
```

接口地址和模型名见 [DeepSeek 官方 API 文档](https://api-docs.deepseek.com/zh-cn/)。

保存后重启工作台，用测试活动生成一份新的策划草稿。概览显示「AI 已配置」代表服务已读取密钥。新策划成功生成并显示「AI 生成」代表实际调用成功。密钥为空时，工作台提供「模板草稿」。调用失败时，工作台会显示错误。

安装依赖和启动方法见 [产品手册](../platform/RUNBOOK.md)。
