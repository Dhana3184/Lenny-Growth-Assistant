import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PI_SCRIPT = PROJECT_ROOT / "pi_answer.mjs"


def generate_with_pi(system_prompt: str, user_prompt: str, provider: str | None = None) -> str:
    payload = json.dumps({
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "provider": provider,
    })

    result = subprocess.run(
        ["node", str(PI_SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=260,
        env=os.environ.copy(),
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Pi agent failed: " + (result.stderr[-1500:] or result.stdout[-1500:])
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Pi agent returned invalid JSON.") from exc

    answer = data.get("answer", "").strip()
    if not answer:
        raise RuntimeError("Pi agent returned an empty answer.")

    return answer
