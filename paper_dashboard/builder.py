import json
import logging
from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


def render_dashboard(template_path: Path, output_dir: Path, context: Dict) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_path.name)
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = template.render(
        papers_json=json.dumps(context["papers"], ensure_ascii=False),
        stats_json=json.dumps(context["stats"], ensure_ascii=False),
        resources_json=json.dumps(context.get("resources", []), ensure_ascii=False),
    )
    output_file = output_dir / "index.html"
    output_file.write_text(rendered, encoding="utf-8")
    logger.info("Wrote dashboard to %s", output_file)
    return output_file
