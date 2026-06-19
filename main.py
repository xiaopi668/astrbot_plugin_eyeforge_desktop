"""
EyeForge Desktop - AstrBot Plugin
"""
import base64, json, re, urllib.request, urllib.error
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

HOST = "127.0.0.1"
PORT = 9178
TOKEN = ""

def api(path):
    return f"http://{HOST}:{PORT}{path}"

def req(method, path, body=None):
    url = api(path)
    data = json.dumps(body).encode("utf-8") if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if TOKEN:
        r.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e)}

class EyeForgeDesktopPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        global HOST, PORT, TOKEN
        HOST = config.get("host", "127.0.0.1")
        PORT = int(config.get("port", 9178))
        TOKEN = config.get("token", "")

    @filter.command("screen")
    async def screen(self, event: AstrMessageEvent):
        r = req("GET", "/api/screenshot")
        if r.get("success"):
            yield event.image_result(r["data"])
            yield event.plain_result(f"桌面截图 ({r.get('width',0)}x{r.get('height',0)})")
        else:
            yield event.plain_result(f"截图失败: {r.get('error','?')}")

    @filter.command("screen_info")
    async def screen_info(self, event: AstrMessageEvent):
        r = req("GET", "/api/screen-info")
        if r.get("success"):
            yield event.plain_result(f"分辨率: {r['width']}x{r['height']}\n显示器: {r['count']}")
        else:
            yield event.plain_result(f"失败: {r.get('error','?')}")

    @filter.command("click")
    async def click(self, event: AstrMessageEvent, x: int, y: int, button: str = "left", double: bool = False):
        r = req("POST", "/api/desktop/click", {"x":x,"y":y,"button":button,"double":double})
        yield event.plain_result("ok" if r.get("success") else f"fail: {r.get('error','?')}")

    @filter.command("type")
    async def type_t(self, event: AstrMessageEvent, text: str):
        r = req("POST", "/api/desktop/type", {"text":text})
        yield event.plain_result("ok" if r.get("success") else f"fail: {r.get('error','?')}")

    @filter.command("scroll")
    async def scroll(self, event: AstrMessageEvent, delta_y: int = -3):
        r = req("POST", "/api/desktop/scroll", {"x":0,"y":0,"delta_y":delta_y})
        yield event.plain_result("ok" if r.get("success") else f"fail: {r.get('error','?')}")

    @filter.command("hotkey")
    async def hotkey(self, event: AstrMessageEvent, keys: str):
        kl = [k.strip() for k in re.split(r"[ ,]+", keys) if k.strip()]
        r = req("POST", "/api/desktop/hotkey", {"keys":kl})
        yield event.plain_result("ok" if r.get("success") else f"fail: {r.get('error','?')}")

    @filter.command("ai_group")
    async def ai_group(self, event: AstrMessageEvent, action: str = "", name: str = "", role: str = "member", message: str = ""):
        if action == "create" and name:
            r = req("POST", "/api/ai-group", {"enabled":True,"name":name,"people":[],"agents":[],"hapi_endpoint":"","strategy":"auto"})
            yield event.plain_result(f"群组 {name} 已创建" if isinstance(r,dict) and "name" in r else f"创建失败: {r}")
        elif action == "add" and name:
            cur = req("GET", "/api/ai-group")
            if not isinstance(cur, dict) or "name" not in cur:
                yield event.plain_result("请先创建群组")
                return
            p = cur.get("people", [])
            p.append({"name":name,"role":role,"endpoint":None,"kind":None})
            r = req("POST", "/api/ai-group", {**cur, "people":p})
            yield event.plain_result(f"{name} 已加入" if isinstance(r,dict) and "name" in r else f"添加失败: {r}")
        elif action == "list":
            cur = req("GET", "/api/ai-group")
            if not isinstance(cur, dict):
                yield event.plain_result(f"获取失败: {cur}")
                return
            lines = [f"{'ON' if cur.get('enabled') else 'OFF'} {cur.get('name','?')}"]
            lines.append(f"成员 ({len(cur.get('people',[]))}):")
            for p in cur.get("people",[]):
                lines.append(f"  - {p.get('name','?')} ({p.get('role','?')})")
            lines.append(f"AI ({len(cur.get('agents',[]))}):")
            for a in cur.get("agents",[]):
                lines.append(f"  - {a.get('name','?')}")
            yield event.plain_result("\n".join(lines))
        elif action == "send" and message:
            r = req("POST", "/ai-groups/dispatch", {"message":message,"source":"astrbot_plugin"})
            yield event.plain_result("已发送" if r.get("success") else f"发送失败: {r.get('error','?')}")
        else:
            yield event.plain_result("用法: create/ add/ list/ send")

    @filter.command("model")
    async def model(self, event: AstrMessageEvent, action: str = "", name: str = ""):
        if action == "list":
            r = req("GET", "/api/model/list")
            if isinstance(r, list):
                lines = ["可用后端:"]
                for b in r:
                    s = "OK" if b.get("available") else "-"
                    f = ", ".join(b.get("formats",[]))
                    lines.append(f"  {s} {b['name']} [{f}]")
                yield event.plain_result("\n".join(lines))
            else:
                yield event.plain_result(f"获取失败: {r}")
        elif action == "status":
            r = req("GET", "/api/model/status")
            if r.get("success"):
                bs = r.get("loaded_backends",[])
                yield event.plain_result(f"已加载 ({len(bs)}):\n" + "\n".join(f"  OK {b}" for b in bs))
            else:
                yield event.plain_result(f"获取失败: {r.get('error','?')}")
        elif action == "load" and name:
            r = req("POST", "/api/model/load", {"backend":name,"device":"auto"})
            yield event.plain_result(r.get("message","ok") if r.get("success") else f"加载失败: {r.get('error','?')}")
        else:
            yield event.plain_result("用法: /model list | status | load <name>")

    @filter.command("ef")
    async def help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "EyeForge Desktop\n"
            "/screen  /screen_info\n"
            "/click <x> <y>\n"
            "/type <text>\n"
            "/scroll [dy]\n"
            "/hotkey <k1> <k2>\n"
            "/ai_group create|add|list|send\n"
            "/model list|status|load"
        )
