"""
抖音插件 CSS/XPath 选择器集中配置
文件路径: src/plugins/community/douyin/selectors.py

所有发布步骤相关选择器均为「唯一匹配」，与 docs/抖音发布插件DOM对照表.md 一致。
步骤失败时可根据报错定位到对应键名，对照文档更新 DOM 即可快速排查。
"""

class Selectors:
    # ==========================================
    # 1. 登录与基础信息提取 (Login & User Info)
    # ==========================================
    LOGIN = {
        # 二维码元素
        "QR_CODE": [".qr-code", "[class*='qr']", "[class*='QRCode']", "canvas[class*='qr']", ".login-qrcode"],
        # 用户名/手机号输入框
        "USERNAME_INPUT": ["input[type='text']", "input[name*='user']", "input[placeholder*='手机']", "input[placeholder*='账号']"],
        # 密码输入框
        "PASSWORD_INPUT": ["input[type='password']"],
        # 登录按钮
        "LOGIN_BTN": ["button[type='submit']", "[class*='login-btn']", "button:has-text('登录')"],
    }
    
    USER_INFO = {
        # 用户昵称提取
        "NICKNAME": [
            ".user-info .nickname", 
            "[class*='user-name']", 
            "[class*='userName']", 
            ".user-info .name", 
            ".header-user-name", 
            ".semi-avatar-label",
            ".name-_lSSDc",
            "div.name-_lSSDc"
        ],
        # 用户头像提取
        "AVATAR": [
            "[class*='avatar']", 
            "img[class*='avatar']", 
            ".user-avatar img", 
            ".semi-avatar img"
        ]
    }
    
    # 登录检测关键 Cookie Name
    REQUIRED_COOKIES = ['sessionid', 'sessionid_ss']


    # ==========================================
    # 2. 首页入口与发布导航（唯一匹配，便于步骤失败时快速定位）
    # ==========================================
    HOME = {
        # 步骤2 唯一匹配：<div class="btn-OkpBsP video-_cFVs8"> 内 title-HvY9Az「发布视频」
        "PUBLISH_VIDEO_BTN": ["div.btn-OkpBsP.video-_cFVs8"],
        # 步骤2 唯一匹配：<div class="btn-OkpBsP image-k7R89r"> 发布图文
        "PUBLISH_IMAGE_BTN": ["div.btn-OkpBsP.image-k7R89r"],
        # 进入视频/图文发布页后的特征元素（用于步骤2 校验）
        "VIDEO_PUBLISH_PAGE_MARKERS": ["div.container-drag-VAfIfu"],
        "IMAGE_PUBLISH_PAGE_MARKERS": ["div.container-drag-VAfIfu"],
    }


    # ==========================================
    # 3. 视频/图文内容发布（唯一匹配，DOM 见 docs/抖音发布插件DOM对照表.md）
    # ==========================================
    PUBLISH = {
        "CONTENT_TYPE_TABS": ["div[role='tablist'] button:has-text('视频')"],
        "TAB_VIDEO": ["div[role='tablist'] button:has-text('视频')"],
        "TAB_IMAGE": ["div[role='tablist'] button:has-text('图文')"],
        # 步骤3 唯一匹配：<button class="semi-button semi-button-primary container-drag-btn-k6XmB4">上传视频
        "UPLOAD_BTN": ["button.container-drag-btn-k6XmB4"],
        "UPLOAD_IMAGE_BTN": ["button.container-drag-btn-k6XmB4"],
        # 步骤3 唯一匹配：div.container-drag-VAfIfu 内 input
        "FILE_INPUT": ["div.container-drag-VAfIfu input[type='file']"],
        "IMAGE_FILE_INPUT": ["div.container-drag-VAfIfu input[type='file'][accept*='image']"],
        # 步骤3 视频上传成功判定：出现「重新上传」区域即表示视频已上传（唯一匹配 DOM）
        # <label class="upload-btn-PdfuUv"> 内含 input[accept*='video'] + 上传图标按钮，文案「重新上传」
        "VIDEO_UPLOAD_SUCCESS_MARKER": ["label.upload-btn-PdfuUv"],
        "REUPLOAD_BTN": ["label.upload-btn-PdfuUv"],
        "IMAGE_THUMBNAIL": ["div.container-drag-VAfIfu div[class*='thumb'] img"],
        "UPLOAD_SUCCESS_TEXT": "text=\"上传成功\"",
        # 步骤4 唯一匹配：<input placeholder="填写作品标题，为作品获得更多流量">
        "TITLE_INPUT": ["input[placeholder='填写作品标题，为作品获得更多流量']"],
        # 步骤4 唯一匹配：<div class="zone-container editor-kit-container editor" data-placeholder="添加作品简介" contenteditable="true">
        "DESC_EDITOR": ["div.zone-container.editor-kit-container.editor[data-placeholder='添加作品简介'][contenteditable='true']"],
        "DESC_PLACEHOLDER": ["div[data-placeholder='添加作品简介']"],
        "TOPIC_INPUT": ["input[placeholder*='话题']"],
        "AT_LIST_CONTAINER": [".at-list-container"],
        # 步骤5 唯一匹配：选择封面入口（竖封面3:4/横封面4:3 上方的卡片，DOM 见对照表）
        # 真实 DOM：<div class="filter-k_CjvJ"><svg class="semi-icons semi-icons-image semi-icons-extra-large">...</svg><div class="title-wA45Xd">选择封面</div></div>
        "COVER_BTN": ["div.filter-k_CjvJ:has(svg.semi-icons.semi-icons-image):has(div.title-wA45Xd:has-text('选择封面'))"],
        # 步骤5 唯一匹配：封面弹窗容器
        "COVER_MODAL": ["div.dy-creator-content-modal-content"],
        "COVER_THUMB": ["div.dy-creator-content-modal-content img"],
        # 步骤5 唯一匹配：<span class="semi-button-content">设置横封面</span>
        "COVER_HORIZONTAL_BTN": ["span.semi-button-content:has-text('设置横封面')"],
        # 步骤5 唯一匹配：<span class="semi-button-content">完成</span>
        "COVER_CONFIRM_BTN": ["span.semi-button-content:has-text('完成')"],
        # 步骤5 唯一匹配：弹窗内上传区域
        "COVER_UPLOAD_BTN": ["div.semi-upload-drag-area"],
        "COVER_FILE_INPUT": ["input.semi-upload-hidden-input[type='file']"],
        # 步骤5 AI 方向唯一匹配：红框内第一个缩略图
        "COVER_AI_RECOMMEND_FIRST": ["div:has-text('AI智能推荐封面') >> img"],
        # 步骤5 完成标准：页面出现「封面效果检测通过」即视为封面设置成功（唯一匹配 DOM）
        # 真实 DOM：<div class="container-QVu5RH success-container-vgr8T8 coverChecking-fmip_6"> 内含 <span>封面效果检测通过</span>
        "COVER_SUCCESS_INDICATOR": [
            "div.container-QVu5RH.success-container-vgr8T8.coverChecking-fmip_6",
            "span:has-text('封面效果检测通过')",
        ],
        # 步骤8 唯一匹配：<button class="button-dhlUZE primary-cECiOJ fixed-J9O8Yw" style="width: 120px; height: 32px;">发布</button>
        "SUBMIT_BTN": ["button.button-dhlUZE.primary-cECiOJ.fixed-J9O8Yw:has-text('发布')"],
    }


    # ==========================================
    # 4. 风控及异常（唯一匹配，步骤1/8 用）
    # ==========================================
    SECURITY = {
        # 步骤1 唯一匹配：风控/账号异常弹窗
        "RISK_MODAL": ["div[role='dialog']:has-text('账号异常')"],
        "PUBLISH_TOAST_ERROR": [".semi-toast:has-text('失败')"],
        "PUBLISH_TOAST_FREQ": [".semi-toast:has-text('频繁')"],
        "PUBLISH_MODAL_COVER": [".semi-modal:has-text('封面')"],
        "PUBLISH_MODAL_SUPPLEMENT": ["div[role='dialog']:has-text('补充信息')"],
    }

    # ==========================================
    # 5. 发布结果验证（唯一匹配）
    # ==========================================
    VERIFY = {
        "MANAGE_PAGE_INDICATOR": ["div:has-text('作品数据')"],
        # 步骤8 唯一匹配：发布成功 Toast
        "SUCCESS_TOAST": "span.semi-toast-content-text:has-text('发布成功')",
    }

    # ==========================================
    # 6. 发布设置（步骤7，唯一匹配 DOM 见对照表）
    # ==========================================
    SETTINGS = {
        # 谁可以看：<label class="radio-d4zkru"> 公开/好友可见/仅自己可见（value 0/2/1 唯一）
        "PRIVACY_PUBLIC": ["label.radio-d4zkru:has-text('公开')"],
        "PRIVACY_FRIEND": ["label.radio-d4zkru:has-text('好友可见')"],
        "PRIVACY_PRIVATE": ["label.radio-d4zkru:has-text('仅自己可见')"],
        # 保存权限：<label class="radio-d4zkru"> 允许/不允许
        "SAVE_ALLOW": ["label.radio-d4zkru:has-text('允许')"],
        "SAVE_DISALLOW": ["label.radio-d4zkru:has-text('不允许')"],
        # 发布时间：<label class="radio-d4zkru one-line-pe7juM"> 内 <input type="checkbox" class="radio-native-p6VBGt"> + <span>定时发布 </span>
        "PUBLISH_NOW": ["label.radio-d4zkru.one-line-pe7juM:has-text('立即发布')"],
        "PUBLISH_SCHEDULE": ["label.radio-d4zkru.one-line-pe7juM:has-text('定时发布') input.radio-native-p6VBGt"],
        # 定时时间输入框 <input format="yyyy-MM-dd HH:mm" placeholder="日期和时间">；步骤7 已改为在输入框内分段选中并输入（年/月/日/时/分），不再使用弹窗
        "SCHEDULE_INPUT": ["input[format='yyyy-MM-dd HH:mm']"],
    }
