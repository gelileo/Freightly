"""WeChat auth client port. FakeWeChatClient keeps login hermetic in tests; RealWeChatClient
calls Tencent's jscode2session with stdlib urllib (deferred imports, no pip dependency).
Mirrors the LlmClient / MailTransport port+fake+real pattern."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class WeChatSession:
    openid: str
    unionid: str | None
    session_key: str


class WeChatClient(Protocol):
    def code2session(self, js_code: str) -> WeChatSession: ...


class FakeWeChatClient:
    """Deterministic, offline. Maps js_code -> stable openid; 'bad'/'' raise like a real reject."""

    def code2session(self, js_code: str) -> WeChatSession:
        if not js_code or js_code == "bad":
            raise ValueError("invalid js_code")
        return WeChatSession(openid=f"openid-{js_code}", unionid=f"union-{js_code}",
                             session_key=f"sk-{js_code}")


class RealWeChatClient:
    ENDPOINT = "https://api.weixin.qq.com/sns/jscode2session"

    def __init__(self, appid: str, secret: str):
        self.appid, self.secret = appid, secret

    def code2session(self, js_code: str) -> WeChatSession:
        import json
        import urllib.parse
        import urllib.request
        query = urllib.parse.urlencode({
            "appid": self.appid, "secret": self.secret,
            "js_code": js_code, "grant_type": "authorization_code"})
        with urllib.request.urlopen(f"{self.ENDPOINT}?{query}", timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("errcode"):
            raise ValueError(f"wechat error {data.get('errcode')}: {data.get('errmsg')}")
        return WeChatSession(openid=data["openid"], unionid=data.get("unionid"),
                             session_key=data["session_key"])
