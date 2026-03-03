# 步骤运行器 — 按顺序执行 step_01～step_08，处理重试与补救（如需要封面时重跑封面步骤）
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Any, Iterable, Optional, Sequence

from playwright.async_api import Page

from src.plugins.core.interfaces.publish_plugin import PublishResult

from ._base import BasePublishStep, NeedsAction, StepOutcome
from .step_08_submit import SubmitStep

logger = logging.getLogger(__name__)
# 用户可见的简洁日志（仅时间+步骤+状态），供发布日志界面展示；终端仍保留完整 logger 输出
USER_LOG = logging.getLogger("publish.user_log")

# 步骤类名 -> 用户界面显示名（严格按发布步骤顺序，便于用户阅读）
STEP_DISPLAY_NAMES = {
    "NavigateHomeStep": "导航首页",
    "EnterPublishEntryStep": "进入发布页",
    "UploadMediaStep": "上传视频/图文",
    "MetadataFillStep": "作品描述",
    "CoverVideoStep": "视频封面",
    "CoverImageStep": "图文封面",
    "ExtraInfoCommonStep": "扩展信息",
    "SelectMusicStep": "选择音乐",
    "PublishSettingsStep": "发布设置",
    "SubmitStep": "点击发布",
}

# 主链 8 阶段顺序（用于输出 [步骤X/8 ...]），同一阶段可能在 video/image 分支表现为不同 Step
MAIN_PHASES = [
    ("NavigateHomeStep",),
    ("EnterPublishEntryStep",),
    ("UploadMediaStep",),
    ("MetadataFillStep",),
    ("CoverVideoStep", "CoverImageStep"),
    ("SelectMusicStep", "ExtraInfoCommonStep"),  # 图文会先选音乐再扩展信息；视频通常直接扩展信息
    ("PublishSettingsStep",),
    ("SubmitStep",),
]

_STEP_TO_PHASE_INDEX: Dict[str, int] = {}
for idx, group in enumerate(MAIN_PHASES, start=1):
    for step_cls in group:
        # 允许同一 step 名映射到第一个出现的阶段（ExtraInfoCommonStep 会落在步骤6）
        _STEP_TO_PHASE_INDEX.setdefault(step_cls, idx)


def _step_display_name(step_name: str) -> str:
    return STEP_DISPLAY_NAMES.get(step_name, step_name)


def _phase_prefix(step_name: str) -> str:
    """返回形如 [步骤3/8 xxx] 的前缀；无法映射时回退为 [步骤 xxx]。"""
    display = _step_display_name(step_name)
    idx = _STEP_TO_PHASE_INDEX.get(step_name)
    if idx is None:
        return f"[步骤 {display}]"
    return f"[步骤{idx}/8 {display}]"


@dataclass
class RunnerConfig:
    """步骤链运行配置"""

    # 每个步骤失败时的最大重试次数（网络/卡顿等可重试，便于提高成功率）
    max_step_retries: int = 3
    # 步骤重试间隔（秒）
    step_retry_delay_seconds: float = 1.5
    # Submit 补救后重试提交的最大次数
    max_submit_retries: int = 2
    screenshot_on_error: bool = True
    screenshot_dir: str = "debug/screenshots/douyin"
    log_selector_probe: bool = True


