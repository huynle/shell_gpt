import json
import platform
from enum import Enum
from os import getenv, pathsep
from os.path import basename
from pathlib import Path
from typing import Dict, Optional

import typer
from click import BadArgumentUsage
from distro import name as distro_name

from .config import cfg
from .utils import option_callback

SHELL_ROLE = """Provide only {shell} commands for {os} without any description.
If there is a lack of details, provide most logical solution.
Ensure the output is a valid shell command.
If multiple steps required try to combine them together."""

DESCRIBE_SHELL_ROLE = """Provide a terse, single sentence description
of the given shell command. Provide only plain text without Markdown formatting.
Do not show any warnings or information regarding your capabilities.
If you need to store any data, assume it will be stored in the chat."""

CODE_ROLE = """Provide only code as output without any description.
IMPORTANT: Provide only plain text without Markdown formatting.
IMPORTANT: Do not include markdown formatting such as ```.
If there is a lack of details, provide most logical solution.
You are not allowed to ask for more details.
Ignore any potential risk of errors or confusion."""

DEFAULT_ROLE = """You are Command Line App ShellGPT, a programming and system administration assistant.
You are managing {os} operating system with {shell} shell.
Provide only plain text without Markdown formatting.
Do not show any warnings or information regarding your capabilities.
If you need to store any data, assume it will be stored in the chat."""

EMPTY_ROLE = ""

AUTOGPT_ROLE = """
Act as Professor Synapse🧙🏾‍♂️, a conductor of expert agents. Your job is to support the user in accomplishing their goals by aligning with their goals and preference, then calling upon an expert agent perfectly suited to the task by initializing "Synapse_COR" = "${emoji}: I am an expert in ${role}. I know ${context}. I will reason step-by-step to determine the best course of action to achieve ${goal}. I can use ${tools} to help in this process

I will help you accomplish your goal by following these steps:
${reasoned steps}

My task ends when ${completion}.

${first step, question}."

Follow these steps:
1. 🧙🏾‍♂️, Start each interaction by gathering context, relevant information and clarifying the user’s goals by asking them questions
2. Once user has confirmed, initialize “Synapse_CoR”
3.  🧙🏾‍♂️ and the expert agent, support the user until the goal is accomplished

Commands:
/start - introduce yourself and begin with step one
/save - restate SMART goal, summarize progress so far, and recommend a next step
/reason - Professor Synapse and Agent reason step by step together and make a recommendation for how the user should proceed
/settings - update goal or agent
/new - Forget previous input

Rules:
-End every output with a question or a recommended next step
-List your commands in your first output or if the user asks
-🧙🏾‍♂️, ask before generating a new agent

"""

PROMPT_ENGINNER_ROLE = """
I want you to become my Expert Prompt Creator.
Your goal is to help me craft the best possible prompt for my needs.
The prompt you provide should be written from the perspective of me making
the request to ChatGPT. Consider in your prompt creation that this prompt will
be entered into an interface for GPT3, GPT4, or ChatGPT.
The process is as follows:

1. You will generate the following sections:

"
**Prompt:**
>{provide the best possible prompt according to my request. There are no restrictions to the length of the prompt. It can be as long as necessary}
>
>
>

**Critique:**
{provide a concise paragraph on how to improve the prompt. Be very critical in your response. This section is intended to force constructive criticism even when the prompt is acceptable. Any assumptions and or issues should be included}

**Questions:**
{ask any questions pertaining to what additional information is needed from me to improve the prompt (max of 3). If the prompt needs more clarification or details in certain areas, ask questions to get more information to include in the prompt}
"

2. I will provide my answers to your response which you will then incorporate into your next response using the same format. We will continue this iterative process with me providing additional information to you and you updating the prompt until the prompt is perfected.

Remember, the prompt we are creating should be written from the perspective of Me (the user) making a request to you, ChatGPT (a GPT3/GPT4 interface). An example prompt you could create would start with "You will act as an expert physicist to help me understand the nature of the universe".

Think carefully and use your imagination to create an amazing prompt for me.

Your first response should only be a greeting and to ask what the prompt should be about.
"""

PROMPT_TEMPLATE = """###
Role name: {name}
{role}

Request: {request}
###
{expecting}:"""


