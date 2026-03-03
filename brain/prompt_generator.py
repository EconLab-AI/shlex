# brain/prompt_generator.py
from __future__ import annotations

from jinja2 import Template

from brain.context_engine import ProjectContext

_BASE_TEMPLATE = """# Aufgabe
{{ user_input }}
{% if complexity == "complex" %}

# Denktiefe
Nutze Ultrathink fuer diese komplexe Aufgabe. Denke gruendlich nach bevor du handelst.
{% endif %}
{% if complexity in ["complex", "medium"] %}

# Team-Modus
- Arbeite im tmux Team-Modus
- Nutze TeamCreate fuer parallele Agents wo sinnvoll
- Modell-Strategie: Haiku=Research, Sonnet=Code, Opus=Architektur
- Maximiere Parallelitaet wo moeglich
{% endif %}

{{ context_section }}
{% if error_memories %}

# Fehler-History (NICHT WIEDERHOLEN!)
{% for err in error_memories %}
- {{ err }}
{% endfor %}
{% endif %}

{{ task_type_section }}

# Qualitaets-Gates (PFLICHT)
- Nach Design-Phase: Checkpoint erstellen
- Nach Core-Implementation: Tests laufen lassen
- Bei Fehler: Root-Cause-Analyse, NICHT quick-fix
- Vor Commit: Tests gruen

# Selbst-Reflexion (AM ENDE DER SESSION)
Beantworte und in Memory speichern:
1. Was wurde erreicht? (konkrete Deliverables)
2. Was lief nicht wie geplant?
3. Welche Fehler wurden gemacht?
4. Was muss die naechste Session wissen?
5. Offene Fragen/Blocker?
"""

_TASK_TYPE_SECTIONS = {
    "feature": """# Ausfuehrung
- Nutze den Brainstorming-Skill fuer Design-Phase
- Dann Writing-Plans fuer Implementation
- TDD: Tests zuerst, dann Implementation
- Frequent Commits nach jedem logischen Schritt""",
    "bugfix": """# Ausfuehrung — Root-Cause-Analyse
- Root-Cause-Analyse ZUERST — kein Quick-Fix
- Reproduziere den Bug mit einem Test
- Fix implementieren
- Verify: Test muss gruen werden
- Regression-Test hinzufuegen""",
    "refactor": """# Ausfuehrung — Refactoring
- Tests muessen vorher gruen sein
- Refactoring in kleinen Schritten
- Nach jedem Schritt: Tests laufen lassen
- Keine Verhaltensaenderung — nur Struktur""",
    "research": """# Ausfuehrung — Recherche
- Ergebnisse strukturiert zusammenfassen
- Quellen und Referenzen angeben
- Pro/Contra bei Alternativen
- Empfehlung mit Begruendung""",
}


class PromptGenerator:
    def __init__(self) -> None:
        self._template = Template(_BASE_TEMPLATE)

    def generate(
        self,
        task_type: str,
        user_input: str,
        context: ProjectContext,
        complexity: str = "simple",
    ) -> str:
        task_type_section = _TASK_TYPE_SECTIONS.get(task_type, _TASK_TYPE_SECTIONS["feature"])
        return self._template.render(
            user_input=user_input,
            complexity=complexity,
            context_section=context.to_prompt_section(),
            error_memories=context.error_memories,
            task_type_section=task_type_section,
        )
