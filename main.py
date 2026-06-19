"""
EyeForge Desktop - AstrBot 插件
连接 EyeForge 桌面助手，提供：
1. 截图查看桌面
2. 鼠标/键盘操作
3. AI 群组创建/管理/发言
4. 模型加载
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

EYEFORGE_HOST = "127.0.0.1"
EYEFORGE_PORT = 9178
EYEFORGE_TOKEN = ""


def _api_url(path: str) -> str:
    return f"http://{EYEFORGE_HOST}:{EYEFORGE_PORT}{path}"


def _request(method: str, path: str, body: dict = None) -> dict:
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
        pass

    @command_group("click")
    def click(self):
        pass

    @command_group("type")
    def type_text(self):
        pass

    @command_group("scroll")
    def scroll(self):
        pass

    @command_group("hotkey")
    def hotkey(self):
        pass

    @command_group("ai_group")
    def ai_group(self):
        pass

    @command_group("model")
    def model(self):
        pass

    # ═══════════════ 截图 ═══════════════

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
        width, height = result.get("width", 0), result.get("height", 0)
        yield event.image_result(img_b64)
        yield event.plain_result(f"桌面截图 ({width}x{height})")

    @screen.command("info")
    async def screen_info(self, event: AstrMessageEvent):
        """查看屏幕信息"""
        result = _request("GET", "/api/screen-info")
        if result.get("success"):
            yield event.plain_result(
                f"屏幕信息:\n  分辨率: {result['width']}x{result['height']}\n  显示器数量: {result['count']}"
            )
        else:
            yield event.plain_result(f"获取屏幕信息失败: {result.get('error', '未知错误')}")

    # ═══════════════ 鼠标操作 ═══════════════

    @click.command("at")
    async def click_at(self, event: AstrMessageEvent, x: int, y: int,
                       button: str = "left", double: bool = False):
        """在指定坐标点击"""
        result = _request("POST", "/api/desktop/click", {
            "x": x, "y": y, "button": button, "double": double,
        })
        yield event.plain_result(
            f"已点击 ({x}, {y})" if result.get("success")
            else f"点击失败: {result.get('error', '未知错误')}"
        )

    @type_text.command("text")
    async def type_text_cmd(self, event: AstrMessageEvent, text: str):
        """输入文本"""
        result = _request("POST", "/api/desktop/type", {"text": text})
        yield event.plain_result(
            f"已输入: {text[:50]}{'...' if len(text) > 50 else ''}"
            if result.get("success")
            else f"输入失败: {result.get('error', '未知错误')}"
        )

    @scroll.command("to")
    async def scroll_to(self, event: AstrMessageEvent,
                        delta_y: int = -3, x: int = 0, y: int = 0):
        """滚动"""
        result = _request("POST", "/api/desktop/scroll", {
            "x": x, "y": y, "delta_x": 0, "delta_y": delta_y,
        })
        yield event.plain_result(
            f"已滚动 ({delta_y})" if result.get("success")
            else f"滚动失败: {result.get('error', '未知错误')}"
        )

    @hotkey.command("press")
    async def hotkey_press(self, event: AstrMessageEvent, keys: str):
        """模拟快捷键"""
        key_list = [k.strip() for k in re.split(r"[ ,]+", keys) if k.strip()]
        result = _request("POST", "/api/desktop/hotkey", {"keys": key_list})
        yield event.plain_result(
            f"已执行快捷键: {' + '.join(key_list)}" if result.get("success")
            else f"快捷键失败: {result.get('error', '未知错误')}"
        )

    # ═══════════════ AI 群组 ═══════════════

    @ai_group.command("create")
    async def ai_group_create(self, event: AstrMessageEvent, name: str):
        """创建 AI 群组
        /ai_group create <群组名称>
        """
        result = _request("POST", "/api/ai-group", {
            "enabled": True,
            "name": name,
            "people": [],
            "agents": [],
            "hapi_endpoint": "",
            "strategy": "auto",
        })
        if isinstance(result, dict) and "name" in result:
            yield event.plain_result(f"✅ AI 群组「{result['name']}」已创建")
        else:
            yield event.plain_result(f"创建失败: {result.get('error', result)}")

    @ai_group.command("add")
    async def ai_group_add(self, event: AstrMessageEvent, name: str, role: str = "member"):
        """拉人进 AI 群组
        /ai_group add <昵称> [角色]
        """
        # 先获取当前配置
        current = _request("GET", "/api/ai-group")
        if not isinstance(current, dict) or "name" not in current:
            yield event.plain_result("❌ 还没创建 AI 群组，先 /ai_group create <名称>")
            return

        people = current.get("people", [])
        people.append({"name": name, "role": role, "endpoint": None, "kind": None})

        result = _request("POST", "/api/ai-group", {
            "enabled": current.get("enabled", True),
            "name": current.get("name", ""),
            "people": people,
            "agents": current.get("agents", []),
            "hapi_endpoint": current.get("hapi_endpoint", ""),
            "strategy": current.get("strategy", "auto"),
        })
        if isinstance(result, dict) and "name" in result:
            yield event.plain_result(f"✅ 已将 {name}({role}) 加入 AI 群组")
        else:
            yield event.plain_result(f"添加失败: {result.get('error', result)}")

    @ai_group.command("send")
    async def ai_group_send(self, event: AstrMessageEvent, message: str):
        """向 AI 群组发送消息"""
        result = _request("POST", "/ai-groups/dispatch", {
            "message": message, "source": "astrbot_plugin",
        })
        yield event.plain_result(
            "✅ 已发送到 AI 群组" if result.get("success")
            else f"发送失败: {result.get('error', '未知错误')}"
        )

    @ai_group.command("list")
    async def ai_group_list(self, event: AstrMessageEvent):
        """查看 AI 群组成员"""
        result = _request("GET", "/api/ai-group")
        if not isinstance(result, dict):
            yield event.plain_result(f"获取失败: {result}")
            return
        name = result.get("name", "未命名")
        people = result.get("people", [])
        agents = result.get("agents", [])
        enabled = result.get("enabled", False)
        lines = [f"{'🟢' if enabled else '🔴'} AI 群组: {name}"]
        lines.append(f"\n👤 成员 ({len(people)}):")
        for p in people:
            lines.append(f"  - {p.get('name', '?')} ({p.get('role', 'member')})")
        lines.append(f"\n🤖 AI ({len(agents)}):")
        for a in agents:
            lines.append(f"  - {a.get('name', '?')} ({a.get('role', '?')})")
        yield event.plain_result("\n".join(lines))

    # ═══════════════ 模型加载 ═══════════════

    @model.command("load")
    async def model_load(self, event: AstrMessageEvent, backend: str = ""):
        """加载模型后端
        /model load [后端名称]
        """
        if not backend:
            yield event.plain_result("请指定后端名称，例如: /model load llama.cpp")
            return
        yield event.plain_result(f"正在加载 {backend}...（功能开发中）")

    @model.command("list")
    async def model_list(self, event: AstrMessageEvent):
        """查看可用的模型后端"""
        result = _request("GET", "/api/ai-group")
        yield event.plain_result("模型后端列表功能开发中，敬请期待")

    # ═══════════════ 帮助 ═══════════════

    @command("ef")
    async def eyeforge_help(self, event: AstrMessageEvent):
        """EyeForge 插件帮助"""
        help_text = (
            "🔧 EyeForge Desktop 插件\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📷 /screen view - 查看桌面截图\n"
            "📷 /screen info - 屏幕信息\n"
            "🖱 /click at <x> <y> - 点击坐标\n"
            "⌨️ /type text <内容> - 输入文本\n"
            "📜 /scroll to [dy] - 滚动\n"
            "🔑 /hotkey press <k1> <k2> - 快捷键\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👥 /ai_group create <名称> - 创建AI群组\n"
            "👥 /ai_group add <昵称> [角色] - 拉人\n"
            "👥 /ai_group list - 群组成员列表\n"
            "👥 /ai_group send <消息> - 群组发言\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 /model load <后端> - 加载模型\n"
            "🤖 /model list - 可用后端列表"
        )
        yield event.plain_result(help_text)
