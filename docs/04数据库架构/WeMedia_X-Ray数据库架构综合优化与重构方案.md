# WeMedia X-Ray 数据库架构综合优化与重构方案

经过对项目数据库物理层实现（`database.py`）、表结构抽象（`database_init.py`）以及业务域（如发布管道、GUI视图层）的全面穿透式分析，并横向评估了当前 Python 异步生态的主流方案。特制定本综合优化与重构方案，旨在彻底解决目前数据库底层的性能隐患与代码耦合痛点。

---

## 🎯 一、 核心痛点回顾与诊断

当前项目在数据库访问层暴露出以下三大核心痛点：

### 1. 结构性反模式：Smart UI (智能视图) 现象严重

系统内的 GUI 页面（如 `publish_records_page.py` 或各种 Dialog）以及底层后台任务（如 `PublishPipeline`）都在直接获取 `AsyncDataStorage` 单例并硬编码执行查表操作。

- **后果**：UI 严重绑定底层表结构，导致代码极其难以进行单元测试；业务代码中随处可见对原始 `dict` 结构的手工取值，极易引发 KeyError；缺乏统一的缓存或权限拦截层。

### 2. 职责臃肿：上帝类与脆弱的维护脚本

`AsyncDataStorage` 承载了全系统十几个表的增删改查动作，代码膨胀至千行以上。

- **后果**：每次新增功能都要修改这个核心类，违反单一职责原则。表结构的修补完全依赖在 `database_init.py` 中写 `Try-Catch` 拦截添加字段，在系统不断迭代的背景下，极易在用户覆盖安装时导致数据表损坏。

### 3. 安全与稳定隐患：多点并发下缺乏事务重试

系统虽然做到了完全的异步 I/O，并且在单条查询级别做了 SQLite `database is locked` 的指数退避，但是在更为复杂的跨表操作 `execute_transaction` 中却缺失了这一机制。

- **后果**：当高并发（例如多端并发写入发布日志或刷新账号状态）时，复杂事务经常遭遇写锁直接崩溃，导致数据断层。

---

## 🛠️ 二、 核心技术选型策略

**总体结论：坚守 SQLite 引擎，全面引入 Tortoise ORM 和彻底的分层抽象。**

本项目作为跨平台的桌面自动化/自媒体分发工具，**免安装、零配置的 SQLite 是无可替代的最优解**。我们要改善的是与 SQLite 交互的“方式”。

### 为什么选择 Tortoise ORM？

基于项目的完全 `asyncio` 异步特性，放弃手动拼接 SQL，我们选择引入 **Tortoise ORM**：

1. **纯血异步**：无需复杂的同步/异步上下文切换配置，天生支持高并发。
2. **极简体验**：类似 Django ORM 的查询体验，将千行 SQL 缩编为几十行代码。
3. **Aerich 自动迁移工具**：完美解决表结构升级时的噩梦，自动生成类似 Alembic 且更轻量化的迁移脚本，保证用户升级时的数据库安全。

---

## 🏗️ 三、 架构分层蓝图 (三层架构与依赖倒置)

为了彻底根治 UI 和底层数据库纠缠不清的问题，整个数据流向将被严格限制：**UI 层 → Service 层 → Repository 层 → ORM 模型 → SQLite DB**。

### 1. 数据访问层 (Repository + ORM)

- 取消 `AsyncDataStorage` 上帝类，按业务拆分出专用的 `AccountRepository`、`PublishRecordRepository`、`SubscriptionRepository`。
- Repository 提供类型安全的方法，内部封装 Tortoise ORM 操作。
- 业务获取到的不再是字典，而是纯正的 Domain Models 或 Pydantic/DataClass DTO 实体。

### 2. 业务逻辑层 (Service / MVVM)

- `PublishService` 和 `AccountService` 负责承接 UI 或后台请求。
- 负责所有的权限管控、并发缓存过滤以及领域事件（Event Bus）派发。

### 3. 视图层 (UI/Dialog) 与 任务引擎 (Pipeline)

- **绝对禁令**：禁止 UI 文件中出现任何直接或间接的 SQL 语句和数据访问代理类的获取。
- UI 只关心渲染：向 Service 请求列表进行展示；向 Service 提交表单完成处理。

---

## 🚀 四、 核心场景改造落地设计

### 场景 A：发布管道 (Publish Pipeline) 重构

**当前**：`PublishPipeline` 查出待发布数据，一边执行 Playwright 发布，一边用 `data_storage.update_publish_record_status` 改状态。前端 UI 也轮询查库更新列表状态。
**重构方案**：

1. Pipeline 执行完单个更新后，调用 `PublishService.update_status()` (内部委托给 Repository 执行事务写入)。
2. `PublishService` 状态改变后，通过内存内的**事件总线 (EventBus)** 或 **PyQt 信号机制** 发射 `TaskStatusChangedEvent`。
3. 前端界面监听事件，仅局部重绘对应数据行的颜色/文字，彻底消灭前端无意义的 DB 轮询。

### 场景 B：账号管理 (Account Management) 重构

**重构方案**：
建立强类型的 `AccountDTO`，使用 `AccountRepository` 将 Cookie 文件路径的读写和 `Tortoise` ORM 对象做一层自动适配转换，向上层呈现完美的统一接口。所有的界面端直接拿到的就是 `[AccountDTO(platform='douyin', status='online'), ...]`。

---

## 🗓️ 五、 分步实施与割接路线图 (Roadmap)

鉴于现有系统盘根错节，不可直接推翻重来。必须采取**双轨并行，灰度替换**或者分阶段重构的方式：

### 第一阶段：基建与打样 (Infrastructure & Prototype) 🏁

- 引入 `tortoise-orm` 和 `aerich`。
- 将目前 `database_init.py` 中的表结构全部用 Python Class 映射为 Tortoise Model。
- 选择最独立、功能单一的 **订阅系统 (Subscription)** 作为白老鼠，完成 `SubscriptionRepository` 和 Service 的改造。
- 生成第一个自动迁移版本（Migration Revision）。

### 第二阶段：核心抽离 (Core Refactoring) ⚙️

- 将包含几百行方法的 `AsyncDataStorage` 进行解体。
- 逐步建立 `AccountRepository` 和 `PublishRecordRepository`。
- 重构 `AccountService` 和后台的 `PublishPipeline`，将所有裸字典操作转化为 Model/DTO 操作。

### 第三阶段：视图层肃清 (UI Cleanup) 🧹

- 逐个清理 `src/ui/pages/` 层下的所有页面，砍掉所有的 `data_storage = service_locator.get(AsyncDataStorage)`。
- 为视图层接上各种 ViewModel，并在 ViewModel 里处理后端 Service 派发的数据变更事件，实现 UI 的响应式刷新。
- **最终里程碑**：废弃并安全删除 `database.py` 和 `database_init.py`。架构全面现代化升级完成！
