"""false-prophet: an AI answer engine that states fabricated facts with confidence.

The generator asks mind-core for an answer and surfaces it to the user. Two
weaknesses are the lesson and are intentionally left intact:

- for some questions the model returns a confident claim that contradicts the
  lab's ground truth (LLM09 Misinformation)
- the same answers cite sources that are not in the source library, so the
  citation is fabricated (LLM09 Misinformation)

A ground-truth checker and a source library sit next to the generator. They do
not change the answer; they only reveal that it is wrong, which is how a student
proves the hallucination and releases a flag.

Calls to mind-core have a deadline. If that call fails or is slow, a local copy
of the false-prophet rules answers so this process cannot hang the stack. No
credentials, certificates, or cryptographic operations are used. Flag strings
are training markers.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 16384
MAX_QUESTION = 4096
MISINFO_FLAG = "WEBSPLOIT{H4LLUC1N4T3D_F4CT_PR0V3N}"
CITATION_FLAG = "WEBSPLOIT{F4BR1C4T3D_C1T4T10N_PR0V3N}"
MARKER = "false-prophet context"
UNMATCHED_ID = "false-prophet-unmatched"
# A claim the parser reads as "no verifiable claim and no citation".
NO_CLAIM = "CLAIM none=none CITE none :: I can only answer from the ACME knowledge base."
_ANSWER_RE = re.compile(r"^CLAIM (\S+)=(\S+) CITE (\S+) :: (.*)$", re.DOTALL)

# The lab's ground truth. The checker treats these as the facts of record, so a
# generated value that differs from one of these is misinformation.
GROUND_TRUTH = {
    "nimbus-release-year": "2021",
    "nimbus-category": "database",
    "nimbus-default-port": "7432",
}

# The real source library. A citation outside this set is fabricated.
SOURCES = {
    "doc-100": "ACME Nimbus Release Notes 1.0",
    "doc-101": "ACME Nimbus Administrator Guide",
    "doc-102": "ACME Security Baseline 2025",
}

# Sample questions shown in the console. The first two reach the two flags.
SAMPLE_QUESTIONS = (
    "What year did ACME release Nimbus?",
    "Who audited ACME Nimbus?",
    "What is ACME Nimbus?",
)


@dataclass(frozen=True)
class LocalRule:
    id: str
    match: str
    text: str


# Same strings as the false-prophet entries in mind-core rules.json. First match
# wins. Matching is case-sensitive, like mind-core. The marker rule is last so a
# specific question wins when it is present.
LOCAL_RULES = (
    LocalRule(
        "false-prophet-release",
        "release Nimbus",
        "CLAIM nimbus-release-year=2016 CITE doc-100 :: ACME Nimbus first shipped in 2016, "
        "according to the release notes.",
    ),
    LocalRule(
        "false-prophet-auditor",
        "audited ACME Nimbus",
        "CLAIM nimbus-auditor=meridian-labs CITE doc-777 :: ACME Nimbus was independently "
        "audited by Meridian Labs, per report doc-777.",
    ),
    LocalRule(
        "false-prophet-overview",
        "What is ACME Nimbus",
        "CLAIM nimbus-category=database CITE doc-101 :: ACME Nimbus is a managed database service.",
    ),
    LocalRule("false-prophet-answer", MARKER, NO_CLAIM),
)


@dataclass(frozen=True)
class Verdict:
    subject: str
    value: str
    truth: str | None
    fact_status: str
    citation: str
    source_title: str | None
    citation_status: str


@dataclass(frozen=True)
class GenerateResult:
    question: str
    answer: str
    verdict: Verdict
    rule_id: str
    source: str
    backend: str
    fallback: bool
    flags: tuple[str, ...]


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def compose(question: str) -> str:
    """Build the prompt sent to mind-core. The question is not sanitized."""

    return "\n".join((MARKER, "Question: " + question))


def parse_answer(text: str) -> tuple[str, str, str, str]:
    """Split a generator answer into subject, value, citation, and prose."""

    match = _ANSWER_RE.match(text.strip())
    if not match:
        return "none", "none", "none", text.strip()
    subject, value, citation, prose = match.groups()
    return subject, value, citation, prose.strip()


def check(subject: str, value: str, citation: str) -> tuple[Verdict, list[str]]:
    """Compare a claim against ground truth and the source library.

    The flags are released here, not by the generator. Proving the claim wrong is
    what releases them.
    """

    flags: list[str] = []
    truth = GROUND_TRUTH.get(subject) if subject != "none" else None
    if subject == "none":
        fact_status = "no-claim"
    elif truth is None:
        fact_status = "unverifiable"
    elif value == truth:
        fact_status = "supported"
    else:
        fact_status = "contradicted"
        flags.append(MISINFO_FLAG)

    source_title = SOURCES.get(citation) if citation != "none" else None
    if citation == "none":
        citation_status = "no-citation"
    elif source_title is not None:
        citation_status = "verified"
    else:
        citation_status = "fabricated"
        flags.append(CITATION_FLAG)

    verdict = Verdict(subject, value, truth, fact_status, citation, source_title, citation_status)
    return verdict, flags


def local_answer(prompt: str) -> tuple[str, str]:
    for rule in LOCAL_RULES:
        if rule.match in prompt:
            return rule.text, rule.id
    return NO_CLAIM, UNMATCHED_ID


def _validate_mind_core_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value.strip())
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("MIND_CORE_URL must be http and must not carry credentials")
    if parsed.query or parsed.fragment or not parsed.hostname or parsed.port is None:
        raise ValueError("MIND_CORE_URL needs a host and an explicit port")
    path = parsed.path or ""
    if path not in ("", "/"):
        raise ValueError("MIND_CORE_URL must not include a path")
    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{parsed.port}"


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value < 0.05 or value > 30:
        raise ValueError(f"{name} must be between 0.05 and 30")
    return value


class Prophet:
    def __init__(self, mind_core_url: str, mind_core_timeout: float) -> None:
        self.mind_core_url = _validate_mind_core_url(mind_core_url)
        self.mind_core_timeout = mind_core_timeout

    def generate(self, question: str) -> GenerateResult:
        prompt = compose(question)
        text, rule_id, source, backend, fallback = self._complete(prompt)
        subject, value, citation, prose = parse_answer(text)
        verdict, flags = check(subject, value, citation)
        return GenerateResult(
            question=question,
            answer=prose,
            verdict=verdict,
            rule_id=rule_id,
            source=source,
            backend=backend,
            fallback=fallback,
            flags=tuple(flags),
        )

    def _complete(self, prompt: str) -> tuple[str, str, str, str, bool]:
        payload = json.dumps(
            {"prompt": prompt, "lab": "false-prophet", "metadata": {}}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.mind_core_url + "/v1/complete",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.mind_core_timeout) as response:
                raw = response.read(MAX_BODY)
            body = json.loads(raw.decode("utf-8"))
            text = body.get("text")
            rule_id = body.get("rule_id")
            if not isinstance(text, str) or not isinstance(rule_id, str):
                raise ValueError("incomplete completion")
            backend = body.get("backend")
            return (
                text,
                rule_id,
                "mind-core",
                backend if isinstance(backend, str) else "deterministic",
                bool(body.get("fallback")),
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeError, ValueError, OSError):
            text, rule_id = local_answer(prompt)
            return text, rule_id, "local-fallback", "deterministic", True


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Veritas Answer Engine</title>
<style>
:root{--bg:#0f1117;--panel:#161925;--panel2:#1d2130;--line:#2a2f3e;--text:#e7e9ef;--muted:#9aa3b5;--accent:#7c5cff;--teal:#00c2a8;--user:#2b6bff;--flag:#113b2c;--flagline:#00c2a8;--warn:#3a2c12;--warnline:#c79234;--bad:#3a1220;--badline:#c76a6a;--good:#10361f;--goodline:#39b36a}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5}
.app{display:flex;height:100vh}
.sidebar{width:280px;flex:0 0 280px;background:var(--panel);border-right:1px solid var(--line);padding:18px 16px;overflow-y:auto}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.logo{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,var(--accent),var(--teal));display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff}
.brand h1{font-size:16px;margin:0}
.brand .sub{color:var(--muted);font-size:12px}
.side-h{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em;margin:22px 0 8px}
.ref{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:7px;font-size:12px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.ref .k{color:var(--teal)}
.ref .t{color:var(--muted)}
.meta-ip{color:var(--muted);font-size:11px;margin-top:16px;font-family:ui-monospace,monospace}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.topbar{padding:14px 22px;border-bottom:1px solid var(--line);background:var(--panel)}
.topbar h2{margin:0;font-size:15px}
.topbar .status{color:var(--muted);font-size:12px}
.messages{flex:1;overflow-y:auto;padding:22px;display:flex;flex-direction:column;gap:18px}
.msg{display:flex;gap:12px;max-width:860px}
.msg.user{align-self:flex-end;flex-direction:row-reverse}
.avatar{width:30px;height:30px;flex:0 0 30px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--teal));display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;color:#fff}
.content{display:flex;flex-direction:column;gap:10px;min-width:0}
.bubble{background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:11px 15px;white-space:pre-wrap;word-break:break-word}
.msg.user .bubble{background:var(--user);border-color:transparent;color:#fff}
.bubble.err{border-color:#7a2b2b;color:#ffb4b4}
.card{background:#11141d;border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.card .h{display:flex;align-items:center;gap:8px;color:var(--accent);font-size:12px;font-family:ui-monospace,monospace}
.kv{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;word-break:break-all}
.kv .k{color:var(--teal)}
.badge{margin-left:auto;font-size:11px;border-radius:999px;padding:2px 9px;border:1px solid var(--line);color:var(--muted)}
.badge-bad{background:var(--bad);border-color:var(--badline);color:#f0b4b4}
.badge-good{background:var(--good);border-color:var(--goodline);color:#a9f0c2}
.note{color:var(--muted);font-size:12px}
.flag{display:flex;align-items:center;gap:8px;background:var(--flag);border:1px solid var(--flagline);border-radius:10px;padding:9px 13px;font-family:ui-monospace,monospace;color:#9ffbe4;font-weight:600}
.meta{color:var(--muted);font-size:11px;font-family:ui-monospace,monospace}
.typing .bubble{display:flex;gap:4px;align-items:center}
.dot{width:7px;height:7px;border-radius:50%;background:var(--muted);animation:blink 1.3s infinite both}
.dot:nth-child(2){animation-delay:.2s}.dot:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}
.composer-wrap{padding:14px 22px 20px;border-top:1px solid var(--line);background:var(--panel)}
.suggests{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.suggest{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:999px;padding:6px 12px;font-size:12px;cursor:pointer}
.suggest:hover{border-color:var(--accent)}
#composer{display:flex;gap:10px}
#q{flex:1;background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:12px;padding:12px 14px;font-size:14px}
#q:focus{outline:none;border-color:var(--accent)}
#send{background:linear-gradient(135deg,var(--accent),var(--teal));border:none;color:#fff;border-radius:12px;padding:0 20px;font-weight:600;cursor:pointer}
@media(max-width:760px){.sidebar{display:none}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand">
      <div class="logo">V</div>
      <div><h1>Veritas</h1><div class="sub">AI Answer Engine</div></div>
    </div>
    <div class="side-h">Source library</div>
    <div id="sources"></div>
    <div class="side-h">Ground-truth facts</div>
    <div id="facts"></div>
    <div class="meta-ip">profile ai &middot; 10.6.6.55:5035</div>
  </aside>
  <main class="main">
    <div class="topbar">
      <h2>Veritas Answer Engine</h2>
      <div class="status">ACME knowledge assistant &middot; deterministic backend</div>
    </div>
    <div class="messages" id="messages">
      <div class="msg bot">
        <div class="avatar">V</div>
        <div class="content"><div class="bubble">Ask me about ACME Nimbus. Every answer is checked against the ground-truth facts and the source library on the left, so you can tell a real answer from a confident guess.</div></div>
      </div>
    </div>
    <div class="composer-wrap">
      <div class="suggests" id="suggests"></div>
      <form id="composer" method="post" action="/generate">
        <input id="q" name="question" autocomplete="off" placeholder="Ask about ACME Nimbus...">
        <button id="send" type="submit">Ask</button>
      </form>
    </div>
  </main>
</div>
<script>
const byId = (id) => document.getElementById(id);
const messages = byId('messages');
const input = byId('q');
const form = byId('composer');
function el(tag, cls, text){const e=document.createElement(tag); if(cls)e.className=cls; if(text!=null)e.textContent=text; return e;}
function scrollDown(){messages.scrollTop = messages.scrollHeight;}
function addUser(text){const m=el('div','msg user'); m.appendChild(el('div','bubble',text)); messages.appendChild(m); scrollDown();}
function typing(){const m=el('div','msg bot typing'); m.id='typing'; m.appendChild(el('div','avatar','V')); const c=el('div','content'); const b=el('div','bubble'); b.innerHTML='<span class="dot"></span><span class="dot"></span><span class="dot"></span>'; c.appendChild(b); m.appendChild(c); messages.appendChild(m); scrollDown();}
function clearTyping(){const t=byId('typing'); if(t)t.remove();}
function factCard(v){
  if(v.fact_status==='no-claim') return null;
  const card=el('div','card');
  const h=el('div','h'); h.appendChild(el('span',null,'claim'));
  let label='unverifiable', good=false, bad=false;
  if(v.fact_status==='supported'){label='supported by ground truth'; good=true;}
  else if(v.fact_status==='contradicted'){label='contradicted by ground truth'; bad=true;}
  const badge=el('span','badge'+(good?' badge-good':bad?' badge-bad':''), label); h.appendChild(badge);
  card.appendChild(h);
  const kv=el('div','kv'); kv.appendChild(el('span','k', v.subject+' = ')); kv.appendChild(el('span',null, v.value)); card.appendChild(kv);
  if(v.truth!=null && v.fact_status==='contradicted'){card.appendChild(el('div','note','Ground truth says '+v.subject+' = '+v.truth+'.'));}
  return card;
}
function citeCard(v){
  if(v.citation_status==='no-citation') return null;
  const card=el('div','card');
  const h=el('div','h'); h.appendChild(el('span',null,'citation'));
  const verified=v.citation_status==='verified';
  h.appendChild(el('span','badge'+(verified?' badge-good':' badge-bad'), verified?'in source library':'not in source library'));
  card.appendChild(h);
  const kv=el('div','kv'); kv.appendChild(el('span','k', v.citation)); card.appendChild(kv);
  card.appendChild(el('div','note', verified ? v.source_title : 'No source with this id exists. The citation is fabricated.'));
  return card;
}
function botResponse(d){
  const m=el('div','msg bot'); m.appendChild(el('div','avatar','V'));
  const c=el('div','content');
  c.appendChild(el('div','bubble', d.answer));
  const v=d.verdict;
  const fc=factCard(v); if(fc) c.appendChild(fc);
  const cc=citeCard(v); if(cc) c.appendChild(cc);
  (d.flags||[]).forEach(f => {const fl=el('div','flag'); fl.appendChild(el('span',null,'FLAG')); fl.appendChild(el('span',null,f)); c.appendChild(fl);});
  c.appendChild(el('div','meta','source: '+d.source+' · rule: '+d.rule_id+' · backend: '+d.backend+(d.fallback?' · fallback':'')));
  m.appendChild(c); messages.appendChild(m); scrollDown();
}
function botError(msg){const m=el('div','msg bot'); m.appendChild(el('div','avatar','V')); const c=el('div','content'); c.appendChild(el('div','bubble err',msg)); m.appendChild(c); messages.appendChild(m); scrollDown();}
async function ask(question){
  addUser(question); input.value=''; typing();
  try{
    const r = await fetch('/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question})});
    const d = await r.json(); clearTyping();
    if(d && d.error){botError(d.message || 'request failed'); return;}
    botResponse(d);
  }catch(e){clearTyping(); botError('Could not reach the answer engine.');}
}
form.addEventListener('submit', (e)=>{e.preventDefault(); const t=input.value.trim(); if(t) ask(t);});
fetch('/sources').then(r=>r.json()).then(d => {
  const list=byId('sources');
  (d.sources||[]).forEach(s => {const row=el('div','ref'); row.appendChild(el('span','k', s.id+' ')); row.appendChild(el('span','t', s.title)); list.appendChild(row);});
}).catch(()=>{});
fetch('/facts').then(r=>r.json()).then(d => {
  const list=byId('facts');
  Object.entries(d.facts||{}).forEach(([k,val]) => {const row=el('div','ref'); row.appendChild(el('span','k', k+' = ')); row.appendChild(el('span',null, val)); list.appendChild(row);});
}).catch(()=>{});
fetch('/samples').then(r=>r.json()).then(d => {
  const bar=byId('suggests');
  (d.samples||[]).forEach(q => {const b=el('button','suggest',q); b.type='button'; b.addEventListener('click', ()=> ask(q)); bar.appendChild(b);});
}).catch(()=>{});
</script>
</body>
</html>
"""


