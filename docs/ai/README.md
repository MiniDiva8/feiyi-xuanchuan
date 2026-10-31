# 营销 AI 模块

Python 3.12+，纯标准库，无须模型 SDK。后端将 `services/marketing-ai` 加入 `PYTHONPATH` 后导入 `marketing_ai.engine`。公开函数及返回值见 `packages/contracts/platform-api.md`。

## 两种运行方式

未配置 `MARKETING_AI_API_KEY` 时，始终返回 `generation_mode: template`。模板使用商家已确认营销资料及实际关联商品/课程，输出渠道、日程、预算、价格/履约和购买/报名入口；缺失资料明确警告。此模式不是远程大模型结果，不证明宣传效果。

有密钥时必须设置 `MARKETING_AI_MODEL`，通过 OpenAI 兼容 HTTPS `POST /chat/completions` 生成 JSON。`MARKETING_AI_BASE_URL` 默认 `https://api.openai.com/v1`；超时默认 30 秒、限制 1—60 秒；`MARKETING_AI_MAX_OUTPUT_TOKENS` 默认 2000、限制 64—4000。配置或提供方失败、截断、错误 JSON、结构无效、超预算或有危险承诺时抛出不含内部信息的 `RuntimeError`，不会悄悄返回模板并假称成功。一次函数调用只发一次请求，重试由后端持久化任务管理。

只接受 HTTPS 提供方地址，拒绝含用户信息/查询/片段的地址并拒绝重定向，以避免将授权头发往跳转地址。读取响应有大小上限。密钥仅用于请求头；错误不回显提供方正文、密钥和内部异常。用量记录 prompt/completion/total tokens、model、elapsed_ms；没有返回 token 用量的兼容提供方记为 0，不能将其作为准确账单。服务端管理者须为提供方账户设预算限制。

## 事实边界

资料只保留当前 workspace、`confirmed is True`、`usage_scope == marketing` 的记录。workspace_id 不同的资料被过滤；外商家的 campaign/offering/plan/analytics 直接拒绝。契约允许资料不带 workspace_id：此时调用方必须已经按已认证 workspace 从数据库筛选，AI 函数不是成员授权层。来源链接只作为引用，模块不会下载链接或文件。商家文本进入独立数据消息；不启用工具或代理执行。

策划预算总额不能超过活动预算，日期必须处于活动区间，生成渠道必须来自活动渠道。生成来源由服务器过滤后的资料固定，模型不能另造引用。自动检查提示绝对收益/效果承诺和缺少确认资料的非遗身份；这不替代人工事实、版权和宣传合规审核。模型仍可能给出未被规则发现的错误，因此方案/素材须经商家审核，后端绑定具体版本和来源快照。

复盘 observations/facts 均由实际 stats 数值确定；收入扣除退款重新计算，不相信模型或外部传入的 net_revenue。未知归因收入单列；无完整成本不称利润，无对照不称因果。模型只能提供假设、验证方法和下一轮建议，其 facts 字段完全丢弃。没有记录时明确不能评价成效。

## 素材类型

- copy：可编辑文案和段落。
- poster：海报文字、详情、CTA 和版式建议；不是图片生成服务，导出由后端渲染可审查的海报文件。
- script：30 秒镜头脚本及项目详情。

## 验证

`./.venv/Scripts/python.exe -m pytest tests/ai -q`

提供方测试替换 HTTP 传输边界，保留 JSON 解析、筛选和校验的真实实现；不消耗真实模型额度。当前未使用真实商家模型密钥验证质量、网络连通或实际计费。
