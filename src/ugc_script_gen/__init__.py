"""ugc-script-gen: shot-ready short-form UGC ad scripts from a product brief."""

from .brief import Brief, load_brief
from .generator import generate_hooks, generate_scripts
from .scoring import score_hook, score_script

__all__ = ["Brief", "load_brief", "generate_hooks", "generate_scripts", "score_hook", "score_script"]
__version__ = "0.1.0"
