"""Constants for Daily News integration."""

DOMAIN = "daily_news"
DEFAULT_NAME = "每日新闻"
DEFAULT_SCAN_INTERVAL = 86400  # 24 hours
DEFAULT_SCROLL_INTERVAL = 15  # 15 seconds

CONF_SCROLL_INTERVAL = "scroll_interval"
CONF_API_KEY = "api_key"  # 新增API Key配置

# API地址模板
API_URL_TEMPLATE = "https://qqlykm.cn/api/60s/index?key={}"

ATTR_STATUS = "status"
ATTR_HEAD_IMAGE = "head_image"
ATTR_NEWS_IMAGE = "news_image"
ATTR_WEIYU = "weiyu"
ATTR_NEWS = "news"
ATTR_UPDATE_TIME = "update_time"
ATTR_CURRENT_INDEX = "current_index"
ATTR_TOTAL_NEWS = "total_news"
ATTR_TITLE = "title"
ATTR_SCROLL_INTERVAL = "scroll_interval"

PLATFORMS = ["sensor"]