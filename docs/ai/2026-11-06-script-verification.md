# 抖音拍摄脚本验收 · Issue #17

## 代码与授权起点

- 成员 c，原生 GitHub 与 gh API 均核验为 zhupaifan；Issue #17 开放且唯一负责人为 zhupaifan，不复用复盘 Issue #15。
- 实际 `git fetch origin main`：`2132fa30164d984e5de92c79420783ee6bd73dbd`。
- PR #12（渠道管理）仍为开放草稿，head `8e765d8f088e057c6da7704ebf2879c5d16e0c7f`。
- PR #14（前端工作台）仍为开放草稿，head `224f264171ae1ae425269f7a26db256ff92b5d6d`。
- PR #16（既有复盘）仍为开放草稿，head `b6344997d2f42f7d769eaacf4d7fdd1299afda38`，已核验包含前两项依赖。
- 当前仓库 API 返回 public，标准 start 因要求 private 报 `[VISIBILITY]`。用户明确授权保持公开状态并使用已有原生流程；没有修改可见性、认证或检查脚本。
- 使用 `start --member c --issue 17 --slug douyin-shooting-script --native --native-issue-verified` 从实际 main 建立新分支，再仅在新分支 fast-forward 到上述 #16 SHA。新草稿 PR 以 `codex/zhupaifan/issue-15-evidence-based-review` 为 base。
- 本轮增量仅限 AI 实现、AI 测试与 AI 文档。没有改动或推送依赖分支，未将整条依赖链合并到 main。

## 实际验证

Python 3.12.14；在仓库外独立虚拟环境安装现有 `services/api/requirements.txt`，没有改依赖声明。经营数据、商家、资料和模型响应均为虚构测试输入，不使用真实模型密钥。

| 检查 | 实际结果 |
| --- | --- |
| 改动前 #16 快照，AI/后端/端到端基线 | 63 passed，3 subtests passed |
| 改动后 `python -m pytest tests/ai tests/backend tests/e2e -q -o faulthandler_timeout=30` | 87 passed，60 subtests passed，18.08秒；1项既有 Starlette/httpx 弃用提示 |
| 新脚本单测 | 15项；商品/课程、缺失与明确零值、精确保留价格/库存、长资料不截成口播、已批准方向、跨商家过滤、父级/方案/渠道约束、模板标识、模型编排及错误路径 |
| 新脚本实际 API 测试 | 9项；商品/课程 × 模板/模拟模型的生成→列表→编辑→审核→TXT/HTML导出、版本保留和来源变更失效；资料不足；四类模型失败任务持久化 |
| 模型验证 | 模拟 HTTP 提供方，实际走既有客户端、JSON解析及校验；错误字段、伪造事实/链接、重复或缺失镜头、非数值/布尔/非有限/超大时间、重叠/空隙/越界、口播过长均拒绝；无静默模板回退 |
| 既有复盘 | 原有 engine/review/review_api 回归保留通过，包含销售/报名与零记录场景 |
| 现有页面读取逻辑 | 已读代码：素材卡完整显示 `a.body`，CSS保留换行且可滚动；编辑器用 `selectedAsset.body`，TXT/HTML导出用持久化正文。实际路由结果已验证，不等同浏览器点击验收 |
| 虚构示例 | 两份文档由同一 `generate_asset(kind=script)` 模板实际生成，含全部正文 |
| `git diff --check` 与本轮路径范围 | 通过；增量路径由已有 `policy_scope` 校验为成员 c 范围 |

后续提交时运行仓库 save 自带的协作检查。对 main 的 preflight 与远端检查以草稿 PR 的实测记录为准；本次依赖 base 不是 main，不能把增量范围通过描述为整条依赖链的 main 检查通过。

## 未验证与后续配合

- 未运行本轮真实浏览器、真实模型、真人拍摄/试读、真实抖音入口权限或线上部署；不证明实际营销效果。
- 模型本轮仅在事实绑定的候选中选择和编排，不开放事实文案自由改写；真实提供方对此约束的遵循率及效果仍待验收。
- 当前界面和接口即可使用。a/b 后续若增加结构化分镜编辑或自动剪辑，应先解决人工编辑 `body` 后旧 `content.storyboard` 仍为生成快照的问题；详见 [使用与交接说明](DOUYIN-SCRIPTS.md)。
- main 尚未包含依赖，现有 CI 仅匹配 main 的配置不能证明本依赖草稿 PR 通过云端检查。保留草稿、其他成员评审及人工合并，不自动合并或部署。
