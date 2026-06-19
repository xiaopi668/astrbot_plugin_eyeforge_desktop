# EyeForge Desktop - AstrBot 插件

连接 EyeForge 桌面助手，让 AI 能看到你的电脑屏幕并做出操作。

## 功能

| 命令 | 功能 |
|:----|:-----|
| `/screen view` | 📷 查看桌面截图 |
| `/screen info` | 📊 屏幕分辨率/显示器信息 |
| `/click at <x> <y>` | 🖱 在坐标处点击 |
| `/type text <内容>` | ⌨️ 输入文本 |
| `/hotkey press <k1> <k2>` | 🔑 模拟快捷键 |
| `/scroll to [delta_y]` | 📜 滚动页面 |
| `/ai_group send <消息>` | 👥 向 AI 群组发送消息 |
| `/ef` | 📖 显示帮助 |

## 依赖

- EyeForge 桌面端（Rust 原生）运行中，网关在 `9178` 端口
- AstrBot 已加载本插件

## 配置

可在 AstrBot 插件配置中修改：

| 配置项 | 默认值 | 说明 |
|:------|:------|:-----|
| `host` | `127.0.0.1` | EyeForge 网关地址 |
| `port` | `9178` | EyeForge 网关端口 |
| `token` | `""` | WebSocket 认证令牌（可选） |
