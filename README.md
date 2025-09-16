# smart-home
Agentic Smart Home

Ollama steps:
    install ollama
    ollama pull llama3.1:8b

    Using this model due to it's tool calling capability while still being light enough to run.

    When ollama was installed it automatically runs a background task on http://localhost:11434
    To test, run: curl http://localhost:11434/api/tags

tts:
    You'll have to download the vosk-model-small-en-us-0.15	from https://alphacephei.com/vosk/models
    and put it in a models folder on the top level directory.