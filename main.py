"""
EyeForge Desktop - AstrBot 插件
连接 EyeForge 桌面助手，提供：
1. 截图查看桌面
2. 鼠标/键盘操作
3. AI 群组接入
"""
import base64
import json
import re
import urllib.request
import urllib.error
from io import BytesIO

from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Image, Plain

# EyeForge 网关地址，可在插件配置中修改
EYEFORGE_HOST = "127.0.0.1"
EYEFORGE_PORT = 9178
EYEFORGE_TOKEN = ""


def _api_url(path: str) -> str:
    return f"http://{EYEFORGE_HOST}:{EYEFORGE_PORT}{path}"


def _request(method: str, path: str, body: dict = None) -> dict:
    """向 EyeForge 网关发送请求"""
    url = _api_url(path)
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if EYEFORGE_TOKEN:
        req.add_header("Authorization", f"Bearer {EYEFORGE_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"连接 EyeForge 失败: {e.reason}"}


@register("eyeforge_desktop", "EyeForge Desktop", "连接 EyeForge 桌面助手，截图/操作桌面/AI群组", version="1.0.0")
class EyeForgeDesktopPlugin(Plugin):
    def __init__(self, config):
        super().__init__(config)
        global EYEFORGE_HOST, EYEFORGE_PORT, EYEFORGE_TOKEN
        EYEFORGE_HOST = config.get("host", "127.0.0.1")
        EYEFORGE_PORT = int(config.get("port", 9178))
        EYEFORGE_TOKEN = config.get("token", "")

    @command_group("screen")
    def screen(self):
        """桌面截图相关命令"""
        pass

    @command_group("click")
    def click(self):
        """鼠标点击相关命令"""
        pass

    @command_group("type")
    def type_text(self):
        """文本输入相关命令"""
        pass

    @command_group("scroll")
    def scroll(self):
        """滚动相关命令"""
        pass

    @command_group("hotkey")
    def hotkey(self):
        """快捷键相关命令"""
        pass

    @command_group("ai_group")
    def ai_group(self):
        """AI 群组相关命令"""
        pass

    # ── 截图 ──
    @screen.command("view")
    async def screen_view(self, event: AstrMessageEvent):
        """查看桌面截图"""
        yield event.plain_result("正在截取桌面...")
        result = _request("GET", "/api/screenshot")
        if not result.get("success"):
            yield event.plain_result(f"截图失败: {result.get('error', '未知错误')}")
            return

        img_b64 = result.get("data", "")
        if not img_b64:
            yield event.plain_result("截图结果为空")
            return

        img_bytes = base64.b64decode(img_b64)
        width = result.get("width", 0)
        height = result.get("height", 0)

        # 上传到 AstrBot 图片托管
        buf = BytesIO(img_bytes)
        # 部分 AstrBot 版本直接支持 base64 图片
        yield event.image_result(img_b64)
        yield event.plain_result(f"桌面截图 ({width}x{height})")

    # ── 点击 ──
    @click.command("at")
    async def click_at(self, event: AstrMessageEvent, x: int, y: int,
                       button: str = "left", double: bool = False):
        """在指定坐标点击
        /click at <x> <y> [button] [double]
        """
        result = _request("POST", "/api/desktop/click", {
            "x": x, "y": y,
            "button": button,
            "double": double,
        })
        if result.get("success"):
            yield event.plain_result(f"已点击 ({x}, {y})")
        else:
            yield event.plain_result(f"点击失败: {result.get('error', '未知错误')}")

    # ── 输入文本 ──
    @type_text.command("text")
    async def type_text_cmd(self, event: AstrMessageEvent, text: str):
        """输入文本
        /type text <内容>
        """
        result = _request("POST", "/api/desktop/type", {"text": text})
        if result.get("success"):
            yield event.plain_result(f"已输入: {text[:50]}{'...' if len(text) > 50 else ''}")
        else:
            yield event.plain_result(f"输入失败: {result.get('error', '未知错误')}")

    # ── 滚动 ──
    @scroll.command("to")
    async def scroll_to(self, event: AstrMessageEvent,
                        delta_y: int = -3, x: int = 0, y: int = 0):
        """滚动
        /scroll to [delta_y] [x] [y]
        """
        result = _request("POST", "/api/desktop/scroll", {
            "x": x, "y": y,
            "delta_x": 0, "delta_y": delta_y,
        })
        if result.get("success"):
            yield event.plain_result(f"已滚动 ({delta_y})")
        else:
            yield event.plain_result(f"滚动失败: {result.get('error', '未知错误')}")

    # ── 快捷键 ──
    @hotkey.command("press")
    async def hotkey_press(self, event: AstrMessageEvent, keys: str):
        """模拟快捷键
        /hotkey press <key1> <key2> ...
        示例: /hotkey press ctrl c
        """
        key_list = [k.strip() for k in re.split(r"[ ,]+", keys) if k.strip()]
        result = _request("POST", "/api/desktop/hotkey", {"keys": key_list})
        if result.get("success"):
            yield event.plain_result(f"已执行快捷键: {' + '.join(key_list)}")
        else:
            yield event.plain_result(f"快捷键失败: {result.get('error', '未知错误')}")

    # ── 屏幕信息 ──
    @screen.command("info")
    async def screen_info(self, event: AstrMessageEvent):
        """查看屏幕信息"""
        result = _request("GET", "/api/screen-info")
        if result.get("success"):
            msg = (
                f"屏幕信息:\n"
                f"  分辨率: {result['width']}x{result['height']}\n"
                f"  显示器数量: {result['count']}"
            )
            yield event.plain_result(msg)
        else:
            yield event.plain_result(f"获取屏幕信息失败: {result.get('error', '未知错误')}")

    # ── AI 群组 ──
    @ai_group.command("send")
    async def ai_group_send(self, event: AstrMessageEvent, message: str):
        """向 AI 群组发送消息
        /ai_group send <消息内容>
        """
        result = _request("POST", "/ai-groups/dispatch", {
            "message": message,
            "source": "astrbot_plugin",
        })
        if result.get("success"):
            yield event.plain_result(f"已发送到 AI 群组")
        else:
            yield event.plain_result(f"发送失败: {result.get('error', '未知错误')}")

    @ai_group.command("status")
    async def ai_group_status(self, event: AstrMessageEvent):
        """查看 AI 群组状态"""
        result = _request("GET", "/api/ai-group")
        if isinstance(result, dict):
            yield event.plain_result(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            yield event.plain_result(f"获取状态失败: {result}")

    # ── 全局帮助 ──
    @command("ef")
    async def eyeforge_help(self, event: AstrMessageEvent):
        """EyeForge 插件帮助"""
        help_text = (
            "🔧 EyeForge Desktop 插件\n"
            "━━━━━━━━━━━━━━━━\n"
            "📷 /screen view - 查看桌面截图\n"
            "📷 /screen info - 屏幕信息\n"
            "🖱 /click at <x> <y> - 点击坐标\n"
            "⌨️ /type text <内容> - 输入文本\n"
            "📜 /scroll to [dy] - 滚动\n"
            "🔑 /hotkey press <k1> <k2> - 快捷键\n"
            "👥 /ai_group send <消息> - AI群组发言\n"
            "👥 /ai_group status - AI群组状态"
        )
        yield event.plain_result(help_text)