class StepRunner:
    """负责执行步骤链，并对 NeedsAction 进行闭环处理。"""

    def __init__(
        self,
        page: Page,
        file_path: str,
        metadata: Dict[str, Any],
        config: Optional[RunnerConfig] = None,
        action_handlers: Optional[Dict[str, Callable[[], Sequence[BasePublishStep]]]] = None,
    ):
        self.page = page
        self.file_path = file_path
        self.metadata = metadata
        self.config = config or RunnerConfig()
        self.action_handlers = action_handlers or {}

        self._submit_retry_count = 0

    async def run(self, steps: Iterable[BasePublishStep]) -> PublishResult:
        """
        按顺序执行步骤链：仅当上一步返回成功时才执行下一步；
        任一步失败则通知主程序（返回 PublishResult(success=False)）并立即退出，不再执行后续步骤。
        每个步骤支持可配置重试（如最多 3 次），便于应对网络波动或卡顿，提高发布成功率并快速定位失败步骤。
        """
        step_list = list(steps)
        submit_indices = [i for i, s in enumerate(step_list) if isinstance(s, SubmitStep)]
        submit_index = submit_indices[0] if submit_indices else None
        max_retries = max(1, self.config.max_step_retries)
        retry_delay = max(0.0, self.config.step_retry_delay_seconds)

        i = 0
        while i < len(step_list):
            step = step_list[i]
            step_name = step.__class__.__name__
            last_failure: Optional[PublishResult] = None

            prefix = _phase_prefix(step_name)
            for attempt in range(1, max_retries + 1):
                if attempt > 1:
                    logger.info(f"--- 重试步骤: {step_name} (第 {attempt}/{max_retries} 次) ---")
                    USER_LOG.info(f"{prefix} ▶ 重试第{attempt}次")
                else:
                    logger.info(f"--- 正在执行步骤: {step_name} ---")
                    USER_LOG.info(f"{prefix} ▶ 执行中")

                # 发布层防风控：步骤前可选随机浏览（拟人化）
                try:
                    from src.infrastructure.anti_risk.human_like import optional_browse_before_action
                    await optional_browse_before_action(
                        self.page, self.metadata, self.metadata.get("anti_risk_config")
                    )
                except Exception:
                    pass

                try:
                    outcome: StepOutcome = await step.execute(self.page, self.file_path, self.metadata)
                except Exception as e:
                    last_failure = PublishResult(
                        success=False,
                        error_message=f"{step_name} 执行异常: {e}",
                    )
                    if attempt >= max_retries:
                        await self._diagnose(step_name, reason=f"exception_after_retries: {e}")
                        short = str(e)[:50] + ("..." if len(str(e)) > 50 else "")
                        USER_LOG.warning(f"{prefix} ✗ 失败: {short}")
                        return PublishResult(
                            success=False,
                            error_message=f"{step_name} 执行异常（已重试 {max_retries} 次）: {e}",
                            failed_step=step_name,
                        )
                    logger.warning(
                        f"{step_name} 第 {attempt} 次执行异常，剩余 {max_retries - attempt} 次重试: {e}",
                    )
                    await asyncio.sleep(retry_delay)
                    continue

                # None: 本步成功，仅此时才执行下一步
                if outcome is None:
                    USER_LOG.info(f"{prefix} ✓ 完成")
                    # 发布层防风控：步骤间间隔，避免固定节奏
                    try:
                        from src.infrastructure.anti_risk.delays import step_interval
                        await step_interval(
                            self.page, self.metadata, self.metadata.get("anti_risk_config")
                        )
                    except Exception:
                        pass
                    i += 1
                    break

                # NeedsAction: 闭环处理（执行 handler 后重试 Submit），不参与步骤重试
                if isinstance(outcome, NeedsAction):
                    handled = await self._handle_action(outcome)
                    if not handled:
                        await self._diagnose(step_name, reason=f"needs_action_unhandled: {outcome.action}")
                        USER_LOG.warning(f"{prefix} ✗ 失败: 需要补救但未实现")
                        return PublishResult(
                            success=False,
                            error_message=outcome.message or f"需要处理动作但未实现: {outcome.action}",
                            failed_step=step_name,
                        )

                    USER_LOG.info(f"{prefix} ▶ 需补救({outcome.action})，执行补救后重试")
                    handler = self.action_handlers.get(outcome.action)
                    if handler:
                        for h_step in handler():
                            h_name = h_step.__class__.__name__
                            logger.info(f"--- 补救步骤: {h_name} (for {outcome.action}) ---")
                            try:
                                h_outcome = await h_step.execute(self.page, self.file_path, self.metadata)
                            except Exception as e:
                                await self._diagnose(h_name, reason=f"handler_exception: {e}")
                                USER_LOG.warning(f"{_phase_prefix(h_name)} ✗ 失败: 补救步骤异常")
                                return PublishResult(success=False, error_message=f"{h_name} 执行异常: {e}", failed_step=h_name)

                            if isinstance(h_outcome, PublishResult):
                                if not h_outcome.success:
                                    await self._diagnose(h_name, reason=h_outcome.error_message or "failed")
                                    short = (h_outcome.error_message or "")[:50]
                                    USER_LOG.warning(f"{_phase_prefix(h_name)} ✗ 失败: {short}")
                                    return PublishResult(
                                        success=False,
                                        error_message=h_outcome.error_message,
                                        failed_step=h_name,
                                    )
                                return h_outcome
                            if isinstance(h_outcome, NeedsAction):
                                await self._diagnose(h_name, reason=f"nested_needs_action: {h_outcome.action}")
                                USER_LOG.warning(f"{_phase_prefix(h_name)} ✗ 失败: 返回未处理动作")
                                return PublishResult(
                                    success=False,
                                    error_message=h_outcome.message or f"{h_name} 返回未处理动作: {h_outcome.action}",
                                    failed_step=h_name,
                                )

                    if submit_index is not None:
                        if self._submit_retry_count >= self.config.max_submit_retries:
                            await self._diagnose(step_name, reason="submit_retry_exceeded")
                            USER_LOG.warning(f"{prefix} ✗ 失败: 提交重试次数已达上限")
                            return PublishResult(
                                success=False,
                                error_message=outcome.message or "已触发补救，但提交重试次数已达上限",
                                failed_step=step_name,
                            )
                        self._submit_retry_count += 1
                        logger.info(f"准备重试提交: {self._submit_retry_count}/{self.config.max_submit_retries}")
                        i = submit_index
                    else:
                        i += 1
                    break

                # PublishResult: 流程终止（成功直接返回；失败则重试本步）
                if isinstance(outcome, PublishResult):
                    if outcome.success:
                        USER_LOG.info(f"{prefix} ✓ 完成")
                        return outcome
                    last_failure = outcome
                    if attempt >= max_retries:
                        await self._diagnose(step_name, reason=outcome.error_message or "failed")
                        short = (outcome.error_message or "未知原因")[:50]
                        USER_LOG.warning(f"{prefix} ✗ 失败: {short}")
                        return PublishResult(
                            success=False,
                            error_message=f"{step_name} 失败（已重试 {max_retries} 次）: {outcome.error_message or '未知原因'}",
                            failed_step=step_name,
                        )
                    logger.warning(
                        f"{step_name} 第 {attempt} 次返回失败，剩余 {max_retries - attempt} 次重试: {outcome.error_message}",
                    )
                    await asyncio.sleep(retry_delay)
                    continue

                # 未知结果类型
                last_failure = PublishResult(
                    success=False,
                    error_message=f"{step_name} 返回未知结果类型，流程中断",
                    failed_step=step_name,
                )
                if attempt >= max_retries:
                    await self._diagnose(step_name, reason="unknown_outcome")
                    USER_LOG.warning(f"{prefix} ✗ 失败: 未知结果类型")
                    return last_failure
                logger.warning(f"{step_name} 返回未知结果类型，剩余 {max_retries - attempt} 次重试")
                await asyncio.sleep(retry_delay)

        return PublishResult(success=False, error_message="发布流程异常中断：步骤链未返回明确结果")

    async def _handle_action(self, action: NeedsAction) -> bool:
        """根据 NeedsAction 做补救动作，并控制 submit 的重试次数。"""
        if action.action in ("need_cover", "need_supplement"):
            return True

        if action.action == "need_retry":
            return self._submit_retry_count < self.config.max_submit_retries

        return False

    async def _diagnose(self, step_name: str, reason: str) -> None:
        if self.config.log_selector_probe:
            try:
                # 简单探测关键选择器命中情况（用于快速定位页面结构变化）
                probes = self.metadata.get("selector_probes") or {}
                if isinstance(probes, dict) and probes:
                    for k, sel in list(probes.items())[:20]:
                        try:
                            cnt = await self.page.locator(str(sel)).count()
                            logger.info(f"[probe] {k} -> {cnt} ({sel})")
                        except Exception:
                            continue
            except Exception:
                pass

        if not self.config.screenshot_on_error:
            return

        try:
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            url = ""
            try:
                url = self.page.url
            except Exception:
                pass

            out_dir = Path(self.config.screenshot_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_reason = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in reason])[:80]
            path = out_dir / f"{now}_{step_name}_{safe_reason}.png"
            await self.page.screenshot(path=str(path), full_page=True)
            logger.info(f"已保存诊断截图: {path} (url={url})")
        except Exception as e:
            logger.warning("诊断时页面不可用或已关闭: %s", e)