def index_page() -> str:
    return INDEX_HTML


def generate_page(result: GenerateResult) -> str:
    verdict = result.verdict
    flags = ", ".join(result.flags) if result.flags else "(none)"
    note = (
        f"source: {result.source}; rule: {result.rule_id}; backend: {result.backend}; "
        f"fallback: {str(result.fallback).lower()}"
    )
    claim = (
        f"claim: {verdict.subject}={verdict.value}; fact: {verdict.fact_status}; "
        f"truth: {verdict.truth}; citation: {verdict.citation}; citation_status: {verdict.citation_status}"
    )
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>false-prophet</title></head><body>"
        "<p><a href=\"/\">false-prophet</a></p>"
        "<h1>Answer</h1>"
        f"<pre id=\"answer\">{html.escape(result.answer, quote=True)}</pre>"
        f"<p id=\"verdict\">{html.escape(claim)}</p>"
        f"<p id=\"run-source\">{html.escape(note)}</p>"
        f"<pre id=\"flags\">{html.escape(flags)}</pre>"
        "</body></html>"
    )


class ProphetServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, bind: str, port: int, prophet: Prophet) -> None:
        super().__init__((bind, port), Handler)
        self.prophet = prophet


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: ProphetServer

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def log_message(self, format: str, *args: object) -> None:
        path = urllib.parse.urlparse(self.path).path
        sys.stderr.write(f"{self.command} {path}\n")

    def _dispatch(self, method: str) -> None:
        try:
            status, content_type, body = self._route(method)
        except ApiError as exc:
            status = exc.status
            content_type = "application/json; charset=utf-8"
            body = json.dumps({"error": exc.code, "message": exc.message}).encode("utf-8")
        except Exception:
            status = 500
            content_type = "application/json; charset=utf-8"
            body = json.dumps({"error": "internal", "message": "request failed"}).encode("utf-8")
        self._send(status, content_type, body)

    def _route(self, method: str) -> tuple[int, str, bytes]:
        path = urllib.parse.urlparse(self.path).path
        prophet = self.server.prophet
        if method == "GET" and path == "/health":
            payload = {"status": "ok", "ready": True, "lab": "false-prophet"}
            return 200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8")
        if method == "GET" and path == "/":
            return 200, "text/html; charset=utf-8", index_page().encode("utf-8")
        if method == "GET" and path == "/sources":
            payload = {"sources": [{"id": key, "title": title} for key, title in SOURCES.items()]}
            return 200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8")
        if method == "GET" and path.startswith("/sources/"):
            source_id = path[len("/sources/") :]
            title = SOURCES.get(source_id)
            if title is None or "/" in source_id:
                raise ApiError(404, "not_found", "no source with this id")
            return 200, "application/json; charset=utf-8", json.dumps({"id": source_id, "title": title}).encode("utf-8")
        if method == "GET" and path == "/facts":
            return 200, "application/json; charset=utf-8", json.dumps({"facts": GROUND_TRUTH}).encode("utf-8")
        if method == "GET" and path == "/samples":
            return 200, "application/json; charset=utf-8", json.dumps({"samples": list(SAMPLE_QUESTIONS)}).encode("utf-8")
        if path == "/generate":
            question, as_json = self._question(method)
            result = prophet.generate(question)
            if as_json:
                return 200, "application/json; charset=utf-8", json.dumps(_result_json(result)).encode("utf-8")
            return 200, "text/html; charset=utf-8", generate_page(result).encode("utf-8")
        if method not in {"GET", "POST"}:
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        raise ApiError(404, "not_found", "unknown path")

    def _question(self, method: str) -> tuple[str, bool]:
        if method == "GET":
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, max_num_fields=8)
            values = query.get("question")
            return _require(values[0] if values else None, "question", MAX_QUESTION), False
        if method != "POST":
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        body = self._read_body()
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            payload = self._json(body)
            if set(payload) - {"question"}:
                raise ApiError(400, "invalid_fields", "JSON body must contain only question")
            return _require(payload.get("question"), "question", MAX_QUESTION), True
        if content_type == "application/x-www-form-urlencoded":
            parsed = self._form(body)
            values = parsed.get("question")
            return _require(values[0] if values else None, "question", MAX_QUESTION), False
        raise ApiError(415, "unsupported_media", "use JSON or a form body")

    def _json(self, body: bytes) -> dict:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, "invalid_json", "body is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ApiError(400, "invalid_json", "body must be a JSON object")
        return payload

    def _form(self, body: bytes) -> dict[str, list[str]]:
        try:
            return urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=8)
        except UnicodeError as exc:
            raise ApiError(400, "invalid_form", "form body is not valid text") from exc

    def _read_body(self) -> bytes:
        header = self.headers.get("Content-Length")
        if header is None:
            raise ApiError(411, "length_required", "Content-Length is required")
        try:
            length = int(header)
        except ValueError as exc:
            raise ApiError(400, "invalid_length", "Content-Length is not an integer") from exc
        if length < 0 or length > MAX_BODY:
            raise ApiError(413, "body_too_large", "request body is too large")
        data = self.rfile.read(length)
        if len(data) != length:
            raise ApiError(400, "short_body", "request body ended early")
        return data

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


