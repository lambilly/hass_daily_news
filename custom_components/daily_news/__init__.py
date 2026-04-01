"""The Daily News integration."""
import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
import async_timeout
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    API_URL_TEMPLATE,
    CONF_SCROLL_INTERVAL,
    CONF_API_KEY,
    DEFAULT_SCROLL_INTERVAL,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Daily News from a config entry."""
    
    # 获取API Key - 必须由用户提供
    api_key = ""
    try:
        if entry.options and CONF_API_KEY in entry.options:
            api_key = entry.options[CONF_API_KEY]
        elif entry.data and CONF_API_KEY in entry.data:
            api_key = entry.data[CONF_API_KEY]
    except (KeyError, AttributeError):
        api_key = ""
    
    # 如果没有API Key，记录错误
    if not api_key or api_key.strip() == "":
        _LOGGER.error("API Key未配置，请配置API Key后再使用")
    
    # 获取滚动间隔配置
    scroll_interval = DEFAULT_SCROLL_INTERVAL
    try:
        if entry.options and CONF_SCROLL_INTERVAL in entry.options:
            scroll_interval = entry.options[CONF_SCROLL_INTERVAL]
        elif entry.data and CONF_SCROLL_INTERVAL in entry.data:
            scroll_interval = entry.data[CONF_SCROLL_INTERVAL]
        
        scroll_interval = int(scroll_interval)
        if scroll_interval < 5:
            scroll_interval = 5
        elif scroll_interval > 300:
            scroll_interval = 300
    except (ValueError, TypeError, KeyError):
        scroll_interval = DEFAULT_SCROLL_INTERVAL
    
    coordinator = DailyNewsDataCoordinator(hass, entry, api_key, scroll_interval)
    
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
    except Exception:
        coordinator.data = coordinator._get_default_data()
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # 启动定时更新任务
    coordinator.start_scheduled_updates()
    
    # 启动滚动任务
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


class DailyNewsDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Daily News data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api_key: str, scroll_interval: int):
        """Initialize."""
        self.entry = entry
        self.api_key = api_key
        self.scroll_interval = scroll_interval
        self.scroll_task = None
        self.update_task = None
        self.current_news_index = 0
        self.today_success = False
        self.today_date = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    def _get_api_url(self):
        """构建完整的API URL."""
        return API_URL_TEMPLATE.format(self.api_key)

    def _get_default_data(self):
        """Get default data when API fails."""
        today_date = datetime.now().strftime("%Y-%m-%d")
        return {
            "title": "每日新闻",
            "date": today_date,
            "status": "等待更新",
            "head_image": "暂无图片",
            "news_image": "暂无图片",
            "weiyu": "暂无微语",
            "news": {},
            "total_news": 0,
            "scroll_interval": self.scroll_interval,
            "last_update": "从未更新",
            "update_schedule": "每日7点开始更新",
            "api_key_status": "未配置" if not self.api_key else "已配置"
        }

    async def _async_update_data(self):
        """Fetch data from API."""
        # 检查API Key是否已配置
        if not self.api_key or self.api_key.strip() == "":
            _LOGGER.error("API Key未配置，无法更新数据")
            default_data = self._get_default_data()
            default_data["status"] = "API Key未配置，请配置API Key"
            default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            default_data["update_schedule"] = "等待配置API Key"
            default_data["api_key_status"] = "未配置"
            return default_data
        
        # 检查是否需要重置每日计数器
        self._check_reset_daily_counters()
        
        try:
            session = async_get_clientsession(self.hass)
            
            # 添加User-Agent头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            api_url = self._get_api_url()
            _LOGGER.debug("请求API URL: %s", api_url.replace(self.api_key, "***"))  # 隐藏API Key
            
            async with async_timeout.timeout(15):
                response = await session.get(api_url, headers=headers)
                
                if response.status == 200:
                    data = await response.json()
                    
                    # 检查API返回的success字段
                    if data.get("success", False):
                        processed_data = self._process_data(data)
                        processed_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        processed_data["update_schedule"] = "更新成功"
                        processed_data["api_key_status"] = "有效"
                        self.today_success = True
                        _LOGGER.info("API更新成功")
                        return processed_data
                    else:
                        _LOGGER.warning("API返回失败状态: %s", data)
                        default_data = self._get_default_data()
                        default_data["status"] = "API返回失败，请检查API Key"
                        default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        default_data["update_schedule"] = "更新失败，15分钟后重试"
                        default_data["api_key_status"] = "可能无效"
                        return default_data
                elif response.status == 401 or response.status == 403:
                    _LOGGER.error("API认证失败，状态码: %s，请检查API Key", response.status)
                    default_data = self._get_default_data()
                    default_data["status"] = f"API认证失败({response.status})，请检查API Key"
                    default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    default_data["update_schedule"] = "认证失败，请检查API Key"
                    default_data["api_key_status"] = "无效"
                    return default_data
                else:
                    _LOGGER.warning("API请求失败，状态码: %s", response.status)
                    default_data = self._get_default_data()
                    default_data["status"] = f"API请求失败({response.status})"
                    default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    default_data["update_schedule"] = "更新失败，15分钟后重试"
                    return default_data
                    
        except asyncio.TimeoutError:
            _LOGGER.warning("API请求超时")
            default_data = self._get_default_data()
            default_data["status"] = "请求超时"
            default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            default_data["update_schedule"] = "更新失败，15分钟后重试"
            return default_data
        except Exception as err:
            _LOGGER.warning("API更新失败: %s", err)
            default_data = self._get_default_data()
            default_data["status"] = f"更新失败: {str(err)[:50]}"
            default_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            default_data["update_schedule"] = "更新失败，15分钟后重试"
            return default_data

    def _check_reset_daily_counters(self):
        """检查并重置每日计数器."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self.today_date != today:
            # 新的一天，重置成功标记
            self.today_date = today
            self.today_success = False
            _LOGGER.info("新的一天开始: %s", today)

    def _process_data(self, data):
        """Process the API response data."""
        def format_news_content(text, index):
            if not text:
                return ""
            # 移除原有的编号（如果有），然后添加新的序号
            import re
            # 移除开头的数字和顿号或点号
            cleaned = re.sub(r'^\d+[、.]\s*', '', text)
            # 添加新的序号（1. 2. 3. ...）
            return f"{index}. {cleaned.strip()[:200]}"
        
        # 从新API获取数据
        api_data = data.get("data", {})
        news_list = api_data.get("news", [])
        weiyu = api_data.get("weiyu", "暂无微语")
        date = api_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        # 处理微语，添加【微语】前缀
        if weiyu and weiyu != "暂无微语":
            weiyu = f"【微语】{weiyu}"
        
        # 处理新闻列表，添加序号
        news_object = {}
        for index, item in enumerate(news_list, 1):
            news_object[f"news_{index}"] = format_news_content(str(item), index)
        
        return {
            "title": "每日新闻",
            "date": date,
            "status": "更新成功",
            "head_image": "暂无图片",  # 新API没有图片字段
            "news_image": "暂无图片",  # 新API没有图片字段
            "weiyu": weiyu,
            "news": news_object,
            "total_news": len(news_list),
            "scroll_interval": self.scroll_interval,
            "api_key_status": "有效"
        }

    def start_scheduled_updates(self):
        """启动定时更新任务 - 每天6点开始，失败则15分钟重试."""
        self.stop_scheduled_updates()
        self.update_task = self.hass.loop.create_task(self._scheduled_updates())

    def stop_scheduled_updates(self):
        """停止定时更新任务."""
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None

    async def _scheduled_updates(self):
        """处理定时更新 - 每天7点开始，失败则15分钟重试."""
        _LOGGER.info("开始定时更新任务")
        
        while True:
            now = dt_util.now()
            current_hour = now.hour
            
            # 重置每日计数器
            self._check_reset_daily_counters()
            
            # 如果现在是7点或之后，且今天还没有成功更新
            if current_hour >= 7 and not self.today_success:
                # 尝试更新
                _LOGGER.info("尝试更新新闻数据")
                
                try:
                    await self.async_refresh()
                except Exception as err:
                    _LOGGER.warning("更新失败: %s", err)
                
                # 等待15分钟后重试
                await asyncio.sleep(15 * 60)
                
            elif current_hour < 7:
                # 还未到7点，计算到7点的等待时间
                today_7am = now.replace(hour=7, minute=0, second=0, microsecond=0)
                wait_seconds = (today_7am - now).total_seconds()
                
                if wait_seconds > 0:
                    _LOGGER.info("等待到7点开始更新，剩余%.0f秒", wait_seconds)
                    await asyncio.sleep(wait_seconds)
                else:
                    # 已经过了7点，立即尝试
                    continue
            else:
                # 今天已经成功更新，等待到明天7点
                tomorrow_7am = now.replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=1)
                wait_seconds = (tomorrow_7am - now).total_seconds()
                
                _LOGGER.info("今日已成功更新，下一次更新将在明天7点，等待%.0f秒", wait_seconds)
                await asyncio.sleep(wait_seconds)
            
    def start_scrolling(self):
        """启动新闻滚动任务."""
        self.stop_scrolling()
        self.scroll_task = self.hass.loop.create_task(self._scroll_news())

    def stop_scrolling(self):
        """停止新闻滚动任务."""
        if self.scroll_task:
            self.scroll_task.cancel()
            self.scroll_task = None

    async def _scroll_news(self):
        """滚动显示新闻."""
        while True:
            await asyncio.sleep(self.scroll_interval)
            
            if self.data and "news" in self.data:
                news_count = self.data.get("total_news", 0)
                
                if news_count > 0:
                    self.current_news_index = (self.current_news_index % news_count) + 1
                    # 通知传感器更新
                    self.async_set_updated_data(self.data)

    def get_current_news(self):
        """获取当前滚动新闻."""
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
        """更新滚动间隔."""
        try:
            new_interval = int(new_interval)
            
            if new_interval < 5:
                new_interval = 5
            elif new_interval > 300:
                new_interval = 300
            
            self.scroll_interval = new_interval
            
            # 更新数据中的滚动间隔
            if self.data:
                self.data["scroll_interval"] = new_interval
            
            # 重启滚动任务
            self.stop_scrolling()
            self.start_scrolling()
            
            _LOGGER.info("滚动间隔更新为 %s 秒", new_interval)
            
        except (ValueError, TypeError):
            _LOGGER.error("更新滚动间隔失败")

    def update_api_key(self, new_api_key: str):
        """更新API Key."""
        if new_api_key and new_api_key.strip():
            self.api_key = new_api_key.strip()
            _LOGGER.info("API Key已更新")
            
            # 重置成功标记，强制立即更新
            self.today_success = False
            self.today_date = None
            
            # 强制立即更新数据
            self.hass.loop.create_task(self.async_refresh())
        else:
            _LOGGER.error("API Key不能为空")