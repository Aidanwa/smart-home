import requests
import json
from typing import Iterable


class Tool:
    """Base tool class."""
    def __init__(self, name: str, schema: dict):
        self.name = name
        self.schema = schema


class Agent:
    """An agent that can interact with a model and use tools."""

    def __init__(self,
        tools: list | None = None,
        messages: list[dict[str, str]] | None = None,
        system_prompt: str = "",
        model: str = "llama3.1:8b",
        include_time: bool = False,
    ) -> None:
        self.model: str = model
        self.system_prompt: str = system_prompt
        self.tools: list = list(tools or [])
        self.tools_schema: list[dict] = [tool.schema for tool in self.tools]
        self.messages: list[dict[str, str]] = list(messages or [])
        if include_time:
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.system_prompt += f" It is {now}"
        if self.system_prompt:
            self.messages.append({"role": "system", "content": self.system_prompt})

        print(f"Created agent with model: {self.model}\n")


    def stream(self, prompt: str, max_tool_loops: int = 3) -> Iterable[str]:
        """Stream response, executing tools in a loop until final answer is reached."""
        self.messages.append({"role": "user", "content": prompt})

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
                            args = tool_call["function"].get("arguments", {})

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
                        break 

                    # Handle natural content
                    content = msg.get("content", "")
                    if content:
                        assistant_reply += content
                        yield content

            if not tool_used:
                if assistant_reply:
                    self.messages.append({"role": "assistant", "content": assistant_reply})
                break


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
