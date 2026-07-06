"""Generate output files from classified KnowledgeItems."""

from .checklist import extract_checklist_tasks, render_setup_checklist_markdown
from .knowledge import render_knowledge_json, render_knowledge_markdown
from .onboarding import render_onboarding_markdown
from .packager import ProjectOutput, write_project_outputs, write_templates_zip
from .references import render_references_markdown
from .warnings import build_requests_url_checker, detect_warnings, render_warnings_markdown

__all__ = [
    "ProjectOutput",
    "build_requests_url_checker",
    "detect_warnings",
    "extract_checklist_tasks",
    "render_knowledge_json",
    "render_knowledge_markdown",
    "render_onboarding_markdown",
    "render_references_markdown",
    "render_setup_checklist_markdown",
    "render_warnings_markdown",
    "write_project_outputs",
    "write_templates_zip",
]
