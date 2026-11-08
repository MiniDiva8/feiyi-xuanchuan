# 前端优化验证记录 · 2026-11-08

## 交付范围与基线

独立分支 codex/MiniDiva8/issue-25-marketing-workspace，Issue #25。业务依赖为 PR #22 的 33d913723090798bae65ed13b972c16b09fbaa5c，包含同事的脚本、事实核对、复盘和此前前后端工作。本轮没有更改这些依赖的源码、分支或审批。

只改 apps/web/、docs/frontend/、tests/frontend/。继续使用既有 React/TypeScript/Vite 和接口，不新增依赖。

## 实际验证

| 检查 | 命令或操作 | 结果 |
| --- | --- | --- |
| 前端逻辑 | npm test --prefix apps/web | 17 项通过；含完整正文保真、嵌套依据0/null/false、未知键、严重级别与消息保留、商家路由与版本导出 |
| 生产构建 | npm run build --prefix apps/web | TypeScript 与 Vite 通过 |
| 业务依赖基线 | Python pytest tests/ai tests/backend tests/e2e -q -o faulthandler_timeout=30 --tb=short | 156 项及60个子测试通过；1项既有 Starlette/httpx 弃用提示。本轮未改这些模块 |
| 真实营销闭环 | tests/e2e/browser_acceptance.py --base-url http://127.0.0.1:8011 | 注册、资料、产品、策划审核、素材审核/PNG、人工发布登记、指标/CSV、复盘、下一轮、刷新恢复共10阶段通过 |
| 渠道账号 | tests/frontend/channels_acceptance.py | 创建、两次快照、粉丝差额、未知值、展开历史、375px与无页面错误通过 |
| 实拍海报 | tests/frontend/photo_posters_acceptance.py | 真实上传、照片权利确认、模板、预览、手机、保存待审新版本、审批、实际PNG下载通过 |
| 异步边界 | tests/frontend/async_regressions.py | 取消上传不串编辑对象；切活动加载失败不保留旧发布资格 |
| 首次准备清单 | tests/frontend/preparation_regressions.py | 空商家、桌面/手机、读取失败、重试与状态刷新通过 |
| 界面回归 | tests/frontend/interface_regressions.py，全部8个case | navigation、channel-edit、poster-size、poster-upload、knowledge-search、form-layout、workspace-route、modal-shortcut 全通过 |
| 全站实际布局 | tests/frontend/marketing_workspace_acceptance.py | 57项通过：11个业务视图 × 375/768/1440px、两个空首页场景、11类弹窗 × 375/768px；无页面错误或外部请求 |
| 内容安全与阅读 | 独立全mock Edge 检查 | 正文空格/CRLF/空行完整、HTML只作文字、不显示旧storyboard、历史版本导出限制、编辑正文权威、嵌套证据和长消息在375/768/1440不截断或横溢 |
| 跨活动待审回归 | tests/frontend/pending_review_regression.py | 旧实现实测失败；修正入口后通过，可选择另一活动并进入其待审策划 |
| 独立代码审查 | 全变更审查与修复复审 | 发现1项P2并已修复；最终需求与质量均通过 |

57项布局检查同时检查关键操作可滚动触达、弹窗不超出屏幕、字段具有可访问标签、Escape可关闭，以及海报缩略图与原生模板选择一致且不会误提交表单。桌面和手机截图实际打开检查。

## 审查修复

概览 pending_review 汇总所有活动的方案和素材，原新增入口却进入默认活动的发布档案，不能保证找到提醒的版本。修正为“选择活动审核”，进入活动列表后由商家选择对应活动；没有将单活动发布页冒称为跨活动待审列表。

回归使用“最新活动没有待审、另一活动有待审方案”的场景。旧构建点击提醒后活动卡数量期望2、实际0；修正后可选正确活动，看到对应待审方案和可用审批按钮。

## 证据与数据隔离

- QA服务仅监听127.0.0.1:8011，使用本任务忽略目录下的独立SQLite数据库；没有载入正常工作区的 .env。
- QA进程显式清空真实模型key；数据、账号、价格、指标、照片均为合成验收材料，不代表商家或经营效果。
- 完整生成截图、结果JSON和临时研究图片保存在忽略的 .artifacts/marketing-workspace、platform-20261031、channels-browser、photo-browser、task2-content 等目录。
- docs/frontend/previews/2026-11-08-* 为精简后的实际界面截图；没有复制参考产品照片作为本项目素材。
- 初期测试脚本的同URL刷新、必填字段可访问名称和屏外关闭按钮等待问题只修了测试定位/等待，不修改产品来迎合测试。种子创建后专门刷新首页，保证最终有数据截图准确。

## 未验证与交付边界

手机检查使用真实Edge中的模拟视口，没有手机实机验收。没有部署公网、合并依赖链、执行真实渠道发布、订单/支付同步或真实模型质量验收。前端独立审查不替代同伴对当前GitHub head的审批。

依赖仍未合入main，已有主分支工作流不能自动视为本依赖PR的远端CI。协作预检结果及上传head以PR中的实际记录为准，不把本地检查冒称为远端CI通过。
