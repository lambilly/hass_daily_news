"""Sensor platform for Daily News."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

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
                "title": "每日新闻",
                "last_update": "从未更新",
                "update_schedule": "每日6点开始更新",
                "api_key_status": "未配置"
            }
            
        data = self.coordinator.data
        
        return {
            "title": "每日新闻",
            "status": data.get("status", ""),
            "head_image": data.get("head_image", "暂无图片"),
            "news_image": data.get("news_image", "暂无图片"),
            "weiyu": data.get("weiyu", "暂无微语"),
            "news": data.get("news", {}),
            "update_time": data.get("date", ""),
            "total_news": data.get("total_news", 0),
            "scroll_interval": data.get("scroll_interval", 15),
            "last_update": data.get("last_update", "从未更新"),
            "update_schedule": data.get("update_schedule", "每日6点开始更新"),
            "api_key_status": data.get("api_key_status", "未知")
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
                "title": "滚动新闻",
                "last_update": "从未更新",
                "update_schedule": "每日6点开始更新",
                "api_key_status": "未配置"
            }
            
        current_news, current_index, total_news = self.coordinator.get_current_news()
        data = self.coordinator.data
        
        attributes = {
            "title": "滚动新闻",
            "current_news": current_news,
            "current_index": current_index,
            "total_news": total_news,
            "status": data.get("status", ""),
            "head_image": data.get("head_image", "暂无图片"),
            "news_image": data.get("news_image", "暂无图片"),
            "weiyu": data.get("weiyu", "暂无微语"),
            "update_time": data.get("date", ""),
            "scroll_interval": data.get("scroll_interval", 15),
            "last_update": data.get("last_update", "从未更新"),
            "update_schedule": data.get("update_schedule", "每日6点开始更新"),
            "api_key_status": data.get("api_key_status", "未知")
        }
        
        return attributes

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:newspaper-variant"