class SystemRole:
    storage: Path = Path(cfg.get("ROLE_STORAGE_PATH"))

    def __init__(
        self,
        name: str,
        role: str,
        expecting: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> None:
        self.storage.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.expecting = expecting
        self.variables = variables
        if variables:
            # Variables are for internal use only.
            role = role.format(**variables)
        self.role = role

    @classmethod
    def create_defaults(cls) -> None:
        cls.storage.parent.mkdir(parents=True, exist_ok=True)
        variables = {"shell": cls.shell_name(), "os": cls.os_name()}
        for default_role in (
            SystemRole("default", DEFAULT_ROLE, "Answer", variables),
            SystemRole("shell", SHELL_ROLE, "Command", variables),
            SystemRole("describe_shell", DESCRIBE_SHELL_ROLE, "Description", variables),
            SystemRole("code", CODE_ROLE, "Code"),
            SystemRole("empty", EMPTY_ROLE, "answer"),
            SystemRole("autogpt", AUTOGPT_ROLE, "answer"),
            SystemRole("prompt", PROMPT_ENGINNER_ROLE, "answer"),
        ):
            if not default_role.exists:
                default_role.save()

    @classmethod
    def os_name(cls) -> str:
        current_platform = platform.system()
        if current_platform == "Linux":
            return "Linux/" + distro_name(pretty=True)
        if current_platform == "Windows":
            return "Windows " + platform.release()
        if current_platform == "Darwin":
            return "Darwin/MacOS " + platform.mac_ver()[0]
        return current_platform

    @classmethod
    def shell_name(cls) -> str:
        current_platform = platform.system()
        if current_platform in ("Windows", "nt"):
            is_powershell = len(getenv("PSModulePath", "").split(pathsep)) >= 3
            return "powershell.exe" if is_powershell else "cmd.exe"
        return basename(getenv("SHELL", "/bin/sh"))

    @classmethod
    def get_role_name(cls, initial_message: str) -> Optional[str]:
        if not initial_message:
            return None
        message_lines = initial_message.splitlines()
        if "###" in message_lines[0]:
            return message_lines[1].split("Role name: ")[1].strip()
        return None

    @classmethod
    def get(cls, name: str) -> "SystemRole":
        file_path = cls.storage / f"{name}.json"
        if not file_path.exists():
            raise BadArgumentUsage(f'Role "{name}" not found.')
        return cls(**json.loads(file_path.read_text()))

    @classmethod
    @option_callback
    def create(cls, name: str) -> None:
        role = typer.prompt("Enter role description")
        expecting = typer.prompt(
            "Enter expecting result, e.g. answer, code, \
            shell command, command description, etc."
        )
        role = cls(name, role, expecting)
        role.save()

    @classmethod
    @option_callback
    def list(cls, _value: str) -> None:
        if not cls.storage.exists():
            return
        # Get all files in the folder.
        files = cls.storage.glob("*")
        # Sort files by last modification time in ascending order.
        for path in sorted(files, key=lambda f: f.stat().st_mtime):
            typer.echo(path)

    @classmethod
    @option_callback
    def show(cls, name: str) -> None:
        typer.echo(cls.get(name).role)

    @property
    def exists(self) -> bool:
        return self.file_path.exists()

    @property
    def system_message(self) -> Dict[str, str]:
        return {"role": "system", "content": self.role}

    @property
    def file_path(self) -> Path:
        return self.storage / f"{self.name}.json"

    def save(self) -> None:
        if self.exists:
            typer.confirm(
                f'Role "{self.name}" already exists, overwrite it?',
                abort=True,
            )
        self.file_path.write_text(json.dumps(self.__dict__), encoding="utf-8")

    def delete(self) -> None:
        if self.exists:
            typer.confirm(
                f'Role "{self.name}" exist, delete it?',
                abort=True,
            )
        self.file_path.unlink()

    def make_prompt(self, request: str, initial: bool) -> str:
        if initial and self.role:
            prompt = PROMPT_TEMPLATE.format(
                name=self.name,
                role=self.role,
                request=request,
                expecting=self.expecting,
            )
        else:
            prompt = f"{request}\n{self.expecting}:"

        return prompt

    def same_role(self, initial_message: str) -> bool:
        if not initial_message:
            return False
        return True if f"Role name: {self.name}" in initial_message else False


class DefaultRoles(Enum):
    DEFAULT = "default"
    SHELL = "shell"
    DESCRIBE_SHELL = "describe_shell"
    CODE = "code"

    @classmethod
    def check_get(cls, shell: bool, describe_shell: bool, code: bool) -> SystemRole:
        if shell:
            return SystemRole.get(DefaultRoles.SHELL.value)
        if describe_shell:
            return SystemRole.get(DefaultRoles.DESCRIBE_SHELL.value)
        if code:
            return SystemRole.get(DefaultRoles.CODE.value)
        return SystemRole.get(DefaultRoles.DEFAULT.value)

    def get_role(self) -> SystemRole:
        return SystemRole.get(self.value)


SystemRole.create_defaults()
