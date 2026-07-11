import os
import pytest

from app.wechat import FakeWeChatClient, WeChatSession


def test_fake_code2session_deterministic():
    c = FakeWeChatClient()
    s = c.code2session("code123")
    assert isinstance(s, WeChatSession)
    assert s.openid == "openid-code123" and s.unionid == "union-code123"
    assert s.session_key == "sk-code123"
    # same input → same openid (stable identity)
    assert c.code2session("code123").openid == s.openid


def test_fake_rejects_bad_code():
    with pytest.raises(ValueError):
        FakeWeChatClient().code2session("bad")
    with pytest.raises(ValueError):
        FakeWeChatClient().code2session("")


@pytest.mark.skipif(not os.environ.get("WECHAT_APPID"),
                    reason="no WECHAT_APPID; skip live WeChat call")
def test_real_client_constructs():
    from app.wechat import RealWeChatClient
    c = RealWeChatClient(os.environ["WECHAT_APPID"], os.environ.get("WECHAT_SECRET", ""))
    assert c is not None  # a real code2session needs a live js_code from a device
