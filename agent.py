import requests
import json
from typing import Any, Iterable, List, Protocol


class Tool(Protocol):
    """Lightweight protocol describing a callable tool."""

    name: str
    description: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        ...


class Agent:
    """An agent that can interact with a model and use tools."""

    def __init__(self,
        tools: List[Tool] | None = None,
        messages: List[dict[str, Any]] | None = None,
        system_prompt: str = "",
        model: str = "mistral",
    ) -> None:
        self.model: str = model
        self.system_prompt: str = system_prompt
        self.tools: List[Tool] = list(tools or [])
        self.messages: List[dict[str, Any]] = list(messages or [])
        if self.system_prompt:
                self.messages.append({"role": "system", "content": self.system_prompt})

    def stream(self, prompt: str) -> Iterable[str]:
        """Stream the model's response to the given prompt while keeping chat history."""
        url = "http://localhost:11434/api/chat"

        self.messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": self.messages,
            "stream": True
        }

        assistant_reply = ""

        with requests.post(url, json=data, stream=True) as response:
            if response.status_code != 200:
                print("Error:", response.text)
                return
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        assistant_reply += content
                        yield content

        self.messages.append({"role": "assistant", "content": assistant_reply})


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
