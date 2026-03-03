# 更新日志 (Changelog)

本文档记录 WeMedia X-Ray 项目的所有显著更改。
格式主要遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，并使用语义化版本 ([Semantic Versioning](https://semver.org/lang/zh-CN/))。

---

## [1.0.0] - 2026-03-03

正式发布 1.0.0 里程碑版本，基础软件功能体系完善。

### ✨ 新增 (Added)

- **平台支持**：抖音平台视频与图文发布功能正式接入。
- **UI交互**：集成 `PySide6-Fluent-Widgets` 现代化界面体验。
- **用户登录**：实现基于 `QWebEngineView` 的交互式动态环境隔离登录。
- **架构升级**：实现标准 4 层 DDD 架构（Domain, Services, Infrastructure, UI）。
- **底层驱动**：实现基于 `aiosqlite` 和 `aiohttp` 的异步数据库及网络操作框架。

### 🚀 优化 (Optimized)

- **双仓库架构**：优化整体代码架构，将项目拆分为开源主仓库 (`wemedia-baby`) 与闭源插件仓库 (`wemedia-baby-pro`)，通过 Git Submodule 挂载管理。
- **目录精简**：整理项目物理目录结构，清理冗余的逻辑层级嵌套。
- **统一规范**：完善 `.gitignore` 规则与项目核心配置文件。

---

> **历史占位版本说明**  
> `1.0.1` (2026-02-09) 与 `1.0.2` (2026-03-01) 曾作为开发过渡小版本，现已整合归入 1.0.0 稳定版统一发布特性中。
