# 抖音发布插件 — 按钮及输入框真实 DOM 对照表

> **使用说明**：请在抖音创作者中心页面中，右键 → 检查，找到对应元素的 HTML 标签，粘贴到下方「真实 DOM」列中。
> 已确认的项目已标注 ✅，待填写的标注为 `【待填写】`。
> **代码对应**：选择器定义见 `src/plugins/community/douyin/selectors.py`，步骤实现见 `src/plugins/community/douyin/steps/`。

---

## 步骤1：导航首页

> 此步骤通过 URL 直接导航；会检测风控/登录弹窗，对应 `Selectors.SECURITY["RISK_MODAL"]`。

| 功能               | 真实 DOM（关键属性）                                                                 | 状态 |
| ------------------ | ------------------------------------------------------------------------------------ | ---- |
| 风控/账号异常弹窗  | `div[role='dialog']:has-text('账号异常')` 或 `.semi-modal:has-text('封禁')`          | ✅   |
| 登录验证弹窗       | 页面内出现「扫码登录」「短信登录」「密码登录」「验证码登录」等文案即视为未登录      | ✅   |

---

## 步骤2：进入发布页

> 对应 `Selectors.HOME["PUBLISH_VIDEO_BTN"]` / `PUBLISH_IMAGE_BTN`。

| 功能               | 真实 DOM（关键属性）                                                                                                                                 | 状态 |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| "发布视频"入口     | `<div class="btn-OkpBsP video-_cFVs8">`，内层 `div.title-HvY9Az` 文案「发布视频」、`div.desc-hHzqYm`「支持常用格式，推荐mp4、webm」                 | ✅   |
| "发布图文"入口     | `<div class="btn-OkpBsP image-k7R89r">`（结构同视频入口，文案为「发布图文」）                                                                         | ✅   |

---

## 步骤3：上传文件

> 对应 `Selectors.PUBLISH` 中 `UPLOAD_BTN`、`FILE_INPUT`、`IMAGE_FILE_INPUT`、`VIDEO_UPLOAD_SUCCESS_MARKER`（视频上传成功）、`IMAGE_THUMBNAIL`。

| 功能             | 真实 DOM（关键属性）                                                                 | 状态 |
| ---------------- | ------------------------------------------------------------------------------------ | ---- |
| 上传区域容器     | `<div class="container-drag-VAfIfu" role="presentation">`                            | ✅   |
| 上传视频按钮     | `<button class="semi-button semi-button-primary container-drag-btn-k6XmB4">上传视频` | ✅   |
| 上传图文按钮     | `<button class="semi-button semi-button-primary container-drag-btn-k6XmB4">上传图文` | ✅   |
| 视频文件 input   | `div.container-drag-VAfIfu input[type='file']`（accept 含 video）                     | ✅   |
| 图片文件 input   | `div.container-drag-VAfIfu input[type='file'][accept*='image']`（multiple）            | ✅   |
| 视频上传成功标识 | 出现「重新上传」区域即表示视频已上传：`<label class="upload-btn-PdfuUv">`（内为 `input.upload-btn-input-UY_qeY` + 上传图标按钮，右侧文案「重新上传」） | ✅   |
| 图文上传完成标识 | 缩略图 `img` 或 `div[class*='thumb'] img`                                                                 | ✅   |

---

## 步骤4：作品描述

> 对应 `Selectors.PUBLISH["TITLE_INPUT"]`、`DESC_EDITOR`、`DESC_PLACEHOLDER`。作品简介支持含话题：与单发页一致，仅「#关键词+空格」视为已确认话题，整段 description 原样填入此编辑区域。

| 功能              | 真实 DOM（关键属性）                                                                                              | 状态 |
| ----------------- | ----------------------------------------------------------------------------------------------------------------- | ---- |
| 标题输入框        | `<input class="semi-input semi-input-default" placeholder="填写作品标题，为作品获得更多流量">`                    | ✅   |
| 描述/简介编辑区域 | `<div class="zone-container editor-kit-container editor" data-placeholder="添加作品简介" contenteditable="true">`   | ✅   |

