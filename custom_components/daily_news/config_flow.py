"""Config flow for Daily News."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN, 
    DEFAULT_NAME, 
    CONF_SCROLL_INTERVAL, 
    CONF_API_KEY,
    DEFAULT_SCROLL_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

class DailyNewsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daily News."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # 验证API Key
            api_key = user_input.get(CONF_API_KEY, "")
            if not api_key or api_key.strip() == "":
                errors[CONF_API_KEY] = "api_key_required"
            
            # 验证滚动间隔
            scroll_interval = user_input.get(CONF_SCROLL_INTERVAL)
            
            if scroll_interval is None or scroll_interval == "":
                errors[CONF_SCROLL_INTERVAL] = "required"
            else:
                try:
                    scroll_interval = int(scroll_interval)
                    if scroll_interval < 5 or scroll_interval > 300:
                        errors[CONF_SCROLL_INTERVAL] = "scroll_interval_range"
                except ValueError:
                    errors[CONF_SCROLL_INTERVAL] = "invalid_scroll_interval"
            
            if not errors:
                # 保存配置
                return self.async_create_entry(
                    title=DEFAULT_NAME, 
                    data={
                        CONF_API_KEY: api_key.strip(),
                        CONF_SCROLL_INTERVAL: scroll_interval
                    }
                )

        # 创建数据模式，API Key在滚动间隔之前
        data_schema = vol.Schema({
            vol.Required(
                CONF_API_KEY,
                description="API密钥（必填）"
            ): str,
            vol.Required(
                CONF_SCROLL_INTERVAL,
                default=DEFAULT_SCROLL_INTERVAL,
                description="滚动间隔（秒）"
            ): int
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DailyNewsOptionsFlow(config_entry)


class DailyNewsOptionsFlow(config_entries.OptionsFlow):
    """Handle Daily News options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        
        if user_input is not None:
            # 验证API Key
            api_key = user_input.get(CONF_API_KEY, "")
            if not api_key or api_key.strip() == "":
                errors[CONF_API_KEY] = "api_key_required"
            
            # 验证滚动间隔
            scroll_interval = user_input.get(CONF_SCROLL_INTERVAL)
            
            if scroll_interval is None or scroll_interval == "":
                errors[CONF_SCROLL_INTERVAL] = "required"
            else:
                try:
                    scroll_interval = int(scroll_interval)
                    if scroll_interval < 5 or scroll_interval > 300:
                        errors[CONF_SCROLL_INTERVAL] = "scroll_interval_range"
                except ValueError:
                    errors[CONF_SCROLL_INTERVAL] = "invalid_scroll_interval"
            
            if not errors:
                # 更新协调器中的配置
                hass = self.hass
                entry_id = self.config_entry.entry_id
                
                if DOMAIN in hass.data and entry_id in hass.data[DOMAIN]:
                    coordinator = hass.data[DOMAIN][entry_id]
                    # 更新API Key
                    coordinator.update_api_key(api_key.strip())
                    # 更新滚动间隔
                    coordinator.update_scroll_interval(scroll_interval)
                
                # 保存选项
                return self.async_create_entry(
                    title="", 
                    data={
                        CONF_API_KEY: api_key.strip(),
                        CONF_SCROLL_INTERVAL: scroll_interval
                    }
                )

        # 获取当前配置值
        current_api_key = ""
        if self.config_entry.options and CONF_API_KEY in self.config_entry.options:
            current_api_key = self.config_entry.options[CONF_API_KEY]
        elif self.config_entry.data and CONF_API_KEY in self.config_entry.data:
            current_api_key = self.config_entry.data[CONF_API_KEY]
        
        current_scroll_interval = self.config_entry.options.get(
            CONF_SCROLL_INTERVAL,
            self.config_entry.data.get(CONF_SCROLL_INTERVAL, DEFAULT_SCROLL_INTERVAL)
        )
        
        # 确保是整数
        try:
            current_scroll_interval = int(current_scroll_interval)
        except (ValueError, TypeError):
            current_scroll_interval = DEFAULT_SCROLL_INTERVAL

        # 创建数据模式，API Key在滚动间隔之前
        data_schema = vol.Schema({
            vol.Required(
                CONF_API_KEY,
                default=current_api_key,
                description="API密钥（必填）"
            ): str,
            vol.Required(
                CONF_SCROLL_INTERVAL,
                default=current_scroll_interval,
                description="滚动间隔（秒）"
            ): int
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors
        )