# Coding Automation Loop — Design Document

**Datum:** 2026-03-03
**Status:** Approved
**Ansatz:** Event-Driven Pipeline (Python + asyncio)

---

## Problem

Repetitive manuelle Bedienung von Claude Code am Terminal: Sessions starten, Prompts schreiben, Output uberwachen, Entscheidungen treffen, Multi-Agent koordinieren. Das soll ein autonomer Orchestrator ubernehmen.

## Losung

Ein Meta-Orchestrator ("Coding Automation Loop"), der die Rolle des menschlichen Operators am Terminal vollstandig automatisiert. Uberwiegend autonom, mit Human-in-the-Loop bei kritischen Entscheidungen via Telegram.

## Rahmenbedingungen

- **Max-Subscription**: Kein API-Zugang, nur Claude Code CLI
- **Terminal-Steuerung**: Python + libtmux
- **Autonomie**: Uberwiegend autonom, Telegram bei kritischen Entscheidungen
- **Input**: Telegram (Text, Dateien, Sprachnachrichten)
- **Monitoring**: tmux lokal + Telegram remote + Web Dashboard live

---

## Architektur: 4-Layer Event-Driven Pipeline

```
+--------------------------------------------------------------+
|                    CODING AUTOMATION LOOP                      |
|                                                                |
|  +-------------+    +--------------+    +-----------------+   |
|  |  INPUT       |    |  BRAIN       |    |  EXECUTION      |   |
|  |  LAYER       |--->|  LAYER       |--->|  LAYER          |   |
|  |              |    |              |    |                 |   |
|  | - Telegram   |    | - Context    |    | - Session Mgr   |   |
|  | - Voice/STT  |    |   Engine     |    | - tmux Control  |   |
|  | - File Parse |    | - Prompt     |    | - Output Parser |   |
|  | - CLI        |    |   Generator  |    | - Decision Eng. |   |
|  +-------------+    | - Task       |    | - Multi-Agent   |   |
|                      |   Planner    |    |   Orchestrator  |   |
|                      +--------------+    +-----------------+   |
|                                                                |
|  +---------------------------------------------------------+  |
|  |  MONITORING LAYER                                        |  |
|  |  - Web Dashboard (FastAPI + WebSocket)                   |  |
|  |  - Telegram Status Reporter                              |  |
|  |  - Event Logger                                          |  |
|  +---------------------------------------------------------+  |
|                                                                |
|  +---------------------------------------------------------+  |
|  |  EVENT BUS (asyncio Queues)                              |  |
|  |  Events: task.new, session.start, output.received,       |  |
|  |  decision.needed, task.complete                           |  |
|  +---------------------------------------------------------+  |
+--------------------------------------------------------------+
```

### Layer-Beschreibung

**1. Input Layer** — Empfangt und normalisiert Eingaben
- Telegram Bot (python-telegram-bot): Text, Dateien, Voice
- Voice: OpenAI Whisper (lokal via whisper.cpp oder API)
- File-Parser: PDF, Bilder, Code-Dateien -> Text
- Optional: CLI-Befehl fur lokalen Start

**2. Brain Layer** — Denkt und plant
- Context Engine: CLAUDE.md, Git-Status, Session-History, tmux Sessions, Memory-Files
- Prompt Generator: Rohinput + Kontext -> Ultra-Prompt
- Task Planner: Zerlegt komplexe Aufgaben, wahlt Strategie (seriell/parallel/hierarchisch)

**3. Execution Layer** — Fuhrt aus
- Session Manager: Erstellt/verwaltet Claude Code Sessions in tmux
- tmux Controller (libtmux): send-keys, capture-pane, Output lesen
- Output Parser: Pattern Matching (Fragen, Fehler, Fertig, Permissions)
- Decision Engine: Autonom oder Eskalation
- Multi-Agent Orchestrator: Parallele Sessions, Synchronisation

**4. Monitoring Layer** — Beobachtet und berichtet
- Web Dashboard: FastAPI + WebSocket (HTMX + Tailwind)
- Telegram Reporter: Status-Updates, Alerts
- Event Logger: Persistent in SQLite

---

## Ultra-Prompt Generator

### Prompt-Struktur

```
# Aufgabe
{aufbereitete_user_anfrage}

# Denktiefe
{ultrathink_directive}

# Team-Modus (PFLICHT bei komplexen Tasks)
- Arbeite im tmux Team-Modus
- Nutze TeamCreate fur parallele Agents
- Modell-Strategie: Haiku=Research, Sonnet=Code, Opus=Architektur

# Projektkontext
- Tech-Stack, Architektur, Relevante Dateien, Letzte Anderungen

# Fehler-History (NICHT WIEDERHOLEN!)
{bekannte_fehler_aus_db}

# Multi-Session Strategie
Session-Plan mit Phasen und Kontext-Ubergabe

# Qualitats-Gates (PFLICHT)
- Checkpoints nach Design, Implementation, Tests
- git diff prufen bei grossen Anderungen
- Root-Cause-Analyse statt Quick-Fix bei Fehlern

# Konventionen
{claude_md_regeln} + {projekt_patterns}

# Selbst-Reflexion (AM ENDE JEDER SESSION)
1. Was wurde erreicht?
2. Was lief nicht wie geplant?
3. Welche Fehler? -> Error Memory updaten
4. Was muss nachste Session wissen?
5. Offene Fragen/Blocker?
```