---

## 步骤5：封面设置（视频/图文）

> 视频为 CoverVideoStep，图文为 CoverImageStep。对应 `Selectors.PUBLISH` 中 `COVER_BTN`、`COVER_MODAL`、`COVER_HORIZONTAL_BTN`、`COVER_CONFIRM_BTN`、`COVER_UPLOAD_BTN`、`COVER_FILE_INPUT`、**`COVER_SUCCESS_INDICATOR`**。步骤完成标准：**仅当主页面出现「封面效果检测通过」时判定成功**。弹窗内顺序：先点「设置横封面」（图1→图2）→ 再点「完成」（图2→图3，点击后触发封面检测）。

| 功能                      | 真实 DOM（关键属性）                                                                                    | 状态 |
| ------------------------- | ------------------------------------------------------------------------------------------------------- | ---- |
| "选择封面"入口（在竖封面3:4/横封面4:3 上方） | `<div class="filter-k_CjvJ"><svg class="semi-icons semi-icons-image semi-icons-extra-large">...</svg><div class="title-wA45Xd">选择封面</div></div>`，下方为「竖封面3:4」或「横封面4:3」文案；选择器：`div.filter-k_CjvJ:has(svg.semi-icons.semi-icons-image):has(div.title-wA45Xd:has-text('选择封面'))` | ✅   |
| 封面弹窗容器              | `div.dy-creator-content-modal-content`                                                                  | ✅   |
| 弹窗内"设置横封面"按钮    | `<span class="semi-button-content">设置横封面</span>`（点击后弹窗切换为横封面设置状态，图2）             | ✅   |
| 弹窗内"完成"按钮          | `<span class="semi-button-content">完成</span>`（点击后触发封面检测，主页面显示图3「封面效果检测通过」） | ✅   |
| 弹窗内"上传封面"区域      | `div.semi-upload-drag-area`（拖拽/点击上传）                                                             | ✅   |
| 弹窗内封面文件 input      | `input.semi-upload-hidden-input[type='file']`                                                            | ✅   |
| **封面效果检测通过**（步骤完成标准） | `<div class="container-QVu5RH success-container-vgr8T8 coverChecking-fmip_6"><svg class="success-icon-o2IUWQ">...</svg><span>封面效果检测通过</span></div>`，可选选择器：`div.coverChecking-fmip_6` 或 `div.success-container-vgr8T8:has(span:has-text('封面效果检测通过'))` | ✅   |

---

## 步骤6：扩展信息 / 选择音乐

> 视频链：ExtraInfoCommonStep（扩展信息）；图文链：SelectMusicStep（选择音乐）→ ExtraInfoCommonStep。扩展信息当前较轻，音乐相关 DOM 如需补充可在此增加。

| 功能     | 真实 DOM（关键属性） | 状态 |
| -------- | -------------------- | ---- |
| 扩展信息 | 暂无需固定 DOM       | -    |
| 选择音乐 | 【待填写】           | ❌   |

---

## 步骤7：发布设置

> 对应 `Selectors.SETTINGS`（PRIVACY_*、SAVE_*、PUBLISH_NOW、PUBLISH_SCHEDULE、SCHEDULE_INPUT）。**定时时间**：已废弃弹窗方式，改为在定时时间输入框内按「年/月/日/时/分」五段分别选中并输入（格式 `YYYY-MM-DD HH:mm`，长度 16），利用输入框支持单段删除与替换的特性设置定时时间。

