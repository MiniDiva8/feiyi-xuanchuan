# 独立审查与修复记录

2026-10-30 对初版完整套件进行一次独立只读审查。审查者独立重跑初版 38 项测试通过，随后补充复现出 4 项 Important 问题；没有 Critical 或 Minor 项。

| 问题 | 修复 | 回归证据 |
|---|---|---|
| 已暂存的外模块改动被工作树反向还原隐藏，save 会顺带提交 | 分开读取索引与工作树范围，合并检查所有路径；部分暂存文件保留原状并要求显式处理 | hidden_staged 与 partially_staged 两项由失败转为通过 |
| fetch URL 正确但 pushurl 指向其他仓库 | 校验每一个有效 fetch/push URL，拒绝多个或非目标地址；离线只接受同一个本地 bare remote | push_urls 测试由失败转为通过 |
| main 新跟踪的文件覆盖本地被忽略配置 | start/sync 先核对忽略路径碰撞，merge 再加 --no-overwrite-ignore | start/sync 的 ignored_file 测试均由失败转为通过 |
| 手动/主分支 CI 跳过策略仍可冒充 PR 通过 | PR gate 要求正确 workflow + pull_request event；主分支/手动汇总名改为 collab-main-quality | ci_cannot 与 different_workflow 测试由失败转为通过 |

修复后的完整套件结果见 verification.md。没有通过真实远程合并来证明这些本地测试。

审查未判定：三账户 Cloud 访问、Cloud 原生 Create PR、GitHub-hosted Windows/Linux 执行、评审通知与分支保护生效。这些需要实际账号操作或远程授权，继续独立标记状态。