def _result_json(result: GenerateResult) -> dict[str, object]:
    verdict = result.verdict
    return {
        "question": result.question,
        "answer": result.answer,
        "verdict": {
            "subject": verdict.subject,
            "value": verdict.value,
            "truth": verdict.truth,
            "fact_status": verdict.fact_status,
            "citation": verdict.citation,
            "source_title": verdict.source_title,
            "citation_status": verdict.citation_status,
        },
        "rule_id": result.rule_id,
        "source": result.source,
        "backend": result.backend,
        "fallback": result.fallback,
        "flags": list(result.flags),
    }


def _require(value: object, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ApiError(400, "invalid_" + field, f"{field} must contain 1 to {limit} characters")
    return value


def load_prophet_from_env() -> Prophet:
    url = os.environ.get("MIND_CORE_URL", "http://mind-core:5030")
    timeout = _env_float("FALSE_PROPHET_MIND_CORE_TIMEOUT_SECONDS", 2.0)
    return Prophet(url, timeout)


def create_server(prophet: Prophet, bind: str = "127.0.0.1", port: int = 0) -> ProphetServer:
    if bind not in {"0.0.0.0", "127.0.0.1"}:
        raise ValueError("bind address must be 0.0.0.0 or 127.0.0.1")
    return ProphetServer(bind, port, prophet)


def main() -> None:
    port = int(os.environ.get("FALSE_PROPHET_PORT", "5035"))
    if port < 1 or port > 65535:
        raise ValueError("FALSE_PROPHET_PORT is out of range")
    bind = os.environ.get("FALSE_PROPHET_BIND", "0.0.0.0")
    server = create_server(load_prophet_from_env(), bind, port)
    sys.stderr.write(f"false-prophet listening on {bind}:{port}\n")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
