#!/usr/bin/env python3
"""Read CC Switch providers and query their enabled JavaScript usage scripts."""

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


RUNNER = r"""
const vm = require('node:vm');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  const payload = JSON.parse(input);
  const context = Object.create(null);
  context.response = payload.response;
  const options = { timeout: 5000, contextCodeGeneration: { strings: false, wasm: false } };
  const script = new vm.Script(`const config = (${payload.code});
    JSON.stringify(${payload.phase === 'request' ? 'config.request' : 'config.extractor(response)'})`);
  const result = script.runInNewContext(context, options);
  process.stdout.write(result ?? 'null');
});
"""


def run_js(code, response, phase):
    completed = subprocess.run(
        ["node", "-e", RUNNER], input=json.dumps({"code": code, "response": response, "phase": phase}),
        text=True, capture_output=True, timeout=7, check=False,
    )
    if completed.returncode:
        raise ValueError("额度脚本执行失败")
    return json.loads(completed.stdout)


def credentials(app, settings):
    env = settings.get("env") or {}
    if app == "codex":
        auth = settings.get("auth") or {}
        key = auth.get("OPENAI_API_KEY") or ""
        config = settings.get("config") or ""
        import re
        found = re.search(r'^\s*base_url\s*=\s*["\']([^"\']+)', config, re.M | re.I)
        return ((found.group(1) if found else "").rstrip("/"), key)
    if app in ("gemini", "agy"):
        return (env.get("GOOGLE_GEMINI_BASE_URL") or "").rstrip("/"), env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY") or ""
    if app in ("claude", "claude-desktop"):
        return (env.get("ANTHROPIC_BASE_URL") or "").rstrip("/"), next((env.get(k) for k in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "GOOGLE_API_KEY") if env.get(k)), "")
    if app == "openclaw":
        return (settings.get("baseUrl") or "").rstrip("/"), settings.get("apiKey") or ""
    if app == "hermes":
        return (settings.get("base_url") or "").rstrip("/"), settings.get("api_key") or ""
    return "", ""


def check_url(url, base, custom):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("无效的额度查询地址")
    loopback = parsed.hostname == "localhost" or parsed.hostname == "127.0.0.1" or parsed.hostname == "::1"
    if not custom and parsed.scheme != "https" and not loopback:
        raise ValueError("额度查询地址需要 HTTPS")
    if base and not custom:
        original = urllib.parse.urlparse(base)
        if parsed.hostname != original.hostname or (parsed.port or (443 if parsed.scheme == "https" else 80)) != (original.port or (443 if original.scheme == "https" else 80)):
            raise ValueError("额度查询地址与供应商地址不同源")


def query(script, app, settings):
    if script.get("templateType") in ("official_subscription", "token_plan", "balance", "github_copilot"):
        raise ValueError("此额度类型需要 CC Switch 应用内查询")
    base, key = credentials(app, settings)
    base = (script.get("baseUrl") or base).rstrip("/")
    key = script.get("apiKey") or key
    code = script.get("code") or ""
    for name, value in (("apiKey", key), ("baseUrl", base), ("accessToken", script.get("accessToken")), ("userId", script.get("userId"))):
        if value is not None:
            code = code.replace("{{" + name + "}}", str(value))
    request = run_js(code, None, "request")
    if not isinstance(request, dict) or not isinstance(request.get("url"), str):
        raise ValueError("额度脚本没有返回有效请求")
    url = request["url"]
    check_url(url, base, script.get("templateType") == "custom")
    method = request.get("method", "GET")
    if not isinstance(method, str) or method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        raise ValueError("不支持的额度查询方法")
    headers = request.get("headers") or {}
    if not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
        raise ValueError("额度脚本请求头无效")
    body = request.get("body")
    if body is not None and not isinstance(body, str):
        raise ValueError("额度脚本请求体无效")
    timeout = max(2, min(30, int(script.get("timeout") or 10)))
    req = urllib.request.Request(url, data=body.encode() if body is not None else None, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as error:
        raise ValueError("额度接口 HTTP " + str(error.code)) from None
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("额度响应过大")
    data = run_js(code, json.loads(raw), "extract")
    rows = data if isinstance(data, list) else [data]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("额度脚本返回的数据格式不正确")
    return [{k: row.get(k) for k in ("planName", "remaining", "total", "used", "unit", "extra", "isValid", "invalidMessage")} for row in rows]


def main():
    config = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".cc-switch").resolve()
    db_path = config / "cc-switch.db"
    if not db_path.is_file():
        print(json.dumps({"error": "未找到 CC Switch 数据库", "cards": []}, ensure_ascii=False))
        return
    db = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True, timeout=2)
    try:
        providers = db.execute("SELECT app_type, name, settings_config, meta FROM providers WHERE is_current = 1 ORDER BY app_type, name").fetchall()
    finally:
        db.close()
    cards = []
    for app, name, settings_raw, meta_raw in providers:
        try:
            settings = json.loads(settings_raw)
            meta = json.loads(meta_raw)
            script = meta.get("usage_script") or {}
            if not script.get("enabled"):
                continue
            card = {"app": app, "name": name, "data": []}
            try:
                card["data"] = query(script, app, settings)
            except (ValueError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
                card["error"] = str(error) if not isinstance(error, OSError) else "额度查询连接失败"
            cards.append(card)
        except (ValueError, TypeError, AttributeError):
            continue
    print(json.dumps({"cards": cards}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (sqlite3.Error, OSError) as error:
        print(json.dumps({"error": "读取 CC Switch 数据库失败", "cards": []}, ensure_ascii=False))
