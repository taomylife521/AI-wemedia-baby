from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json
import asyncio
from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishPluginInterface, PublishResult, FormField

logger = logging.getLogger(__name__)


def _load_platform_config() -> Dict[str, Any]:
    """从 config/platforms/kuaishou.json 读取平台配置（含 anti_risk）。"""
    try:
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        path = project_root / "config" / "platforms" / "kuaishou.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("anti_risk") if isinstance(data.get("anti_risk"), dict) else {}
    except Exception:
        pass
    return {}

class KuaishouPublishPlugin(PublishPluginInterface):
    @property
    def platform_id(self) -> str:
        return "kuaishou"

    def get_form_schema(self, content_type: str = "video") -> List[FormField]:
        """返回发布表单定义"""
        schema = [
            FormField(name="title", label="标题", field_type="text", placeholder="输入视频标题"),
            FormField(name="description", label="描述", field_type="textarea", placeholder="输入作品描述..."),
            FormField(name="tags", label="话题", field_type="text", required=False, placeholder="话题, 用逗号隔开"),
        ]
        return schema

    async def publish(
        self,
        context: Page,
        file_path: str,
        metadata: Dict[str, Any]
    ) -> PublishResult:
        """执行快手自动发布流程"""
        page = context
        anti_risk_config = _load_platform_config()
        try:
            logger.info(f"开始执行快手自动发布: {file_path}")
            
            # 1. 跳转到具体的发布页 (快手侧边栏点击通常较繁琐，直接进入视频上传页)
            upload_url = "https://cp.kuaishou.com/article/publish/video"
            await page.goto(upload_url, wait_until="networkidle")
            
            # 检查是否由于未登录跳转
            if "login" in page.url or "signin" in page.url:
                return PublishResult(success=False, error_message="Cookie 已过期，请重新登录")

            # 发布层防风控：进入发布页后、上传前操作延迟
            try:
                from src.infrastructure.anti_risk.delays import operation_delay
                await operation_delay(page, metadata, anti_risk_config)
            except Exception:
                pass

            # 2. 上传视频
            logger.info("寻找快手上传按钮...")
            async with page.expect_file_chooser() as fc_info:
                upload_area = page.locator('input[type="file"], .upload-video, div[class*="upload"]').first
                try:
                    from src.infrastructure.anti_risk.human_like import human_click
                    await human_click(page, upload_area, metadata, anti_risk_config)
                except Exception:
                    await upload_area.click()
            
            file_chooser = await fc_info.value
            await file_chooser.set_files(file_path)
            
            # 3. 等待上传进度
            logger.info("视频正在上传，等待快手后台处理...")
            # 快手上传完成通常会出现“上传成功”或者进度条消失
            try:
                # 等待特定成功标志
                await page.wait_for_selector('div:has-text("上传完成"), .upload-success', timeout=180000)
                logger.info("快手文件上传完成")
            except Exception as e:
                # 即使没检测到文字，如果表单显示出来了也可以继续
                logger.warning(f"上传状态检测超时，尝试继续执行表单填写: {e}")

            # 步骤间间隔
            try:
                from src.infrastructure.anti_risk.delays import step_interval
                await step_interval(page, metadata, anti_risk_config)
            except Exception:
                pass

            # 4. 填写表单
            title = metadata.get("title", "")
            description = metadata.get("description", "")
            tags = metadata.get("tags", [])
            
            # 操作前延迟 + 拟人输入标题
            try:
                from src.infrastructure.anti_risk.delays import operation_delay
                await operation_delay(page, metadata, anti_risk_config)
            except Exception:
                pass
            title_selector = 'input[placeholder*="标题"], .title-input'
            title_input = page.locator(title_selector).first
            if await title_input.count() > 0 and title:
                try:
                    from src.infrastructure.anti_risk.human_like import human_type_text
                    await human_type_text(page, title_selector, title, metadata, anti_risk_config)
                except Exception:
                    await title_input.fill(title)
            
            # 描述与话题（contenteditable 保留逐字 type）
            desc_box = page.locator('div[contenteditable="true"], .description-input').first
            if await desc_box.count() > 0:
                try:
                    from src.infrastructure.anti_risk.human_like import human_click
                    await human_click(page, desc_box, metadata, anti_risk_config)
                except Exception:
                    await desc_box.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                full_desc = description
                if tags:
                    for tag in tags:
                        full_desc += f" #{tag}"
                await desc_box.type(full_desc, delay=30)
                logger.info("已填写作品描述")

            # 5. 点击发布（操作延迟 + 拟人点击）
            try:
                from src.infrastructure.anti_risk.delays import operation_delay
                await operation_delay(page, metadata, anti_risk_config)
            except Exception:
                pass
            logger.info("执行最终发布...")
            submit_btn = page.locator('button:has-text("发布"), button:has-text("确认发布")').first
            await submit_btn.wait_for(state="visible", timeout=30000)
            try:
                from src.infrastructure.anti_risk.human_like import human_click
                await human_click(page, submit_btn, metadata, anti_risk_config)
            except Exception:
                await submit_btn.click()

            # 6. 结果确认
            try:
                # 跳转到内容管理页
                await page.wait_for_url("**/article/manage**", timeout=30000)
                logger.info("已进入管理页，发布成功")
                return PublishResult(success=True, publish_url=page.url)
            except:
                if await page.get_by_text("发布成功").count() > 0:
                    return PublishResult(success=True)

            return PublishResult(success=False, error_message="发布超时，请前往快手后台核实")

        except Exception as e:
            logger.error(f"快手发布插件异常: {e}", exc_info=True)
            return PublishResult(success=False, error_message=str(e))
