import os
import subprocess
import sys


def test_invalid_config_stops_startup_with_readable_message():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VERTEX_", "GOOGLE_", "GEMINI_"))}
    env["LLM_PROVIDER"] = "vertex"
    out = subprocess.run([sys.executable, "-c", "import app.main"], env=env, capture_output=True, text=True)
    assert out.returncode != 0
    assert "VERTEX_LLM_MODEL is required when LLM_PROVIDER=vertex" in out.stderr
    assert "Traceback" not in out.stderr
