"""The Daily News integration."""
import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    API_URL,
    CONF_SCROLL_INTERVAL,
    DEFAULT_SCROLL_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Daily News from a config entry."""
    
    # 从配置项获取滚动间隔，优先从options获取，其次从data获取，最后使用默认值
    scroll_interval = entry.options.get(
        CONF_SCROLL_INTERVAL,
        entry.data.get(CONF_SCROLL_INTERVAL, DEFAULT_SCROLL_INTERVAL)
    )
    
    coordinator = DailyNewsDataCoordinator(hass, entry, scroll_interval)
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # 创建设备
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="新闻数据",
        manufacturer="Node-RED",
        model="每日新闻",
        sw_version=entry.version,
    )
    
    # 立即进行第一次数据更新
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning(f"Initial update failed: {err}. Will retry at scheduled time.")
        # 即使第一次更新失败，仍然继续设置集成
        # 设置默认数据
        coordinator.data = coordinator._get_default_data()
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # 启动定时更新任务
    coordinator.start_scheduled_updates()
    
    # Start scrolling service
    coordinator.start_scrolling()
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.stop_scheduled_updates()
    coordinator.stop_scrolling()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

class DailyNewsDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Daily News data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, scroll_interval: int) -> None:
        """Initialize."""
        self.entry = entry
        self.scroll_interval = scroll_interval
        self.scroll_task = None
        self.update_task = None
        self.current_news_index = 0
        self.retry_count = 0
        self.max_retries = 2
        self.last_update_success = False
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    def _get_default_data(self):
        """Get default data when API fails."""
        return {
            "title": "每日新闻",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "等待更新",
            "head_image": "暂无图片",
            "news_image": "暂无图片",
            "weiyu": "暂无微语",
            "news": {},
            "total_news": 0,
            "scroll_interval": self.scroll_interval,
            "last_update": "从未更新"
        }

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            session = async_get_clientsession(self.hass)
            
            # 添加User-Agent头，模拟浏览器请求
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            async with async_timeout.timeout(15):  # 增加超时时间到15秒
                response = await session.get(API_URL, headers=headers)
                
                if response.status == 200:
                    data = await response.json()
                    self.retry_count = 0  # 重置重试计数
                    self.last_update_success = True
                    processed_data = self._process_data(data)
                    processed_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return processed_data
                elif response.status == 403:
                    _LOGGER.error("API returned 403 Forbidden. The server is rejecting the request.")
                    self.last_update_success = False
                    # 返回默认数据，但标记状态
                    default_data = self._get_default_data()
                    default_data["status"] = f"API拒绝访问 (403)"
                    default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return default_data
                else:
                    _LOGGER.warning(f"API request failed with status {response.status}")
                    self.last_update_success = False
                    default_data = self._get_default_data()
                    default_data["status"] = f"API请求失败 ({response.status})"
                    default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return default_data
                    
        except asyncio.TimeoutError:
            _LOGGER.warning("API request timed out after 15 seconds")
            self.retry_count += 1
            self.last_update_success = False
            default_data = self._get_default_data()
            default_data["status"] = f"请求超时 (重试 {self.retry_count}/{self.max_retries})"
            default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return default_data
        except aiohttp.ClientConnectionError as err:
            _LOGGER.warning(f"Connection error: {err}")
            self.retry_count += 1
            self.last_update_success = False
            default_data = self._get_default_data()
            default_data["status"] = f"连接错误: {err}"
            default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return default_data
        except Exception as err:
            _LOGGER.warning(f"API update failed (attempt {self.retry_count + 1}): {err}")
            self.retry_count += 1
            self.last_update_success = False
            default_data = self._get_default_data()
            default_data["status"] = f"更新失败: {str(err)[:50]}"
            default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return default_data

    def _process_data(self, data):
        """Process the API response data."""
        def format_news_content(text):
            if not text:
                return ""
            return (text
                .replace("、", ". ")
                .replace("  ", " ")
                .strip()[:200])
        
        def is_valid_date(date_str):
            import re
            return bool(re.match(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$", date_str))
        
        news_list = data.get("news", [])
        news_object = {}
        for index, item in enumerate(news_list):
            news_object[f"news_{index+1}"] = format_news_content(str(item))
        
        return {
            "title": "每日新闻",
            "date": data.get("date", "无效日期") if is_valid_date(data.get("date", "")) else datetime.now().strftime("%Y-%m-%d"),
            "status": (data.get("msg", "更新成功") or "更新成功")[:50],
            "head_image": data.get("head_image", "暂无图片") or "暂无图片",
            "news_image": data.get("image", "暂无图片") or "暂无图片",
            "weiyu": (data.get("weiyu", "暂无微语") or "暂无微语")[:100],
            "news": news_object,
            "total_news": len(news_list),
            "scroll_interval": self.scroll_interval
        }

    def start_scheduled_updates(self):
        """Start scheduled updates at 7:00 AM with retry at 9:00 AM if failed."""
        self.stop_scheduled_updates()
        self.update_task = self.hass.loop.create_task(self._scheduled_updates())

    def stop_scheduled_updates(self):
        """Stop scheduled updates."""
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None

    async def _scheduled_updates(self):
        """Handle scheduled updates with retry logic."""
        while True:
            now = dt_util.now()
            
            # 计算今天7:00的时间
            today_7am = now.replace(hour=7, minute=0, second=0, microsecond=0)
            # 计算今天9:00的时间
            today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # 如果现在时间已经过了7:00但还没到9:00，且今天还没有成功更新，则立即尝试更新
            if now >= today_7am and now < today_9am and not self.last_update_success:
                _LOGGER.info("Executing scheduled update (7:00 AM)")
                try:
                    await self.async_refresh()
                except Exception as err:
                    _LOGGER.warning(f"Scheduled update failed: {err}")
            
            # 如果现在时间已经过了9:00，且上次更新失败，则进行重试
            elif now >= today_9am and not self.last_update_success:
                _LOGGER.info(f"Executing retry update (9:00 AM)")
                try:
                    await self.async_refresh()
                except Exception as err:
                    _LOGGER.warning(f"Retry update failed: {err}")
            
            # 计算下一次更新时间（明天7:00）
            next_update = today_7am + timedelta(days=1)
            
            wait_seconds = (next_update - now).total_seconds()
            _LOGGER.debug(f"Next update scheduled at {next_update} (in {wait_seconds:.0f} seconds)")
            
            await asyncio.sleep(wait_seconds)

    def start_scrolling(self):
        """Start the news scrolling task."""
        self.stop_scrolling()
        self.scroll_task = self.hass.loop.create_task(self._scroll_news())

    def stop_scrolling(self):
        """Stop the news scrolling task."""
        if self.scroll_task:
            self.scroll_task.cancel()
            self.scroll_task = None

    async def _scroll_news(self):
        """Scroll through news items."""
        while True:
            await asyncio.sleep(self.scroll_interval)
            if self.data and "news" in self.data:
                news_count = self.data.get("total_news", 0)
                if news_count > 0:
                    self.current_news_index = (self.current_news_index % news_count) + 1
                    # 通知传感器更新
                    self.async_set_updated_data(self.data)
                else:
                    # 如果没有新闻，也更新一次以刷新状态
                    self.async_set_updated_data(self.data)

    def get_current_news(self):
        """Get current scrolling news item."""
        if not self.data or "news" not in self.data:
            return "等待数据", 0, 0
            
        news_data = self.data["news"]
        total_news = self.data.get("total_news", 0)
        
        if total_news == 0:
            return "暂无新闻", 0, 0
            
        current_key = f"news_{self.current_news_index}"
        current_news = news_data.get(current_key, "暂无新闻")
        
        return current_news, self.current_news_index, total_news

    def update_scroll_interval(self, new_interval: int):
        """Update scroll interval and restart scrolling."""
        self.scroll_interval = new_interval
        # 更新数据中的滚动间隔
        if self.data:
            self.data["scroll_interval"] = new_interval
        self.stop_scrolling()
        self.start_scrolling()
        _LOGGER.info(f"Scroll interval updated to {new_interval} seconds")