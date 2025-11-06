import os
import json
import requests
from typing import Iterable, Optional, List, Dict, Any

# Load .env early
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Lazy OpenAI import + client
_OpenAIClient = None
def _get_openai_client():
    global _OpenAIClient
    if _OpenAIClient is not None:
        return _OpenAIClient
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError(
            "The 'openai' package is required. Install with 'uv add openai' or 'pip install openai'."
        ) from e
    _OpenAIClient = OpenAI()  # uses OPENAI_API_KEY from env
    return _OpenAIClient


class Tool:
    """Base tool class. Subclasses should implement .call(**kwargs) -> str."""
    def __init__(self, name: str, schema: dict):
        # schema must be OpenAI-compatible function tool:
        # {"type":"function","function":{"name":"...", "description":"...", "parameters":{...}}}
        self.name = name
        self.schema = schema


class Agent:
    """An agent that can interact with a model and use tools (OpenAI Responses API or Ollama fallback)."""

    def __init__(
        self,
        tools: Optional[List[Tool]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        system_prompt: str = "",
        model: str = "llama3.1:8b",
        include_time: bool = False,
    ) -> None:
        self.model: str = model
        self.system_prompt: str = system_prompt
        self.tools: List[Tool] = list(tools or [])
        self.tools_schema: List[Dict[str, Any]] = [tool.schema for tool in self.tools] if self.tools else []
        self.messages: List[Dict[str, Any]] = list(messages or [])

        if include_time:
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.system_prompt += f" It is {now}"

        if self.system_prompt:
            self.messages.append({"role": "system", "content": self.system_prompt})

        # Prefer OPENAI_ env if present; otherwise leave your provided default model (ollama)
        env_model = os.getenv("OPENAI_MODEL", "").strip()
        if env_model:
            self.model = env_model

        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.provider = "openai" if self.openai_key and self.model else "ollama"

        print(f"Created agent with provider: {self.provider} | model: {self.model}\n")

    # ---------- Public API ----------

    def stream(self, prompt: str, max_tool_loops: int = 3) -> Iterable[str]:
        """Stream response, executing tools in a loop until final answer is reached."""
        self.messages.append({"role": "user", "content": prompt})
        if self.provider == "openai":
            yield from self._stream_openai(max_tool_loops=max_tool_loops)
        else:
            yield from self._stream_ollama(max_tool_loops=max_tool_loops)

    # ---------- Ollama path ----------

    def _stream_ollama(self, max_tool_loops: int) -> Iterable[str]:
        loop_count = 0
        while True:
            if loop_count >= max_tool_loops:
                print("\n[Max tool loop limit reached — stopping.]\n")
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

            with requests.post(url, json=data, stream=True) as response:
                if response.status_code != 200:
                    print(f"\nError: {response.text}\n")
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
                        print(f"\n[Tool call requested: {tool_calls}]\n")

                        for tool_call in tool_calls:
                            fn = tool_call["function"]["name"]
                            args = tool_call["function"].get("arguments", {}) or {}

                            for tool in self.tools:
                                if tool.name == fn:
                                    result = tool.call(**args)
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
                                    print(f"[Tool {fn} executed → {result}]\n")
                        break  # break streaming to start next loop turn

                    # Handle natural content
                    content = msg.get("content", "")
                    if content:
                        assistant_reply += content
                        yield content

            if not tool_used:
                if assistant_reply:
                    self.messages.append({"role": "assistant", "content": assistant_reply})
                break

    # ---------- OpenAI streaming (Responses API only) ----------

    def _stream_openai(self, max_tool_loops: int) -> Iterable[str]:
        """
        Tool loop with streaming:
        1) stream assistant text + function-call deltas
        2) if calls present, run tools, append tool results, and iterate
        3) otherwise finalize the turn and return
        """
        client = _get_openai_client()
        model = self.model
        loop_count = 0

        while True:
            if loop_count >= max_tool_loops:
                print("\n[Max tool loop limit reached — stopping.]\n")
                break

            assistant_text_parts: List[str] = []
            pending_calls: Dict[str, Dict[str, Any]] = {}  # call_id -> {"name": str, "args_json": str}

            # Stream with Responses API
            with client.responses.stream(
                model=model,
                input=self.messages,
                tools=self.tools_schema
            ) as stream:
                for event in stream:
                    etype = getattr(event, "type", None)

                    # Assistant text tokens
                    if etype == "response.output_text.delta":
                        delta = event.delta or ""
                        assistant_text_parts.append(delta)
                        yield delta

                    # Function call name and arguments arrive as deltas; reconstruct by call_id
                    elif etype == "response.function_call.name.delta":
                        cid = event.id
                        rec = pending_calls.setdefault(cid, {"name": "", "args_json": ""})
                        rec["name"] += (event.delta or "")

                    elif etype == "response.function_call.arguments.delta":
                        cid = event.id
                        rec = pending_calls.setdefault(cid, {"name": "", "args_json": ""})
                        rec["args_json"] += (event.delta or "")

                    # Optional: you can check for completion events here
                    elif etype in ("response.completed", "response.output_text.done"):
                        pass

                    elif etype == "response.error":
                        raise RuntimeError(getattr(event, "error", "Unknown OpenAI streaming error"))

                # Forces final object to be materialized (usage, etc.), and raises if there was an error
                _ = stream.get_final_response()

            # If the model asked to call tools, execute them and continue the loop
            if pending_calls:
                loop_count += 1
                print(f"\n[Tool call requested: {list(pending_calls.values())}]\n")

                # Record the assistant turn with the tool_calls for a faithful transcript
                self.messages.append({
                    "role": "assistant",
                    "content": "".join(assistant_text_parts),
                    "tool_calls": [
                        {
                            "id": cid,
                            "type": "function",
                            "function": {
                                "name": info.get("name", ""),
                                "arguments": self._raw_or_empty_json(info.get("args_json", "")),
                            },
                        }
                        for cid, info in pending_calls.items()
                    ],
                })

                # Execute each tool and append a tool message (with tool_call_id)
                for cid, info in pending_calls.items():
                    fn = (info.get("name") or "").strip()
                    args_obj = self._parse_json_object(info.get("args_json", ""))
                    for tool in self.tools:
                        if tool.name == fn:
                            result = tool.call(**(args_obj if isinstance(args_obj, dict) else {}))
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": cid,
                                "name": fn,
                                "content": result if isinstance(result, str) else json.dumps(result),
                            })
                            print(f"[Tool {fn} executed → {result}]\n")

                # Go back for another assistant turn (with tool results included)
                continue

            # No tools used — finalize assistant message and exit loop
            if assistant_text_parts:
                self.messages.append({"role": "assistant", "content": "".join(assistant_text_parts)})
            break

    # ---------- Utilities ----------

    @staticmethod
    def _raw_or_empty_json(s: str) -> str:
        """Ensure we store a raw JSON string for tool_calls; default to '{}' if blank/bad."""
        s = (s or "").strip()
        if not s:
            return "{}"
        # we don't validate here; keep raw to preserve exact payload
        return s

    @staticmethod
    def _parse_json_object(s: str) -> Any:
        """Parse function-call arguments JSON into a Python object safely."""
        try:
            return json.loads(s) if s else {}
        except Exception:
            return {}

# ---------- CLI ----------

if __name__ == "__main__":
    while True:
        prompt = input("Prompt: ").strip()
        if prompt == "exit":
            break
        if not prompt:
            raise SystemExit("A non-empty prompt is required.")

        agent = Agent(system_prompt="You are a helpful smart home assistant.")

        for chunk in agent.stream(prompt):
            print(chunk, end="", flush=True)
        print()

    print(agent.messages)
