"""Stateless model calls for skill generation and item judgments."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request


def add_model_arguments(parser):
    parser.add_argument("--backend", choices=("codex", "claude", "api"), required=True)
    parser.add_argument("--model", required=True)


def complete(prompt, backend, model):
    if backend == "api":
        base = os.environ["OPENAI_BASE_URL"].rstrip("/")
        request = urllib.request.Request(
            base + "/chat/completions",
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            }).encode(),
            headers={
                "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=600) as response:
            choice = json.load(response)["choices"][0]
        if choice.get("finish_reason") == "length":
            raise ValueError("The model response was truncated.")
        text = choice["message"]["content"]
    else:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "response.md"
            if backend == "codex":
                command = [
                    "codex", "exec", "--sandbox", "read-only",
                    "--skip-git-repo-check", "--ephemeral",
                    "-c", 'model_reasoning_effort="high"',
                    "--model", model, "--output-last-message", str(output), "-",
                ]
            else:
                command = [
                    "claude", "-p", "--model", model,
                    "--tools", "", "--system-prompt", "", "--setting-sources", "",
                    "--strict-mcp-config", "--no-session-persistence", "--output-format", "json",
                ]
            result = subprocess.run(
                command, input=prompt, text=True, capture_output=True,
                cwd=directory, timeout=600, check=True,
            )
            if backend == "codex":
                text = output.read_text(encoding="utf-8")
            else:
                response = json.loads(result.stdout)
                if response.get("is_error"):
                    raise ValueError("Claude Code returned an error.")
                text = response["result"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The model returned an empty response.")
    return text.strip()


def read_json_response(text):
    if text.startswith("```") and text.endswith("```"):
        text = text.split("\n", 1)[1].rsplit("\n", 1)[0]
    return json.loads(text)
