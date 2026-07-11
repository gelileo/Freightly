from app import config
from engine.llm import FakeLlmClient
from app.transport import FakeTransport


def test_factories_default_to_fakes(monkeypatch):
    # Test the SELECTION logic in isolation: pretend .env is already loaded (so load_env is a
    # no-op and won't repopulate keys from a real .env on disk), and clear the credentials →
    # the factories must return the deterministic fakes. (The real Gemini/Gmail branches are
    # import-guarded and never exercised in CI.)
    monkeypatch.setattr(config, "_ENV_LOADED", True)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GMAIL_TOKEN_FILE", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("SMTP_ADDRESS", raising=False)
    assert isinstance(config.make_llm(), FakeLlmClient)
    assert isinstance(config.make_transport(), FakeTransport)


def _reset(monkeypatch, **env):
    monkeypatch.setattr(config, "_ENV_LOADED", True)  # don't read the real .env
    for k in ("SMTP_PASSWORD", "SMTP_ADDRESS", "GMAIL_TOKEN_FILE"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)


def test_make_transport_prefers_alibaba_then_fake(monkeypatch):
    from app.transport import AlibabaSmtpTransport
    _reset(monkeypatch, SMTP_PASSWORD="pw16")
    t = config.make_transport()
    assert isinstance(t, AlibabaSmtpTransport) and t.address == "hs@justnanoinc.com"
    _reset(monkeypatch)  # nothing set
    assert isinstance(config.make_transport(), FakeTransport)


def test_make_imap_config_defaults(monkeypatch):
    _reset(monkeypatch, SMTP_PASSWORD="pw16")
    cfg = config.make_imap_config()
    assert cfg["host"] == "imap.qiye.aliyun.com" and cfg["port"] == 993
    assert cfg["address"] == "hs@justnanoinc.com" and cfg["password"] == "pw16"


def test_load_env_reads_file_without_overriding_real_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('FOO_ONLY_IN_FILE=fromfile\nGEMINI_API_KEY="quoted_val"\n# comment\n')
    monkeypatch.setattr(config, "_ENV_LOADED", False)
    monkeypatch.setenv("GEMINI_API_KEY", "from_real_env")  # real env must win
    monkeypatch.delenv("FOO_ONLY_IN_FILE", raising=False)
    config.load_env(str(env))
    import os
    assert os.environ["FOO_ONLY_IN_FILE"] == "fromfile"       # loaded from file
    assert os.environ["GEMINI_API_KEY"] == "from_real_env"    # NOT overridden
    monkeypatch.setattr(config, "_ENV_LOADED", False)  # reset the module cache for other tests
