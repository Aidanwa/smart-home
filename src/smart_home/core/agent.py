import os
import json
import requests
import uuid
import logging
from datetime import datetime
from typing import Iterable, Optional, List, Dict, Any
from dotenv import load_dotenv
from smart_home.config.paths import AGENT_LOGS_DIR

load_dotenv()

logger = logging.getLogger(__name__)

PROVIDER = os.getenv("PROVIDER").strip().lower()
OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("OPENAI_MODEL").strip() if PROVIDER == "openai" else os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip()

# ---------- Base Tool Class ----------
class Tool:
    """Base tool class. Subclasses should implement .call(**kwargs) -> str."""
    def __init__(self, name: str, description: str, params: dict):
        self.name = name
        self.description = description
        self.parameters = params
        self.schema = self.construct_schema()

    def construct_schema(self) -> dict:
        if PROVIDER == "openai":
            self.parameters['additionalProperties'] = False
            return {
                "type": "function",
                "name": self.name,
                "description": self.description or "",
                "parameters": self.parameters or {},
                "strict": True,
            }
        elif PROVIDER == "ollama":
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description or "",
                    "parameters": self.parameters or {},
                }
            }
        else:
            raise RuntimeError(f"Unknown provider '{PROVIDER}' for tool schema. Fix your .env PROVIDER value.")


