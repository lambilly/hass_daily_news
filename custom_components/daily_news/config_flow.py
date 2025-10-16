"""Config flow for Daily News."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, DEFAULT_NAME, CONF_SCROLL_INTERVAL, DEFAULT_SCROLL_INTERVAL

class DailyNewsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daily News."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # 保存配置
            return self.async_create_entry(
                title=DEFAULT_NAME, 
                data=user_input
            )

        # 在初始设置时显示滚动间隔配置
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCROLL_INTERVAL,
                    default=DEFAULT_SCROLL_INTERVAL,
                    description="滚动新闻切换间隔（秒）"
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300))
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DailyNewsOptionsFlow(config_entry)

class DailyNewsOptionsFlow(config_entries.OptionsFlow):
    """Handle Daily News options."""

    def __init__(self, config_entry):
        """Initialize Daily News options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        
        if user_input is not None:
            # 验证输入
            if user_input[CONF_SCROLL_INTERVAL] < 5 or user_input[CONF_SCROLL_INTERVAL] > 300:
                errors[CONF_SCROLL_INTERVAL] = "scroll_interval_range"
            else:
                # 更新配置
                hass = self.hass
                entry_id = self.config_entry.entry_id
                
                if DOMAIN in hass.data and entry_id in hass.data[DOMAIN]:
                    coordinator = hass.data[DOMAIN][entry_id]
                    coordinator.update_scroll_interval(user_input[CONF_SCROLL_INTERVAL])
                
                return self.async_create_entry(title="", data=user_input)

        # 确保从options中获取值，如果没有则从data中获取，最后使用默认值
        scroll_interval = self.config_entry.options.get(
            CONF_SCROLL_INTERVAL,
            self.config_entry.data.get(CONF_SCROLL_INTERVAL, DEFAULT_SCROLL_INTERVAL)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCROLL_INTERVAL,
                    default=scroll_interval,
                    description="滚动新闻切换间隔（秒）"
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300))
            }),
            errors=errors
        )