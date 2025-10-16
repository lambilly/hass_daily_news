# 每日新闻 Home Assistant 集成

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

一个用于获取和展示每日新闻的 Home Assistant 自定义集成，支持新闻自动滚动显示。

## 功能特点

- 📰 获取每日新闻摘要
- 🔄 自动滚动显示新闻内容
- ⚙️ 可配置滚动间隔时间
- 🌐 中文界面支持
- 🕒 每天7:00尝试获取新闻数据。如果7点更新失败，会在9:00自动重试，最多重试2次

## 安装

### 方法一：通过 HACS 安装（推荐）

1. 确保已安装 [HACS](https://hacs.xyz/)
2. 在 HACS 中点击「集成」
3. 点击右下角「自定义仓库」
4. 添加仓库：`https://github.com/lambilly/hass_daily_news`
5. 选择分类：集成
6. 搜索「每日新闻」并安装
7. 重启 Home Assistant

### 方法二：手动安装

1. 将 `custom_components/daily_news` 文件夹复制到您的 Home Assistant 配置目录中
2. 重启 Home Assistant
3. 在「配置」->「设备与服务」中添加集成

## 配置

### 初始设置

1. 在 Home Assistant 中转到「配置」->「设备与服务」
2. 点击「添加集成」
3. 搜索「每日新闻」
4. 按照提示完成设置

### 配置选项

- **滚动间隔**：设置新闻滚动显示的间隔时间（默认15秒）

## 实体

集成会创建两个传感器实体：

### 每日新闻传感器
- **实体ID**: `sensor.daily_news`
- **状态**: 新闻日期（如：2025-10-15）
- **属性**:
  - `title`: "每日新闻"
  - `status`: API状态信息
  - `head_image`: 头部图片URL
  - `news_image`: 新闻图片URL
  - `weiyu`: 微语内容
  - `news`: 所有新闻条目的对象
  - `update_time`: 更新时间
  - `total_news`: 新闻总条数
  - `scroll_interval`: 滚动间隔

### 滚动新闻传感器
- **实体ID**: `sensor.scrolling_news`
- **状态**: 新闻日期（如：2025-10-15）
- **属性**:
  - `title`: "滚动新闻"
  - `current_news`: 当前显示的新闻内容
  - `current_index`: 当前新闻索引
  - `total_news`: 新闻总条数
  - `scroll_interval`: 滚动间隔
  - 其他属性与每日新闻传感器相同

## 使用示例

### 在概览中显示

```yaml
type: entities
entities:
  - entity: sensor.daily_news
    name: 今日新闻
  - entity: sensor.scrolling_news
    name: 滚动新闻
title: 新闻资讯
```
## 故障排除
 - 集成无法添加
 •	确保网络连接正常
 •	检查 Home Assistant 日志获取详细错误信息

 - 新闻无法显示
 •	确认 API 服务可用性
 •	检查网络连接是否能够访问 http://api.suxun.site/api/sixs?type=json

 - 滚动功能不工作
 •	检查滚动间隔配置
 •	重启 Home Assistant
## 支持
如果您遇到问题或有建议：
1.	查看 Home Assistant 社区
2.	在 GitHub 仓库提交 Issue
## 贡献
欢迎提交 Pull Request 来改进这个集成！
## 许可证
MIT License
## 作者
lambilly

