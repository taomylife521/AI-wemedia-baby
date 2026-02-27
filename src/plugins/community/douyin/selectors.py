"""
抖音插件 CSS/XPath 选择器集中配置
文件路径: src/plugins/community/douyin/selectors.py
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
    # 2. 视频内容发布 (Video Publish)
    # ==========================================
    PUBLISH = {
        # 上传视频按钮触发区域 (兜底使用)
        "UPLOAD_BTN": [
            "button[class*='upload']", 
            "[class*='upload-btn']", 
            "div[class*='upload']", 
            "button:has-text('上传视频')"
        ],
        # 文件输入框 (最稳定)
        "FILE_INPUT": [
            "input[type='file'][accept*='video']",
            "input[type='file']", 
            "[class*='upload-input']"
        ],
        # 重新上传按钮 (用于判断是否上传且转码初期已就绪)
        "REUPLOAD_BTN": [
            "button:has-text('重新上传')", 
            "div:has-text('重新上传')",
            "button:has-text('更换视频')"
        ],
        # 上传成功文本标识 (非绝对基准)
        "UPLOAD_SUCCESS_TEXT": "text=\"上传成功\"",
        
        # 标题输入框
        "TITLE_INPUT": [
            "input[placeholder*='标题']", 
            "textarea[placeholder*='标题']", 
            "input[class*='title']", 
            ".title-input input"
        ],
        # 描述/内容编辑器区域 (div[contenteditable])
        "DESC_EDITOR": [
            "div[contenteditable='true']",
            "textarea[placeholder*='描述']", 
            "textarea[placeholder*='简介']", 
            ".desc-editor", 
            ".content-editor",
            ".zone-container.editor"
        ],
        "DESC_PLACEHOLDER": [
            "div[data-placeholder='填写作品相关动态，让更多人看到~']",
            "div[data-placeholder*='描述']"
        ],
        
        # 话题设置与@列表
        "TOPIC_INPUT": ["input[placeholder*='话题']", "[class*='topic-input']"],
        "AT_LIST_CONTAINER": [".at-list-container"],
        
        # 封面设置按钮
        "COVER_BTN": [
            "button:has-text('选择封面')", 
            "button:has-text('封面')", 
            "[class*='cover-btn']"
        ],
        
        # 最终发布按钮
        "SUBMIT_BTN": [
            "button:has-text('发布')", 
            "button:has-text('立即发布')", 
            "button[class*='publish']", 
            ".publish-btn",
            "button[class*='Publish']"
        ]
    }


    # ==========================================
    # 3. 滑块、风控及异常状态探测 (Anti-Risk & Exceptions)
    # ==========================================
    SECURITY = {
        # 风控拦截/封号提示模态框 
        "RISK_MODAL": [
            "div[role='dialog']:has-text('账号异常')",
            ".semi-modal:has-text('封禁')",
            ".login-verify-dialog",
            "div:has-text('请登录')"
        ],
        # 发布拦截或业务报错
        "PUBLISH_TOAST_ERROR": [
            ".semi-toast:has-text('失败')",
            ".semi-toast:has-text('错误')"
        ],
        "PUBLISH_TOAST_FREQ": [
            ".semi-toast:has-text('频繁')",
            ".semi-toast:has-text('太快')"
        ],
        "PUBLISH_MODAL_COVER": [
            ".semi-modal:has-text('封面')"
        ],
        "PUBLISH_MODAL_SUPPLEMENT": [
            "div[role='dialog']:has-text('补充信息')"
        ]
    }


    # ==========================================
    # 4. 发布结果验证特征 (Verification)
    # ==========================================
    VERIFY = {
        # 作品管理页面标识元素
        "MANAGE_PAGE_INDICATOR": [
            "div:has-text('作品数据')",
            "div:has-text('稿件管理')",
            ".manage-content",
            "div[class*='Manage']"
        ],
        # 直接浮出的成功文案
        "SUCCESS_TOAST": "text=\"发布成功\""
    }
