# 分工、任务协调与 PR 规则

## 唯一协调来源
GitHub Issue 保存任务、负责人、路径范围、验收标准、依赖及阻塞；PR 保存代码、检查、评审和合并记录。
Cloud 环境和本地 clone 是各自的执行空间。不要用聊天口头声明或过期环境快照替代 GitHub 当前状态。

## 认领与并行
一个 Issue 只有一个 Assignee。开始前查看是否已有活跃 PR/分支；同一 Issue 不重复开多个实现任务。
默认分支：codex/<GitHub登录名>/issue-<编号>-<英文短名>。
建议分工为 a 前端、b 后端、c AI；可由团队通过共享配置 PR 调整。CODEOWNERS 的备份评审者不是额外模块作者。
大型功能拆成三条关联 Issue，先确定 packages/contracts/ 的契约，再分别实现。接口暂未确定的地方记录假设，不能擅自改别人的代码。
状态标签：status:ready、status:in-progress、status:blocked。状态更新在 GitHub 完成；脚本 board 读取 GitHub，不创建本地“全队状态数据库”。
Issue/标签不提供原子分布式锁。三人应避免同时对同一 Issue 开多个任务；普通 push 的并发拒绝不能被 force push 绕过。

## 推荐节奏
1. start 拉最新 main，创建本人的独立任务分支。
2. 小步实现，save 自动验证、暂存范围内文件、提交。
3. preflight 检查范围和 main 冲突；needs_sync 为 true 时 sync。
4. publish 普通 push，创建草稿 PR，请同伴审查。
5. 准备完毕后由作者在 GitHub 点击 Ready for review。新提交继续 publish 复用原 PR。
6. 至少一位同伴对当前 head 审批；共享改动要求另外两位。
7. check-pr 只读复核 Issue、路径、CI、最新 main、当前提交审批和 mergeability。
8. 合并人再次看 GitHub 当前检查，明确点击 Squash and merge；删除合并后的功能分支。
9. 新任务重新 fetch main，从新基线创建新分支。已有任务不会因别人合并而自动获得最新工作文件。

## 同步与冲突
sync 在当前人的任务分支上同步 main，保留已推送历史，不自动 rebase/强推。
冲突先由 merge-tree 发现，工作树不进入冲突状态。向相关负责人核对意图后再人工解决。
如果另一个人已修改共享契约，先同步和更新测试，再更新 PR。内容改动后的旧审批不覆盖新 head。
在 CI/PR 检查仍 pending、未知或失败时不合并；检查缺失也不是通过。

## 审查责任
默认前端由 zhupaifan 备份审查；后端由 MiniDiva8；AI 由 donghaochen45-pixel。
作者不能审批自己。CODEOWNERS 每个模块列出主负责人和备份评审者，避免只有作者本人有 Code Owner 身份造成无法审批。
共享改动由另外两位评审，先核对接口兼容、商家隔离与调用方影响，再看代码。
AI Review 可补充问题发现，但不计入团队真人审批数量。

## 自动化与强制的区别
脚本保护正常使用路径，CI 给出服务端检查结果。AGENTS.md、CODEOWNERS 和模板不是文件系统 ACL。
私有分支保护受 GitHub 计划限制。未启用保护时，有 write 权限的协作者仍可能直接操作 main；团队应遵守约定，不能声称已经技术上禁止。
有保护时也应保护 .github/、scripts/ 与 team.json 的修改并认真审查，避免移除检查本身。
