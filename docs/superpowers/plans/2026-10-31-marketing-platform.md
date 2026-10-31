# 非遗商家营销平台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 将现有三人协作脚手架补全为可本地使用的真实营销闭环产品。
**Architecture:** React工作台调用FastAPI，SQLAlchemy持久化所有私有记录和审核历史；AI模块通过严格输入契约生成有来源的内容与复盘。浏览器不保存私有业务数据库。
**Tech Stack:** React, TypeScript, Vite, FastAPI, SQLAlchemy, SQLite/PostgreSQL, pytest, browser E2E.
**Spec:** docs/superpowers/specs/2026-10-31-marketing-platform-design.md

## Global Constraints
- 保留已有协作脚本和团队规则。用户本次授权实现所有模块，不变更他人账户/权限，不自动推送、合并或部署。
- 私有资料、文件、任务、导出和统计必须由服务端校验商家成员权限。
- 审核绑定具体不可变版本；事实/假设/模板草稿分别显示。
- 中文界面，无凭据入库或日志，无假数据冒充真实经营效果。

## Review Focus
- 错误商家ID/文件ID不得泄露数据：后端隔离测试。
- 修订后的新版本不得复用审批：后端工作流测试。
- 重复及非法CSV不能污染指标：导入测试。
- 模型超时/缺配置必须准确展示：AI测试和前端反馈。
- 首次空数据库、重启和过期会话：端到端测试。

### Task 1: 固定共享接口和后端业务
**Files:** packages/contracts/openapi.md; services/api/app/{main,db,models,security,schemas,workflow,metrics}.py; tests/backend/test_platform.py; services/api/requirements.txt.
**Interfaces:** /api/auth/*; /api/workspaces; /api/workspaces/{id}/{overview,knowledge,offerings,campaigns,plans,assets,publications,metrics,reviews,audit,tasks}. JSON契约先落盘，再分工。
- [x] 写测试并运行确认缺失行为。
- [x] 实现登录/商家隔离、CRUD、不可变版本审核、持久化文件与导出、事务CSV预检和导入、看板。
- [x] 测试隔离、版本、幂等、错误、重启持久化。

### Task 2: AI与证据约束
**Files:** services/marketing-ai/marketing_ai/{__init__,engine}.py; tests/ai/test_engine.py.
**Interfaces:** generate_plan(context), generate_asset(context), build_review(context) return JSON; model config only from environment.
- [x] 先测试资料限制、缺配置模板标记、统计事实边界。
- [x] 实现模板生成、可配置真实模型适配、超时与用量记录、事实检查与复盘。
- [x] 运行全部AI测试，向后端交付稳定契约。

### Task 3: 中文产品工作台
**Files:** apps/web/{package.json,index.html,vite.config.ts,src/*}; tests/frontend/*.
**Interfaces:** 使用Task1契约，cookie鉴权；管理/审核/导出均实际调用API。
- [x] 编写关键端到端场景，首次确认缺失界面。
- [x] 实现总览、资料库、产品课程、活动策划/素材、审核发布、数据复盘、设置，加载/空/错误状态，响应式布局。
- [x] 类型检查与生产构建。

### Task 4: 联调、交付和独立审查
**Files:** compose.yaml; .env.example; scripts/start-platform.ps1; docs/platform/{RUNBOOK,VERIFICATION}.md; README.md.
- [x] 本地安装依赖和启动，执行完整端到端闭环与浏览器视觉检查。
- [x] 回归既有协作测试；独立审查权限和审核/数据约束，修复实际发现。
- [x] 输出启动入口、真实验证结果、配置步骤和未接入的外部能力。
