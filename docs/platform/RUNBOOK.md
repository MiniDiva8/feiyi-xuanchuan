# 非遗商家 AI 营销平台 · 本地使用与部署

当前产品代码位于此仓库的 apps/web、services/api 和 services/marketing-ai。原协作脚本、团队成员与 PR 规则保留。实际测试结果单独见 VERIFICATION.md，不将本地验证写成线上部署或商家经营效果。

## Windows 启动

要求：Python 3.12+、Node.js 22.12+、npm，联网安装依赖。

```powershell
cd D:\Codex\Projects\HeritageMarketingCollab
powershell -ExecutionPolicy Bypass -File scripts\start-platform.ps1 -Install
```

这里的 ExecutionPolicy Bypass 只作用于本次脚本进程，不修改全局策略。若系统允许直接执行脚本，可用 `./scripts/start-platform.ps1 -Install`。

依赖和前端构建已完成时：

```powershell
powershell -File scripts\start-platform.ps1
```

打开 http://127.0.0.1:8010 。首次使用注册自己的账号与商家空间，没有默认账号或共享密码。未填任何业务数据时看板为零；没有内置的虚假业绩。Ctrl+C 停止服务，重启后数据仍保留。开发前端可在 apps/web 运行 npm run dev，Vite将 /api 代理到8010。

## 完成一轮真实业务

1. 建立商家资料：填写非遗事实、品牌说明或素材，记录可核查来源和使用范围。只有商家确认且允许营销使用的资料进入生成。
2. 建立商品或体验课程：维护价格、库存/名额、地点、交付安排和已有购买/预约入口。此平台不处理支付或自动扣库存。
3. 创建活动：选目标、受众、周期、预算和渠道，关联真实商品或课程。
4. 生成策划：核对依据、预算和履约安排，商家确认后才能生成各渠道素材。
5. 审核素材：检查标题、正文、文化事实及承接入口。修订产生新版本，旧审批不覆盖新内容。已确认资料发生变化，相关内容需要重新核对。
6. 导出已批准内容，在渠道手动发布；登记真实作品链接和发布时间。下载素材不等同渠道发布成功。
7. 按活动录入经营台账或导入CSV。先预览错误再确认；重复数据不会重复累计。没有可靠来源的成交标为未知归因。
8. 查看传播、意向和经营指标，生成复盘。观察事实、原因假设、调整建议和数据不足分别显示。创建下一轮会保留历史，重新策划和确认。

## 真实模型配置

无API密钥时提供明确标记的模板草稿；它不是大模型调用结果。已有审核、发布登记、数据和分析功能仍可使用。

复制 .env.example 为 .env，在本机编辑服务器端配置。不要在聊天、前端、截图或Git中提交密钥：

- MARKETING_AI_API_KEY：本人可用的模型API密钥。
- MARKETING_AI_BASE_URL：可信兼容服务的 HTTPS API基础地址。
- MARKETING_AI_MODEL：账号实际有权调用的模型名称。
- MARKETING_AI_TIMEOUT_SECONDS / MARKETING_AI_MAX_OUTPUT_TOKENS：调用超时与输出上限。

示例模型名仅作配置示例，不证明账号具备权限。重新启动服务生效。配置了模型但请求失败时显示失败，不悄悄替换成模板冒充成功。输入商家资料属于用户内容，不能让其中的指令改变系统权限或调用其他商家的数据。

## 数据、备份与权限

本地SQLite文件为 .data/platform.db，上传文件由服务端随私有数据库保存，运行目录和环境文件均已忽略。不要删除 .data 或把真实数据库加入版本库。数据库包含商家资料与用户数据，应控制本机访问并保留备份。

SQLite在线备份可运行：

```powershell
.\.venv\Scripts\python.exe scripts\backup-platform.py
```

备份默认位于 .data/backups，使用SQLite备份API保持一致性。将备份另存到自己管理的独立介质；同磁盘备份不能应对磁盘故障。恢复前停止服务并保留当前数据库副本。

用户只能读取自己所属商家空间；新增空间不获得其他商家权限。所有者管理成员；编辑者维护业务，审核者确认版本。新增成员使用已注册账号，不发送邮件邀请。

## 容器部署配置

仓库提供 Dockerfile.platform 和 compose.yaml：构建前端，运行 API + PostgreSQL17，数据库和文件使用持久卷。首次设置 .env 的 POSTGRES_PASSWORD，使用足够长的随机URL安全密码；不提供可直接上线的默认密码。

```text
docker compose up --build -d
```

默认仅监听服务器本机127.0.0.1:8010。真实对外服务需要自管HTTPS反向代理、正确的 TRUSTED_ORIGINS、SESSION_SECURE=true、数据库备份、访问控制与监控。不要直接把开发端口暴露公网。首次数据库结构由应用创建，后续结构演进须有正式迁移和恢复演练。本次没有申请域名、购买服务或部署线上环境。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend tests/ai tests/e2e -q
python -m unittest discover -s tests -v
cd apps\web
npm run build
```

浏览器验收使用项目内Playwright和本机Edge，脚本及截图写到 .artifacts。实际执行、数量及限制见 VERIFICATION.md。配置存在不等于Docker引擎和PostgreSQL部署已通过验证。

## 能力边界

渠道当前采用导出与手动发布登记；真实自动发布和自动经营数据同步仍需相应平台准入、授权和适配。购买、预约使用商家已有入口；不代收款、不办理退款、不执行课程核销交易。AI辅助检查不替代商家对文化事实、素材授权和宣传内容的审核。指标没有可靠归因时不会写成AI带来的成交；不把实收减推广支出称为利润。
