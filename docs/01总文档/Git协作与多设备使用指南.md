# Git 项目协作与多设备使用指南

## 1. 项目架构说明

本项目采用了 **主仓库（开源） + 子模块（私有）** 的混合架构：

- **主仓库**：`wemedia-baby` (Public)
  - 包含项目的核心框架、基础服务和开源插件。
- **子模块**：`src/plugins_pro` -> `wemedia-baby-pro` (Private)
  - 包含所有付费版（Pro）插件、敏感业务逻辑和 Key 配置。
  - 作为独立的 Git 仓库管理，但在主项目中通过 `git submodule` 引用。

---

## 2. 换电脑/新环境配置流程

当您在新的电脑上克隆项目时，需按以下步骤操作以完整获取代码：

### 2.1 第一步：克隆主仓库

```bash
git clone https://github.com/chitang818/wemedia-baby.git
cd wemedia-baby
```

此时你会发现 `src/plugins_pro` 目录是空的，这是正常的。

### 2.2 第二步：初始化并拉取私有子模块

> **注意**：执行此步前，请确保您的新电脑已配置好 GitHub 权限（SSH Key 或 Token），且该账号有权访问 privte 仓库 `wemedia-baby-pro`。

```bash
# 初始化子模块配置
git submodule init

# 拉取子模块代码（会提示输入 GitHub 账号密码，除非已配置 SSH）
git submodule update
```

或者使用一键命令：

```bash
git submodule update --init --recursive
```

---

## 3. 日常开发与推送流程

### 3.1 场景一：只修改了主仓库代码

如果您的修改**不涉及** `src/plugins_pro` 目录下的文件：

```bash
git add .
git commit -m "fix: 修复了主程序的某个 bug"
git push origin main
```

### 3.2 场景二：修改了 `src/plugins_pro` 下的代码（重要！）

由于 `src/plugins_pro` 是一个独立的 Git 仓库，您必须先提交它，再更新主仓库的引用指针。

**Step 1: 进入子模块提交代码**

```bash
cd src/plugins_pro

# 检出主分支（默认是游离状态 detached HEAD，开发前建议先 checkout）
git checkout main

git add .
git commit -m "feat: 更新了 Pro 版插件功能"

# 推送到私有仓库
git push origin main
```

**Step 2: 回到主仓库更新引用**
子模块提交后，主项目会检测到 `src/plugins_pro` 的 commit id 发生了变化，需要提交这个变化。

```bash
cd ../..  # 回到 wemedia-baby 根目录

git status
# 您会看到：modified: src/plugins_pro (new commits)

git add src/plugins_pro
git commit -m "chore: update pro submodule reference"
git push origin main
```

---

## 4. 常见问题排查

### Q1: `src/plugins_pro` 里面是空的？

**A**: 说明子模块未更新。请在项目根目录运行：

```bash
git submodule update --init --recursive
```

### Q2: 在 `src/plugins_pro` 里 git push 失败？

**A**:

1.  检查是否有权限访问 `wemedia-baby-pro` 仓库。
2.  检查是否处在 `detached HEAD` 状态。如果是，请先切回分支：
    ```bash
    git checkout main
    ```
    如果已经在游离状态下提交了代码，可以新建一个临时分支合并：
    ```bash
    git checkout -b temp-branch
    git checkout main
    git merge temp-branch
    git branch -d temp-branch
    ```

### Q3: 团队成员拉取代码后 `src/plugins_pro` 报错或版本不对？

**A**: 每次 `git pull` 主仓库后，如果别人更新了子模块指针，您需要同步更新子模块：

```bash
git pull origin main
git submodule update  # 这一步很重要，同步子模块到主仓库指向的版本
```
