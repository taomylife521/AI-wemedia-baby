from typing import List, Dict, Any, Optional
from qfluentwidgets import FluentIcon, NavigationItemPosition

class NavigationConfig:
    """导航栏配置管理"""
    
    @staticmethod
    def get_items(
        batch_feature: bool = False,
        data_center: bool = False,
        interaction: bool = False,
        subscription: bool = False
    ) -> List[Dict[str, Any]]:
        """获取导航菜单配置"""
        
        items = [
            # 1. 工作台
            {
                "route_key": "workspace_page",
                "icon": FluentIcon.HOME,
                "text": "工作台",
                "position": NavigationItemPosition.TOP,
                "selectable": True
            },
            
            # 2. 账号库 (父级)
            {
                "route_key": "account_container",
                "icon": FluentIcon.PEOPLE,
                "text": "账号库",
                "selectable": False,
                "selectable": False,
                "expanded": False, # [Fix] 禁用默认展开以防止UI初始化时的布局重叠问题
                "children": [
                    {
                        "route_key": "account_page",
                        "icon": FluentIcon.PEOPLE,
                        "text": "账号管理",
                    },
                    {
                        "route_key": "account_group_page",
                        "icon": FluentIcon.FOLDER,
                        "text": "账号组管理",
                    }
                ]
            },
            
            # 3. 发布管理 (父级)
            {
                "route_key": "publish_container",
                "icon": FluentIcon.SEND,
                "text": "发布管理",
                "route_key": "publish_container",
                "icon": FluentIcon.SEND,
                "text": "发布管理",
                "selectable": True, # [Fix] 设置为True以确保显示，点击逻辑由手风琴处理覆盖
                "children": [
                    {
                        "route_key": "publish_list_page",
                        "icon": FluentIcon.VIEW,
                        "text": "发布列表",
                    },
                    {
                        "route_key": "publish_records_page",
                        "icon": FluentIcon.HISTORY,
                        "text": "发布记录",
                    }
                ]
            },
            
            # 4. 视频发布 (父级)
            {
                "route_key": "video_publish_container",
                "icon": FluentIcon.VIDEO,
                "text": "视频发布",
                "selectable": False,
                "children": [
                    {
                        "route_key": "single_publish_page",
                        "icon": FluentIcon.MOVIE,
                        "text": "单个视频",
                    }
                ]
            },
            
            # 5. 图文发布 (父级)
            {
                "route_key": "image_publish_container",
                "icon": FluentIcon.PHOTO,
                "text": "图文发布",
                "selectable": False,
                "children": [
                    {
                        "route_key": "image_single_publish_page",
                        "icon": FluentIcon.EDIT,
                        "text": "单个图文",
                    }
                ]
            },
        ]

        # 动态注入 - 批量视频
        if batch_feature:
            NavigationConfig._append_child(items, "video_publish_container", {
                "route_key": "batch_publish_page",
                "icon": FluentIcon.LIBRARY,
                "text": "批量视频",
            })

        # 动态注入 - 批量图文
        if batch_feature:
            NavigationConfig._append_child(items, "image_publish_container", {
                "route_key": "image_batch_publish_page",
                "icon": FluentIcon.TILES,
                "text": "批量图文",
            })

        # 6. 数据中心 (Pro)
        if data_center:
            items.append({
                "route_key": "data_center_page",
                "icon": FluentIcon.PIE_SINGLE,
                "text": "数据中心",
                "selectable": True
            })

        # 7. 评论及私信 (Pro)
        if interaction:
            interaction_group = {
                "route_key": "interaction_container",
                "icon": FluentIcon.CHAT,
                "text": "评论及私信",
                "selectable": False,
                "children": [
                    {
                        "route_key": "comment_page",
                        "icon": FluentIcon.PEOPLE,
                        "text": "评论管理",
                    },
                    {
                        "route_key": "private_message_page",
                        "icon": FluentIcon.MESSAGE,
                        "text": "私信管理",
                    }
                ]
            }
            items.append(interaction_group)

        # 8. 浏览器
        items.append({
            "route_key": "browser_page",
            "icon": FluentIcon.GLOBE,
            "text": "浏览器",
            "selectable": True
        })

        # 9. 文件管理
        items.append({
            "route_key": "file_page",
            "icon": FluentIcon.FOLDER,
            "text": "文件管理",
            "selectable": True
        })
        
        # 10. 底部菜单
        # 个人中心
        if subscription:
            items.append({
                "route_key": "personal_center_page",
                "icon": FluentIcon.CERTIFICATE,
                "text": "个人中心",
                "position": NavigationItemPosition.BOTTOM,
                "selectable": True
            })

        # 设置
        items.append({
            "route_key": "settings_page",
            "icon": FluentIcon.SETTING,
            "text": "设置",
            "position": NavigationItemPosition.BOTTOM,
            "selectable": True
        })

        return items

    @staticmethod
    def _append_child(items: List[Dict], parent_key: str, child: Dict):
        """辅助方法：向指定父级添加子项"""
        for item in items:
            if item.get("route_key") == parent_key:
                if "children" not in item:
                    item["children"] = []
                item["children"].append(child)
                return

    @staticmethod
    def get_accordion_mapping() -> Dict[str, str]:
        """获取手风琴父子映射 (Parent Key -> First Child Key)"""
        return {
            "account_container": "account_page",
            "publish_container": "publish_list_page",
            "video_publish_container": "single_publish_page",
            "image_publish_container": "image_single_publish_page",
            "interaction_container": "comment_page",
        }
    
    @staticmethod
    def get_child_to_parent_mapping() -> Dict[str, str]:
        """获取子页面到父级的映射 (用于跳转时自动展开)"""
        return {
            # 发布列表
            "publish_list_page": "publish_container",
            "publish_records_page": "publish_container",
            # 视频
            "single_publish_page": "video_publish_container",
            "batch_publish_page": "video_publish_container",
            # 图文
            "image_single_publish_page": "image_publish_container",
            "image_batch_publish_page": "image_publish_container",
            # 互动
            "comment_page": "interaction_container",
            "private_message_page": "interaction_container",
            # 账号库
            "account_page": "account_container",
            "account_group_page": "account_container",
        }
