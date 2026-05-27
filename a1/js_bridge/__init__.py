"""Bundled JS bridge (from streamlit-javascript) — no extra pip install needed."""

from __future__ import annotations

import os

import streamlit.components.v1 as components

_BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend_build")
_component = components.declare_component("streamlit_javascript", path=_BUILD_DIR)


def run_javascript(js_code: str, *, key: str) -> object:
    """Run JavaScript in the browser and return the result to Python."""
    full_key = f"a1_js_{key}"
    return _component(js_code=js_code, key=full_key, default=0)