# ---------- Base Agent Class ----------
class Agent:
    """An agent that can interact with a model and use tools (OpenAI Responses API or Ollama fallback)."""

    def __init__(
        self,
        tools: Optional[List[Tool]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        system_prompt: str = "",
        model: Optional[str] = None,
        include_time: bool = False,
        provider: Optional[str] = None,
        agent_type: str = "agent",
    ) -> None:
        self.model: str = model or DEFAULT_MODEL
        self.system_prompt: str = system_prompt
        self.tools: List[Tool] = list(tools or [])
        self.tools_schema: List[Dict[str, Any]] = [tool.schema for tool in self.tools] if self.tools else []
        self.messages: List[Dict[str, Any]] = list(messages or [])
        self.agent_id: str = str(uuid.uuid4())
        self.agent_type: str = agent_type

        if include_time:
            now = datetime.now().isoformat(timespec="minutes")
            self.system_prompt += f" It is {now}"

        if self.system_prompt:
            self.messages.append({"role": "system", "content": self.system_prompt})

        self.provider = provider or PROVIDER
        if self.provider == "openai":
            self.openai_key = OPENAI_API_KEY

        logger.info(
            f"Created agent with provider: {self.provider} | model: {self.model}",
            extra={"agent_id": self.agent_id, "provider": self.provider, "model": self.model}
        )

    # ---------- Public API ----------

    def stream(self, prompt: str, max_tool_loops: int = 3) -> Iterable[str]:
        """Stream response, executing tools in a loop until final answer is reached."""
        self.messages.append({"role": "user", "content": prompt})
        if self.provider == "openai":
            yield from self._stream_openai(max_tool_loops=max_tool_loops)
        else:
            yield from self._stream_ollama(max_tool_loops=max_tool_loops)

        # Save messages after streaming completes
        self._save_messages()

    def _save_messages(self) -> None:
        """Save conversation messages to logs/{agent_type}/{agent_id}_{timestamp}.json"""
        try:
            # Create agent-type-specific subdirectory
            logs_dir = AGENT_LOGS_DIR / self.agent_type
            logs_dir.mkdir(parents=True, exist_ok=True)

            # Create filename with agent_id and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            log_file = logs_dir / f"{self.agent_id}_{timestamp}.json"

            # Save messages with metadata
            log_data = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "provider": self.provider,
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "messages": self.messages
            }

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to save messages: {e}", exc_info=True, extra={"agent_id": self.agent_id})

    # ---------- Ollama path ----------

    def _stream_ollama(self, max_tool_loops: int) -> Iterable[str]:
        loop_count = 0
        while True:
            if loop_count >= max_tool_loops:
                logger.warning("Max tool loop limit reached", extra={"agent_id": self.agent_id, "max_loops": max_tool_loops})
                break

            url = "http://localhost:11434/api/chat"
            data = {
                "model": self.model,
                "messages": self.messages,
                "tools": self.tools_schema,
                "stream": True
            }

            assistant_reply = ""
            tool_used = False

            try:
                with requests.post(url, json=data, stream=True, timeout=30) as response:
                    if response.status_code != 200:
                        logger.error(
                            f"Ollama API error: {response.text}",
                            extra={"agent_id": self.agent_id, "status_code": response.status_code}
                        )
                        return

                    for line in response.iter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line.decode("utf-8"))
                        msg = chunk.get("message", {})

                        # Handle tool calls
                        tool_calls = msg.get("tool_calls", [])
                        if tool_calls:
                            tool_used = True
                            loop_count += 1
                            logger.debug(
                                f"Tool call requested",
                                extra={"agent_id": self.agent_id, "tool_calls": tool_calls}
                            )

                            for tool_call in tool_calls:
                                fn = tool_call["function"]["name"]
                                args = tool_call["function"].get("arguments", {}) or {}

                                for tool in self.tools:
                                    if tool.name == fn:
                                        try:
                                            result = tool.call(**args)
                                        except Exception as ex:
                                            result = f"Tool execution error: {ex}"
                                            logger.error(
                                                f"Tool {fn} failed: {ex}",
                                                exc_info=True,
                                                extra={"agent_id": self.agent_id, "tool_name": fn}
                                            )
                                        # Save assistant request + tool result
                                        self.messages.append({
                                            "role": "assistant",
                                            "content": "",
                                            "tool_calls": [tool_call]
                                        })
                                        self.messages.append({
                                            "role": "tool",
                                            "content": result
                                        })
                                        logger.info(
                                            f"Tool {fn} executed",
                                            extra={"agent_id": self.agent_id, "tool_name": fn, "result": result[:100]}
                                        )
                            break  # break streaming to start next loop turn

                        # Handle natural content
                        content = msg.get("content", "")
                        if content:
                            assistant_reply += content
                            yield content

            except requests.RequestException as ex:
                logger.error(f"Ollama API request failed: {ex}", exc_info=True, extra={"agent_id": self.agent_id})
                yield f"\n[Error: Could not connect to Ollama: {ex}]"
                return

            if not tool_used:
                if assistant_reply:
                    self.messages.append({"role": "assistant", "content": assistant_reply})
                break

    # ---------- OpenAI streaming (Responses API only) ----------

    def _stream_openai(self, max_tool_loops: int) -> Iterable[str]:
        model = self.model
        loop_count = 0

        while True:
            if loop_count >= max_tool_loops:
                logger.warning("Max tool loop limit reached", extra={"agent_id": self.agent_id, "max_loops": max_tool_loops})
                break

            assistant_text_parts: List[str] = []
            # item_id -> {"name": str, "call_id": str, "args": [str], "args_json": str, "ready": bool}
            pending_calls: Dict[str, Dict[str, Any]] = {}
            # also keep a list of completed function_call items to append to history verbatim
            emitted_function_calls: List[dict] = []

            body = {
                "model": model,
                "input": self.messages,            # persistent history (role'd messages + prior items)
                "tools": self.tools_schema or [],
                "tool_choice": "auto",
                "parallel_tool_calls": True,
                "stream": True,
            }

            url = f"{OPENAI_API_BASE}/responses"

            try:
                with requests.post(url, headers=self._openai_headers(), data=self._json(body), stream=True, timeout=30) as resp:
                    if resp.status_code != 200:
                        try:
                            err = resp.json()
                        except Exception:
                            err = {"error": resp.text}
                        logger.error(f"OpenAI API error: {err}", extra={"agent_id": self.agent_id})
                        raise RuntimeError(f"OpenAI Responses API error: {err}")

                    # ---- SSE event loop ----
                    for etype, data in self._sse_events(resp, debug=False):
                        # 1) Streamed assistant text tokens
                        if etype == "response.output_text.delta":
                            delta = data.get("delta") or ""
                            if delta:
                                assistant_text_parts.append(delta)
                                yield delta
                            continue

                        # 2) New function_call item — capture name & call_id
                        if etype == "response.output_item.added":
                            item = data.get("item") or {}
                            if item.get("type") == "function_call":
                                item_id = item.get("id")
                                if item_id:
                                    rec = pending_calls.setdefault(
                                        item_id, {"name": "", "call_id": None, "args": [], "ready": False}
                                    )
                                    if item.get("name"):
                                        rec["name"] = item["name"]
                                    if item.get("call_id"):
                                        rec["call_id"] = item["call_id"]
                            continue

                        # 3) JSON args fragments (accumulate)
                        if etype == "response.function_call_arguments.delta":
                            item_id = data.get("item_id")
                            frag = data.get("delta") or ""
                            if item_id and frag:
                                rec = pending_calls.setdefault(
                                    item_id, {"name": "", "call_id": None, "args": [], "ready": False}
                                )
                                rec["args"].append(frag)
                            continue

                        # 4) Args finished — mark ready and prepare a function_call item we can persist
                        if etype == "response.function_call_arguments.done":
                            item_id = data.get("item_id")
                            if item_id and item_id in pending_calls:
                                rec = pending_calls[item_id]
                                args_json = "".join(rec["args"]) if rec["args"] else "{}"
                                rec["args_json"] = args_json
                                rec["ready"] = True
                            continue

                        # 5) Item completed — second ready signal; build final function_call item
                        if etype == "response.output_item.done":
                            item = data.get("item") or {}
                            if item.get("type") == "function_call":
                                item_id = item.get("id")
                                if item_id and item_id in pending_calls:
                                    rec = pending_calls[item_id]
                                    # ensure args_json
                                    if not rec.get("args_json"):
                                        rec["args_json"] = "".join(rec["args"]) if rec["args"] else "{}"
                                    rec["ready"] = True
                                    # create a function_call item that mirrors what Responses would return in .output
                                    fn_name = rec.get("name") or item.get("name") or ""
                                    call_id = rec.get("call_id") or item.get("call_id")
                                    arguments = rec.get("args_json", "{}")
                                    emitted_function_calls.append({
                                        "id": item_id,
                                        "type": "function_call",
                                        "status": "completed",
                                        "name": fn_name,
                                        "call_id": call_id,
                                        "arguments": arguments,
                                    })
                            continue

                        # 6) Model-side error
                        if etype == "response.error":
                            err = data.get("error", "Unknown OpenAI streaming error")
                            raise RuntimeError(str(err))

                # ---- After streaming: persist streamed assistant text (if any)
                if assistant_text_parts:
                    self.messages.append({
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "".join(assistant_text_parts)}],
                    })
                    assistant_text_parts = []

                # ---- Persist the function_call items into history (docs-style)
                # (Now the tool calls live in input; no need for previous_response_id.)
                if emitted_function_calls:
                    self.messages += emitted_function_calls  # append list of dict items directly

                # ---- Execute tools and persist function_call_output items
                if any(rec.get("ready") for rec in pending_calls.values()):
                    loop_count += 1

                    for item_id, rec in pending_calls.items():
                        if not rec.get("ready"):
                            continue

                        fn_name = (rec.get("name") or "").strip()
                        call_id = rec.get("call_id")
                        if not fn_name or not call_id:
                            logger.warning(
                                f"Missing name/call_id for tool item, skipping",
                                extra={"agent_id": self.agent_id, "item_id": item_id}
                            )
                            continue

                        # Parse args JSON
                        args_obj = self._parse_json_object(rec.get("args_json", "")) or {}

                        # Execute your local tool
                        tool_found = False
                        result_payload = ""
                        for tool in self.tools:
                            if tool.name == fn_name:
                                tool_found = True
                                try:
                                    result = tool.call(**args_obj)
                                except Exception as ex:
                                    result = f"Tool execution error: {ex}"
                                    logger.error(
                                        f"Tool {fn_name} failed: {ex}",
                                        exc_info=True,
                                        extra={"agent_id": self.agent_id, "tool_name": fn_name}
                                    )
                                # function_call_output.output expects a string
                                result_payload = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                                break
                        if not tool_found:
                            result_payload = f"[Tool '{fn_name}' not found]"

                        # Persist function_call_output item into history (docs example style)
                        self.messages.append({
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": result_payload,
                        })

                    # Kick off a fresh assistant turn with expanded history (includes function_call + outputs)
                    # By design we do NOT set previous_response_id here, because history contains the calls.
                    continue

            except requests.RequestException as ex:
                logger.error(f"OpenAI API request failed: {ex}", exc_info=True, extra={"agent_id": self.agent_id})
                yield f"\n[Error: Could not connect to OpenAI API: {ex}]"
                return
            except RuntimeError as ex:
                logger.error(f"OpenAI API error: {ex}", exc_info=True, extra={"agent_id": self.agent_id})
                yield f"\n[Error: {ex}]"
                return

            # ---- No tool calls this turn: finish
            break

    # ---------- Utilities ----------

    @staticmethod
    def _parse_json_object(s: str) -> Any:
        """Parse function-call arguments JSON into a Python object safely."""
        try:
            return json.loads(s) if s else {}
        except Exception:
            return {}
        
    @staticmethod
    def _openai_headers() -> Dict[str, str]:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is missing.")
        return {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

    @staticmethod
    def _sse_events(response: requests.Response, *, debug: bool = False):
        """
        Robust SSE parser for OpenAI Responses API.
        Flushes on blank lines, handles multi-line JSON, ignores comments.
        """
        event = None
        data_lines = []

        def flush():
            nonlocal event, data_lines
            if not data_lines:
                return
            payload = "\n".join(data_lines)
            data_lines = []
            if payload.strip() == "[DONE]":
                raise StopIteration
            try:
                data = json.loads(payload)
            except Exception:
                data = {"raw": payload}
            yield (event, data)
            event = None

        for raw in response.iter_lines(chunk_size=8192, decode_unicode=True):
            if raw is None:
                continue
            if debug:
                logger.debug(f"SSE raw line: {raw}")

            line = raw.lstrip("\ufeff")
            if not line:
                yield from flush()
                continue

            if line.startswith(":"):
                continue  # comment/heartbeat
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip() or None
                continue
            if line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
                continue

            # Fallback (treat unknown fields as data continuation)
            data_lines.append(line.strip())

        yield from flush()


    @staticmethod
    def _json(obj) -> str:
        try:
            return json.dumps(obj)
        except Exception:
            return "{}"
        