### Prompt-Templates (Jinja2)
- `feature.j2` — Neue Features (Brainstorming -> Plans -> Impl)
- `bugfix.j2` — Bugfixes (Root-Cause-Analyse)
- `refactor.j2` — Refactoring (Test-First)
- `research.j2` — Recherche
- `review.j2` — Code Reviews

### Kontext-Quellen
| Quelle | Was | Wann |
|---|---|---|
| CLAUDE.md | Projekt-Regeln | Immer |
| git log/status/diff | Code-Zustand | Immer |
| Memory-Files | Session-Learnings | Immer |
| tmux list-sessions | Laufende Sessions | Immer |
| Projekt-Struktur | Datei-Ubersicht | Immer |
| Error Memory DB | Bekannte Fehler | Immer |
| Session-History | Was wurde schon gemacht | Bei Bedarf |

---

## Multi-Agent Orchestrierung

### Adaptive Strategie

| Komplexitat | Strategie | Beschreibung |
|---|---|---|
| EINFACH (1 Aspekt) | SERIELL | 1 Session, direkte Ausfuhrung |
| MITTEL (2-3 Aspekte) | PARALLEL | 2-3 Sessions parallel, Merge am Ende |
| KOMPLEX (4+ Aspekte) | HIERARCHISCH | Lead plant + Workers fuhren aus |

### Session Lifecycle
1. CREATE — tmux new-window / split-pane
2. INIT — claude --dangerously-skip-permissions starten
3. PROMPT — Ultra-Prompt via send-keys
4. MONITOR — capture-pane Output lesen
5. RESPOND — Follow-up Prompts bei Bedarf
6. COMPLETE — Output parsen, Ergebnis extrahieren
7. REFLECT — Reflexions-Prompt, Memory updaten
8. CLEANUP — Session beenden, Pane schliessen

### Synchronisation
- Shared State: SQLite fur Task-Status, Dateisperren
- Merge-Strategie: Git-Konflikte prufen nach parallelen Sessions
- Abhangigkeiten: Task-Graph mit Blocking-Dependencies

---

## Monitoring & Interaktion

### Web Dashboard
- FastAPI Backend + WebSocket fur Live-Updates
- HTMX + Tailwind Frontend
- Zeigt: Active Tasks, Live Sessions, Event Log, Metriken

### Telegram Bot

**Eingehend:**
| Input | Aktion |
|---|---|
| Text | Task erstellen |
| Sprachnachricht | Whisper -> Task |
| Datei | Parsen -> Kontext |
| /status | Ubersicht aktive Tasks |
| /sessions | Laufende tmux Sessions |
| /stop, /pause, /resume | Steuerung |
| /approve, /reject | Kritische Entscheidungen |

**Ausgehend:**
- Task gestartet/Fortschritt/Fehler/Fertig
- Kritische Entscheidungen mit Inline-Keyboards
- Session-Reflexionen

---

## Datenmodell (SQLite)

### Tabellen
- **tasks** — Haupteinheit (id, title, raw_input, ultra_prompt, strategy, status, parent_id)
- **sessions** — Claude Code tmux Sessions (task_id, tmux_pane, status, prompt, output_log)
- **events** — System-Events (event_type, payload, timestamp)
- **error_memory** — Projektspezifische Fehler (project, error_desc, root_cause, prevention)
- **reflections** — Session-Reflexionen (achieved, issues, learnings, next_steps)
- **context_cache** — Vorberechneter Kontext (project, key, value)

---

## Projektstruktur

```
coding-automation-loop/
├── main.py                    # Entry point, Event Loop
├── config.yaml                # Konfiguration
├── core/
│   ├── event_bus.py           # asyncio Event Bus
│   ├── models.py              # Pydantic Models
│   └── database.py            # SQLite via aiosqlite
├── input/
│   ├── telegram_bot.py        # Telegram Bot
│   ├── voice_processor.py     # Whisper
│   ├── file_parser.py         # File Parser
│   └── cli.py                 # CLI
├── brain/
│   ├── context_engine.py      # Kontext-Loader
│   ├── prompt_generator.py    # Ultra-Prompt Builder
│   ├── task_planner.py        # Strategie-Entscheidung
│   └── templates/             # Jinja2 Prompt-Templates
├── execution/
│   ├── session_manager.py     # Session Lifecycle
│   ├── tmux_controller.py     # libtmux Wrapper
│   ├── output_parser.py       # Pattern Matching
│   ├── decision_engine.py     # Decision Logic
│   └── multi_agent.py         # Multi-Agent Orchestrierung
├── monitoring/
│   ├── dashboard.py           # FastAPI Dashboard
│   ├── telegram_reporter.py   # Telegram Notifications
│   ├── event_logger.py        # Event Logger
│   └── templates/index.html   # Dashboard UI
├── data/
│   └── loop.db                # SQLite DB
└── tests/
```

---

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python 3.12+ |
| Async | asyncio |
| Terminal | libtmux |
| Telegram | python-telegram-bot |
| Voice | whisper.cpp (lokal) |
| Web Dashboard | FastAPI + HTMX + Tailwind |
| WebSocket | FastAPI WebSocket |
| Datenbank | SQLite via aiosqlite |
| Templates | Jinja2 |
| Models | Pydantic v2 |