| 功能                  | 真实 DOM（关键属性）                                                                                 | 状态 |
| --------------------- | ---------------------------------------------------------------------------------------------------- | ---- |
| "公开" 单选按钮       | `<label class="radio-d4zkru"><input class="radio-native-p6VBGt" value="0" checked> 公开`             | ✅   |
| "好友可见" 单选按钮   | `<label class="radio-d4zkru"><input class="radio-native-p6VBGt" value="2"> 好友可见`                  | ✅   |
| "仅自己可见" 单选按钮 | `<label class="radio-d4zkru"><input class="radio-native-p6VBGt" value="1"> 仅自己可见`               | ✅   |
| "允许" 保存权限       | `<label class="radio-d4zkru"><input class="radio-native-p6VBGt" value="1" checked> 允许`              | ✅   |
| "不允许" 保存权限     | `<label class="radio-d4zkru"><input class="radio-native-p6VBGt" value="0"> 不允许`                    | ✅   |
| "立即发布" 单选按钮   | `<label class="radio-d4zkru one-line-pe7juM"><input class="radio-native-p6VBGt" value="0"> 立即发布`  | ✅   |
| "定时发布" 单选按钮   | `<label class="radio-d4zkru one-line-pe7juM"><input class="radio-native-p6VBGt" value="1"> 定时发布` | ✅   |
| 定时时间输入框        | `input[format='yyyy-MM-dd HH:mm']` 或 `input.semi-input[placeholder='日期和时间']`；步骤7 在框内分段选中并输入年/月/日/时/分 | ✅   |

### 步骤7 - 定时时间选择器弹窗（已废弃）

> **已废弃**：不再通过弹窗选日期时间。现采用在时间输入框内分段选中并输入（年 `[0:4]`、月 `[5:7]`、日 `[8:10]`、时 `[12:14]`、分 `[15:17]`）。以下为历史参考，对应选择器已从 `Selectors.SETTINGS` 中移除。

| 功能           | 真实 DOM（关键属性）                                                                 | 状态     |
| -------------- | ------------------------------------------------------------------------------------ | -------- |
| 弹窗容器       | `.semi-datepicker-dropdown` 或 `[class*='datepicker'][class*='dropdown']`             | 已废弃   |
| 上月按钮       | `.semi-datepicker-prev-month` 或 `[class*='datepicker'] [class*='prev']`              | 已废弃   |
| 下月按钮       | `.semi-datepicker-next-month` 或 `[class*='datepicker'] [class*='next']`               | 已废弃   |
| 年月标题       | 展示「2026年3月」的标题元素，用于解析当前展示月                                       | 已废弃   |
| 日期单元格     | 当前月下的日期格（建议带 `data-date='YYYY-MM-DD'` 或文本为日期数字）                   | 已废弃   |
| 时间触发区域   | 底部显示时间（如「08:00」），点击后展开时间选择                                       | 已废弃   |
| 时间面板-小时  | 时间选择面板内的小时列表项                                                           | 已废弃   |
| 时间面板-分钟  | 时间选择面板内的分钟列表项                                                           | 已废弃   |

---

## 步骤8：点击发布

> 对应 `Selectors.PUBLISH["SUBMIT_BTN"]`、`Selectors.VERIFY["SUCCESS_TOAST"]`、`Selectors.SECURITY["PUBLISH_TOAST_ERROR"]` 等。

| 功能               | 真实 DOM（关键属性）                                                                 | 状态 |
| ------------------ | ------------------------------------------------------------------------------------ | ---- |
| 发布按钮（底部红色） | `<button class="button-dhlUZE primary-cECiOJ fixed-J9O8Yw" ...>发布</button>`，选择器带 `:has-text('发布')` 唯一匹配，避免误点「同时发布」等 | ✅   |
| "发布成功" Toast   | `span.semi-toast-content-text:has-text('发布成功')` 或 `.semi-toast-success:has-text('发布成功')` | ✅   |
| "发布失败" Toast   | `.semi-toast:has-text('失败')` 或 `.semi-toast:has-text('错误')`                     | ✅   |
| 操作频繁/风控 Toast| `.semi-toast:has-text('频繁')` 或 `.semi-toast:has-text('太快')`                     | ✅   |
| 需选封面弹窗       | `.semi-modal:has-text('封面')`                                                       | ✅   |
| 需补充信息弹窗     | `div[role='dialog']:has-text('补充信息')`                                              | ✅   |
