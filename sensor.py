"""Sensor platform for Daily News."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_STATUS,
    ATTR_HEAD_IMAGE,
    ATTR_NEWS_IMAGE,
    ATTR_WEIYU,
    ATTR_NEWS,
    ATTR_UPDATE_TIME,
    ATTR_CURRENT_INDEX,
    ATTR_TOTAL_NEWS,
    ATTR_SCROLL_INTERVAL,
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Daily News sensor based on config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    sensors = [
        DailyNewsSensor(coordinator, config_entry),
        ScrollingNewsSensor(coordinator, config_entry)
    ]
    
    async_add_entities(sensors, False)

class DailyNewsSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Daily News Sensor."""

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "每日新闻"
        self._attr_unique_id = f"{config_entry.entry_id}_daily_news"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "新闻数据",
            "manufacturer": "Node-RED",
            "model": "每日新闻",
            "sw_version": config_entry.version,
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("date", "未知日期")
        return "未知日期"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self.coordinator.data:
            return {
                "title": "每日新闻"
            }
            
        data = self.coordinator.data
        return {
            "title": "每日新闻",  # 新增 title 属性
            ATTR_STATUS: data.get("status", ""),
            ATTR_HEAD_IMAGE: data.get("head_image", ""),
            ATTR_NEWS_IMAGE: data.get("news_image", ""),
            ATTR_WEIYU: data.get("weiyu", ""),
            ATTR_NEWS: data.get("news", {}),
            ATTR_UPDATE_TIME: data.get("date", ""),
            ATTR_TOTAL_NEWS: data.get("total_news", 0),
            ATTR_SCROLL_INTERVAL: data.get("scroll_interval", 15)  # 添加滚动间隔
        }

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:newspaper"

class ScrollingNewsSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Scrolling News Sensor."""

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = "滚动新闻"
        self._attr_unique_id = f"{config_entry.entry_id}_scrolling_news"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "新闻数据",
            "manufacturer": "Node-RED",
            "model": "每日新闻",
            "sw_version": config_entry.version,
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("date", "未知日期")
        return "未知日期"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self.coordinator.data:
            return {
                "title": "滚动新闻"
            }
            
        current_news, current_index, total_news = self.coordinator.get_current_news()
        data = self.coordinator.data
        
        # 构建属性字典，排除news属性
        attributes = {
            "title": "滚动新闻",  # 新增 title 属性
            "current_news": current_news,
            ATTR_CURRENT_INDEX: current_index,
            ATTR_TOTAL_NEWS: total_news,
            ATTR_STATUS: data.get("status", ""),
            ATTR_HEAD_IMAGE: data.get("head_image", ""),
            ATTR_NEWS_IMAGE: data.get("news_image", ""),
            ATTR_WEIYU: data.get("weiyu", ""),
            # 注意：这里故意不包含 ATTR_NEWS 属性
            ATTR_UPDATE_TIME: data.get("date", ""),
            ATTR_SCROLL_INTERVAL: data.get("scroll_interval", 15)  # 添加滚动间隔
        }
        
        return attributes

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:newspaper-variant"