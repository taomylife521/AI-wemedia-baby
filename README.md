# 媒小宝 (WeMediaBaby) 🚀

> **一款面向自媒体创作者的专业多平台批量发布与管理工具 (v2.0 架构升级版)**
>
> 采用现代化 Fluent Design 风格，深度集成的浏览器引擎，为您提供极致的发布体验与安全保护。

---

## 📦 版本说明

| 版本                  | 功能                                     | 许可证        |
| :-------------------- | :--------------------------------------- | :------------ |
| **Community Edition** | 抖音单视频发布、账号管理、基础 UI        | AGPLv3 (开源) |
| **Pro Edition**       | 批量发布、多平台支持、定时发布、高级调度 | 商业许可      |

### Community Edition 开源功能

- ✅ 抖音账号登录与管理
- ✅ 抖音单视频发布
- ✅ 本地文件管理
- ✅ 浏览器反检测管理
- ✅ Fluent Design 界面

### Pro Edition 专业功能

- 🔒 视频/图文批量发布
- 🔒 快手、小红书、视频号平台
- 🔒 定时发布与任务调度
- 🔒 断点续传与任务队列
- 🔒 多账号矩阵管理

---

## 🌟 核心特性

- **多账号矩阵管理**：支持抖音等热门平台，Cookie 深度加密保护，防关联检测。
- **批量发布流水线**：支持视频、图文内容的流水线式批量处理，大幅提升分发效率。
- **智能任务调度**：内置定时任务队列，支持断点续发与发布日志监控。
- **极简现代化 UI**：基于 PySide6-Fluent-Widgets 打造，支持 Windows 11 视觉效果与深色模式。
- **双轨制安全打包**：支持 Nuitka 机器码级混淆保护，确保商业应用安全性。

---

## 🚀 5分钟快速上手

### 1. 环境准备

- **操作系统**: Windows 10/11 (64位)
- **Python 环境**: Python 3.12 (建议) 或 3.10+
- **浏览器**: 必须安装 **Google Chrome** (用于视频发布与抗指纹检测)
- **必要工具**: 已安装 [Git](https://git-scm.com/)

### 2. 快速安装

```powershell
# 克隆项目
git clone <repository-url>
cd wemedia-baby

# 创建并激活虚拟环境 (推荐使用项目内置标准路径 .venv)
python -m venv .venv
.venv\Scripts\activate

# 安装项目依赖
pip install -r requirements.txt

# 安装特殊 UI 组件库 (必须通过 git 安装以保证适配性)
pip install git+https://github.com/zhiyiYo/PySide6-Fluent-Widgets.git@PySide6
```

### 3. 初始化并启动

```powershell
# 初始化本地数据库结构
python src/infrastructure/storage/database_init.py

# 启动应用程序
python main.py
```

---

## 📂 项目结构规范

```bash
wemedia-baby/
├── .venv/                  # 项目专属虚拟环境
├── config/                 # 平台选择器与系统配置
├── data/                   # 数据库与加密存储池
├── docs/                   # 标准化技术文档 (Architecture, Build, etc.)
├── resources/              # 静态资源 (Icons, StyleSheets)
├── scripts/                # 打包与运维自动化脚本
├── src/                    # 核心 4 层 DDD 架构源代码
│   ├── domain/           # 业务模型与领域事件
│   ├── services/         # 核心业务逻辑服务
│   ├── infrastructure/   # 基础设施 (DB, Network, Browser)
│   ├── plugins/          # [开源] 平台插件 (Douyin, Kuaishou)
│   ├── plugins_pro/      # [闭源] 高级插件 (Xiaohongshu, Wechat) - Git Submodule
│   └── ui/               # MVVM 界面实现
├── tools/                  # 外部执行工具 (FFmpeg, Browsers)
└── main.py                 # 统一入口程序
```

---

## 🛡️ 技术栈方案

| 组件           | 技术选型                    | 优势                       |
| :------------- | :-------------------------- | :------------------------- |
| **GUI 架构**   | PySide6 + Fluent-Widgets    | 商业级视觉效果，LGPL 协议  |
| **异步引擎**   | qasync (asyncio + Qt)       | 解决复杂逻辑下的界面卡死   |
| **浏览器方案** | QWebEngineView + Playwright | 混合动力，兼顾交互与自动化 |
| **存储层**     | SQLite (aiosqlite)          | 轻量、异步、零维护         |
| **代码保护**   | Nuitka (C++ 级编译)         | 防反编译，性能提升         |

---

## 📖 详细文档指引

- [技术架构文档](docs/01总文档/01技术文档.md)
- [开源策略方案](docs/01总文档/02开源策略方案.md)
- [软件打包实施方案](docs/01总文档/03软件打包实施方案.md)

---

## 🛠️ 打包指令

我们提供预设的打包脚本，建议使用：

- **快速测试**: `.\scripts\build_fast.ps1` (产出至 `dist/fast`)
- **正式发布**: `.\scripts\build_nuitka.ps1` (产出至 `dist/secure`)
- **一键清理**: `.\scripts\clean_project.ps1` (删除 build/dist/缓存，方便备份)

---

**特别说明**：本项目目前处于 v2.0.0 架构升级阶段，插件化体系已落地。如有疑问，请通过 Email 联系开发者。
