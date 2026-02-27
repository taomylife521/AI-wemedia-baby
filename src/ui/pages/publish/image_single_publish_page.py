from ..common.placeholder_page import PlaceholderPage
try:
    from qfluentwidgets import FluentIcon
except ImportError:
    pass

class ImageSinglePublishPage(PlaceholderPage):
    """单个图文发布页面"""
    def __init__(self, parent=None):
        icon = FluentIcon.PHOTO if 'FluentIcon' in globals() else None
        super().__init__("单个图文发布", "发布单个图文或文章内容", icon, parent)
