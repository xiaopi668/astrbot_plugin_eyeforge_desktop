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

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools

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


class EyeForgeDesktopPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        global EYEFORGE_HOST, EYEFORGE_PORT, EYEFORGE_TOKEN
        EYEFORGE_HOST = config.get("host", "127.0.0.1")
        EYEFORGE_PORT = int(config.get("port", 9178))
        EYEFORGE_TOKEN = config.get("token", "")

    @filter.command("screen")
    async def screen(self, event: AstrMessageEvent):
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
        yield event.image_result(img_b64)
        yield event.plain_result(f"桌面截图 ({result.get('width',0)}x{result.get('height',0)})")

    @filter.command("screen_info")
    async def screen_info(self, event: AstrMessageEvent):
        """查看屏幕信息"""
        result = _request("GET", "/api/screen-info")
        if result.get("success"):
            yield event.plain_result(
                f"屏幕信息:\n  分辨率: {result['width']}x{result['height']}\n  显示器数量: {result['count']}"
            )
        else:
            yield event.plain_result(f"获取屏幕信息失败: {result.get('error', '未知错误')}")

    @filter.command("click")
    async def click(self, event: AstrMessageEvent, x: int, y: int,
                    button: str = "left", double: bool = False):
        """点击坐标"""
        result = _request("POST", "/api/desktop/click", {
            "x": x, "y": y, "button": button, "double": double,
        })
        yield event.plain_result(
            f"已点击 ({x}, {y})" if result.get("success")
            else f"点击失败: {result.get('error', '未知错误')}"
        )

    @filter.command("type")
    async def type_text(self, event: AstrMessageEvent, text: str):
        """输入文本"""
        result = _request("POST", "/api/desktop/type", {"text": text})
        yield event.plain_result(
            f"已输入: {text[:50]}{'...' if len(text) > 50 else ''}"
            if result.get("success")
            else f"输入失败: {result.get('error', '未知错误')}"
        )

    @filter.command("scroll")
    async def scroll(self, event: AstrMessageEvent,
                     delta_y: int = -3, x: int = 0, y: int = 0):
        """滚动"""
        result = _request("POST", "/api/desktop/scroll", {
            "x": x, "y": y, "delta_x": 0, "delta_y": delta_y,
        })
        yield event.plain_result(
            f"已滚动 ({delta_y})" if result.get("success")
            else f"滚动失败: {result.get('error', '未知错误')}"
        )

    @filter.command("hotkey")
    async def hotkey(self, event: AstrMessageEvent, keys: str):
        """模拟快捷键"""
        key_list = [k.strip() for k in re.split(r"[ ,]+", keys) if k.strip()]
        result = _request("POST", "/api/desktop/hotkey", {"keys": key_list})
        yield event.plain_result(
            f"已执行: {' + '.join(key_list)}" if result.get("success")
            else f"快捷键失败: {result.get('error', '未知错误')}"
        )

    @filter.command("ai_group")
    async def ai_group(self, event: AstrMessageEvent, action: str = "", name: str = "",
                       role: str = "member", message: str = ""):
        """AI 群组管理
        用法:
          /ai_group create <名称>
          /ai_group add <昵称> [角色]
          /ai_group list
          /ai_group send <消息>
        """
        if action == "create" and name:
            result = _request("POST", "/api/ai-group", {
                "enabled": True, "name": name,
                "people": [], "agents": [],
                "hapi_endpoint": "", "strategy": "auto",
            })
            yield event.plain_result(
                f"✅ AI 群组「{name}」已创建" if isinstance(result, dict) and "name" in result
                else f"创建失败: {result.get('error', result)}"
            )
        elif action == "add" and name:
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
            yield event.plain_result(
                f"✅ 已将 {name}({role}) 加入 AI 群组"
                if isinstance(result, dict) and "name" in result
                else f"添加失败: {result.get('error', result)}"
            )
        elif action == "list":
            result = _request("GET", "/api/ai-group")
            if not isinstance(result, dict):
                yield event.plain_result(f"获取失败: {result}")
                return
            lines = [f"{'🟢' if result.get('enabled') else '🔴'} AI 群组: {result.get('name','未命名')}"]
            lines.append(f"\n👤 成员 ({len(result.get('people',[]))}):")
            for p in result.get("people", []):
                lines.append(f"  - {p.get('name','?')} ({p.get('role','member')})")
            lines.append(f"\n🤖 AI ({len(result.get('agents',[]))}):")
            for a in result.get("agents", []):
                lines.append(f"  - {a.get('name','?')} ({a.get('role','?')})")
            yield event.plain_result("\n".join(lines))
        elif action == "send" and message:
            result = _request("POST", "/ai-groups/dispatch", {
                "message": message, "source": "astrbot_plugin",
            })
            yield event.plain_result(
                "✅ 已发送到 AI 群组" if result.get("success")
                else f"发送失败: {result.get('error', '未知错误')}"
            )
        else:
            yield event.plain_result(
                "用法:\n"
                "  /ai_group create <名称>\n"
                "  /ai_group add <昵称> [角色]\n"
                "  /ai_group list\n"
                "  /ai_group send <消息>"
            )

    @filter.command("model")
    async def model(self, event: AstrMessageEvent, action: str = "", name: str = ""):
        """模型管理
        用法:
          /model list   - 查看可用后端
          /model status - 查看加载状态
          /model load <后端名> - 加载模型
        """
        if action == "list":
            result = _request("GET", "/api/model/list")
            if isinstance(result, list):
                lines = ["🤖 可用模型后端:"]
                for b in result:
                    status = "✅" if b.get("available") else "⬜"
                    fmts = ", ".join(b.get("formats", []))
                    lines.append(f"  {status} {b['name']}  [{fmts}]")
                yield event.plain_result("
".join(lines))
            else:
                yield event.plain_result(f"获取失败: {result}")
        elif action == "status":
            result = _request("GET", "/api/model/status")
            if result.get("success"):
                backends = result.get("loaded_backends", [])
                yield event.plain_result(
                    f"已加载后端 ({len(backends)}):
" +
                    "
".join(f"  ✅ {b}" for b in backends) +
                    f"
📚 知识库条目: {result.get('kb_count', 0)}"
                )
            else:
                yield event.plain_result(f"获取失败: {result.get('error', '未知错误')}")
        elif action == "load" and name:
            result = _request("POST", "/api/model/load", {
                "backend": name, "device": "auto",
            })
            yield event.plain_result(
                f"✅ {result.get('message', '加载请求已发送')}"
                if result.get("success")
                else f"加载失败: {result.get('error', '未知错误')}"
            )
        else:
            yield event.plain_result(
                "用法:
"
                "  /model list
"
                "  /model status
"
                "  /model load <后端名>"
            )

    @filter.command("ef")
    async def help(self, event: AstrMessageEvent):
        """EyeForge 插件帮助"""
        yield event.plain_result(
            "🔧 EyeForge Desktop 插件\n"
            "━━━━━━━━━━━━━━\n"
            "📷 /screen - 查看桌面截图\n"
            "📊 /screen_info - 屏幕信息\n"
            "🖱 /click <x> <y> - 点击坐标\n"
            "⌨️ /type <文本> - 输入文本\n"
            "📜 /scroll [dy] - 滚动\n"
            "🔑 /hotkey <k1> <k2> - 快捷键\n"
            "━━━━━━━━━━━━━━\n"
            "👥 /ai_group create <名称>\n"
            "👥 /ai_group add <昵称> [角色]\n"
            "👥 /ai_group list\n"
            "👥 /ai_group send <消息>"
        )
