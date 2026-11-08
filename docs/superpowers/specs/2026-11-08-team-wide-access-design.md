# 三人全目录协作与公开仓库兼容

用户已明确确认：允许MiniDiva8、donghaochen45-pixel、zhupaifan三人修改前端、后端、AI和公共代码，保留PR评审和测试。实际GitHub权限已均为write；无待接受邀请、无main分支保护、无ruleset。

采用显式scope_mode=team-wide；成员module/paths仅作为主责参考。未配置该模式的旧策略继续按partitioned执行，未知模式拒绝。所有人仍禁止提交凭据、运行数据、依赖、缓存及Git元数据，仍须使用本人Issue/分支并保留冲突检查。

仓库已公开，增加visibility=public配置；脚本校验精确仓库身份与配置可见性，不再硬编码只允许private。默认未配置时仍为private，可见性不符拒绝；不由普通命令更改仓库可见性。

team-wide下跨目录不要求scope:shared-approved，普通PR至少一名其他成员对当前head批准，CI必须通过。旧partitioned模式和两人共享评审逻辑保留兼容。本次策略迁移本身按main旧共享策略及批准Issue发布，保留人工合并。

根AGENTS明确废止所有子模块历史“只修改本模块”的权限限制；各模块技术/数据规范保留。更新共同任务提示及CODEOWNERS。迁移PR只改旧策略允许的共享文件与本人模块说明，不借改head配置绕过base策略。已有队友分支由各自同步main，不修改他人分支。

验收：真实CLI三名成员跨目录save、公开仓库在线start/board/publish/check-pr边界mock、路径/凭据保护、旧模式兼容、当前head评审与CI、冲突无损；完整unittest及三cloneGit仿真；实际GitHub草稿PR及CI，明确生效条件。
