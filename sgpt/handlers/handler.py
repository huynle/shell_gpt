from typing import Any, Dict, Generator, List

import typer

from ..clients.openai import OpenAIClient
from ..clients.ollama import OllamaClient
from ..config import cfg
from ..role import SystemRole


class Handler:
    def __init__(self, role: SystemRole) -> None:
        self.client = OllamaClient(
            cfg.get("OPENAI_API_HOST"), cfg.get("OPENAI_API_KEY")
        )
        self.role = role
        self.color = cfg.get("DEFAULT_COLOR")

    def make_prompt(self, prompt: str) -> str:
        raise NotImplementedError

    def make_messages(self, prompt: str) -> List[Dict[str, str]]:
        raise NotImplementedError

    def get_completion(self, **kwargs: Any) -> Generator[str, None, None]:
        yield from self.client.get_completion(**kwargs)

    def handle(self, prompt: str, **kwargs: Any) -> str:
        messages = self.make_messages(self.make_prompt(prompt))
        full_completion = ""
        stream = cfg.get("DISABLE_STREAMING") == "false"
        if not stream:
            typer.echo("Loading...\r", nl=False)
        if self.color != "none":
            for word in self.get_completion(messages=messages, **kwargs):
                typer.secho(word, fg=self.color, bold=True, nl=False)
            full_completion += word
            typer.echo("\033[K" if not stream else "")  # Overwrite "loading..."
        else:
            for word in self.get_completion(messages=messages, **kwargs):
                typer.echo(word, nl=False)  # Overwrite "loading..."
                full_completion += word
        return full_completion
