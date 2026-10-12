from pathlib import Path
import importlib.util


def test_dotenv_is_declared_in_requirements():
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    text = requirements.read_text(encoding="utf-8")
    assert "python-dotenv" in text


def test_dotenv_module_is_available():
    assert importlib.util.find_spec("dotenv") is not None
