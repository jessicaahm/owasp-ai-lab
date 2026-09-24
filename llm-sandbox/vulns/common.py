"""Shared helpers used by the fixed lessons."""
import logging
import pathlib
import re

SCRATCH = (pathlib.Path(__file__).resolve().parent.parent / "scratch").resolve()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def confine_to_scratch(user_path: str) -> pathlib.Path:
    """Resolve a user-supplied path and ensure it stays inside scratch/.

    Uses the resolved (symlink-free) path so `..` and symlinks cannot escape.
    """
    candidate = (SCRATCH / user_path).resolve()
    if candidate != SCRATCH and SCRATCH not in candidate.parents:
        raise PermissionError(f"path escapes sandbox: {user_path}")
    return candidate


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str, max_len: int) -> str:
    """Strip control characters and cap length. Defence-in-depth, not a cure."""
    text = _CONTROL.sub("", text)
    return text[:max_len]
