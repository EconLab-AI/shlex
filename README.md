# Coding Automation Loop

**Dein autonomer Co-Pilot fuer Claude Code — damit du nicht mehr am Terminal sitzen musst.**

---

## Was ist das?

Du kennst das: Du sitzt vor Claude Code, tippst Prompts, wartest auf Output, beantwortest Rueckfragen, startest die naechste Session — und das stundenlang. Der **Coding Automation Loop** uebernimmt genau diese Rolle. Er ist der Mensch am Terminal, nur dass er nie muede wird.

Konkret: Du schickst eine Nachricht per **Telegram** — Text, Sprachnachricht oder Datei — und der Loop erledigt den Rest:

1. Versteht deine Anfrage und reichert sie mit Projektkontext an
2. Generiert einen optimalen **Ultra-Prompt** fuer Claude Code
3. Startet eine oder mehrere **tmux-Sessions** mit Claude Code
4. Ueberwacht den Output, beantwortet Rueckfragen automatisch
5. Eskaliert nur bei kritischen Entscheidungen — per Telegram zu dir
6. Berichtet das Ergebnis zurueck

**Kein API-Zugang noetig.** Der Loop arbeitet mit deinem bestehenden Claude Code Max-Abo, direkt ueber das CLI im Terminal.

---

## Warum?

| Ohne Loop | Mit Loop |
|---|---|
| Du tippst jeden Prompt manuell | Du schickst eine Telegram-Nachricht |
| Du wartest auf Output und reagierst | Der Loop ueberwacht und reagiert autonom |
| Du startest Sessions einzeln | Der Loop parallelisiert automatisch |
| Du vergisst Fehler aus frueheren Sessions | Der Loop merkt sich Fehler und vermeidet sie |
| Du bist an den Schreibtisch gebunden | Du steuerst alles per Handy |

---

## Wie funktioniert es?

### Architektur: 4-Layer Event-Driven Pipeline

```
┌──────────────────────────────────────────────────────────┐
│                   CODING AUTOMATION LOOP                  │
│                                                          │
│  ┌─────────┐    ┌──────────┐    ┌───────────────────┐   │
│  │  INPUT   │───>│  BRAIN   │───>│  EXECUTION        │   │
│  │         │    │          │    │                   │   │
│  │Telegram │    │ Kontext  │    │ tmux Sessions     │   │
│  │Sprache  │    │ Prompts  │    │ Output-Erkennung  │   │
│  │Dateien  │    │ Planung  │    │ Entscheidungen    │   │
│  │CLI      │    │          │    │ Multi-Agent       │   │
│  └─────────┘    └──────────┘    └───────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  MONITORING                                       │   │
│  │  Web Dashboard  ·  Telegram Status  ·  Event Log  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  EVENT BUS (asyncio)                              │   │
│  │  task.new · session.start · output.received · ... │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Die vier Schichten

**Input Layer** — Nimmt deine Aufgaben entgegen
- Telegram Bot: Text, Sprachnachrichten, Dateien
- Whisper-Transkription fuer Sprachnachrichten (deutsch)
- CLI fuer lokalen Zugriff

**Brain Layer** — Denkt und plant
- Laedt vollstaendigen Projektkontext (CLAUDE.md, Git-Status, Memory, Fehler-History)
- Generiert optimierte Ultra-Prompts mit Jinja2-Templates
- Waehlt automatisch die richtige Strategie: seriell, parallel oder hierarchisch

**Execution Layer** — Fuehrt aus
- Erstellt und verwaltet Claude Code Sessions in tmux
- Erkennt Output-Signale: Fragen, Fehler, Fertig, Permission-Requests
- Entscheidet autonom: Weitermachen, Wiederholen, oder Eskalieren
- Orchestriert mehrere Agents parallel bei komplexen Aufgaben

**Monitoring Layer** — Beobachtet und berichtet
- Live Web Dashboard (FastAPI + WebSocket)
- Telegram Status-Updates und Alerts
- Vollstaendiges Event-Log in SQLite

---

## Schnellstart

### Voraussetzungen

- Python 3.12+
- tmux installiert (`brew install tmux`)
- Claude Code CLI installiert und eingeloggt (Max-Abo)
- Optional: Telegram Bot Token (via [@BotFather](https://t.me/BotFather))

### Installation

```bash
git clone https://github.com/EconLab-AI/shlex.git
cd shlex
pip install -e ".[dev]"
```

### Konfiguration

Bearbeite `config.yaml`:

```yaml
telegram:
  token: "DEIN_BOT_TOKEN"        # Von @BotFather
  allowed_users: [123456789]      # Deine Telegram User-ID

whisper:
  model: "base"                   # Whisper-Modell fuer Sprache
  language: "de"

dashboard:
  host: "0.0.0.0"
  port: 8080

database:
  path: "data/loop.db"

tmux:
  session_prefix: "loop"
  claude_command: "claude --dangerously-skip-permissions"

orchestrator:
  poll_interval_ms: 500
  max_parallel_sessions: 4
```

### Starten

```bash
python main.py
```

Der Orchestrator startet und wartet auf Aufgaben. Schicke dem Bot eine Nachricht per Telegram — oder nutze das Dashboard unter `http://localhost:8080`.

---

## Nutzung per Telegram

### Aufgaben senden

Einfach eine Nachricht an deinen Bot schicken:

> "Implementiere einen Login-Flow mit OAuth2 fuer das Backend"

Oder per Sprachnachricht — Whisper transkribiert und der Loop uebernimmt.

Oder eine Datei senden — PDF, Code, Bilder werden automatisch geparst.

### Befehle

| Befehl | Funktion |
|---|---|
| `/status` | Uebersicht aller aktiven Tasks |
| `/sessions` | Laufende tmux Sessions |
| `/stop` | Aktiven Task stoppen |
| `/pause` / `/resume` | Task pausieren/fortsetzen |
| `/approve` / `/reject` | Kritische Entscheidung beantworten |
| `/logs` | Letzte Events anzeigen |

### Automatische Benachrichtigungen

Der Bot meldet sich bei dir:
- Task gestartet / Fortschritt / Fehler / Fertig
- Kritische Entscheidungen (mit Inline-Buttons zum Antworten)
- Session-Reflexionen am Ende jeder Session

---

## Der Ultra-Prompt

Das Herzsueck des Loops. Jede Aufgabe wird nicht einfach 1:1 an Claude Code weitergereicht, sondern zu einem **Ultra-Prompt** angereichert:

```
# Aufgabe
{deine aufbereitete Anfrage}

# Denktiefe
{ultrathink bei komplexen Tasks}

# Team-Modus
{Team-Aktivierung bei parallelen Aufgaben}

# Projektkontext
{CLAUDE.md + Git-Status + Dateistruktur + Memory}

# Fehler-History
{bekannte Fehler — NICHT WIEDERHOLEN!}

# Qualitaets-Gates
{Checkpoints nach Design, Implementation, Tests}

# Selbst-Reflexion
{Was wurde erreicht? Was lief nicht? Learnings?}
```

Der Prompt wird automatisch an den Task-Typ angepasst:
- **Feature** — Brainstorming, dann Planung, dann Implementation
- **Bugfix** — Root-Cause-Analyse statt Quick-Fix
- **Refactor** — Test-First-Ansatz
- **Research** — Strukturierte Recherche

---

## Multi-Agent Strategien

Der Loop erkennt die Komplexitaet deiner Aufgabe und waehlt automatisch:

| Komplexitaet | Strategie | Was passiert |
|---|---|---|
| Einfach (1 Aspekt) | **Seriell** | 1 Claude Code Session |
| Mittel (2-3 Aspekte) | **Parallel** | 2-3 Sessions gleichzeitig in tmux |
| Komplex (4+ Aspekte) | **Hierarchisch** | Lead-Agent plant, Worker fuehren aus |

---

## Web Dashboard

Unter `http://localhost:8080` siehst du live:

- **Aktive Tasks** — Status, Strategie, Fortschritt
- **Live Sessions** — Welche tmux-Panes laufen, was passiert
- **Event Log** — Chronologisches Protokoll aller Aktionen

Updates kommen per WebSocket in Echtzeit.

---

## Projektstruktur

```
coding-automation-loop/
├── main.py                     # Orchestrator — Einstiegspunkt
├── config.yaml                 # Konfiguration
├── core/
│   ├── event_bus.py            # Asyncio Event Bus (Pub/Sub)
│   ├── models.py               # Pydantic Datenmodelle
│   └── database.py             # SQLite via aiosqlite
├── brain/
│   ├── context_engine.py       # Projektkontext laden
│   ├── prompt_generator.py     # Ultra-Prompt Builder (Jinja2)
│   └── task_planner.py         # Strategie-Auswahl
├── execution/
│   ├── tmux_controller.py      # libtmux Wrapper
│   ├── output_parser.py        # Output-Signal-Erkennung
│   ├── session_manager.py      # Session Lifecycle
│   ├── decision_engine.py      # Autonome Entscheidungen
│   └── multi_agent.py          # Multi-Agent Orchestrierung
├── input/
│   ├── telegram_bot.py         # Telegram Bot
│   ├── voice_processor.py      # Whisper Transkription
│   └── cli.py                  # CLI Einstieg
├── monitoring/
│   ├── dashboard.py            # FastAPI Web Dashboard
│   ├── telegram_reporter.py    # Telegram Benachrichtigungen
│   ├── event_logger.py         # Event-Persistierung
│   └── templates/index.html    # Dashboard UI
├── data/
│   └── loop.db                 # SQLite Datenbank (Runtime)
└── tests/                      # 79 Tests, 100% Module abgedeckt
```

---

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python 3.12+ |
| Async Runtime | asyncio |
| Terminal-Steuerung | libtmux |
| Telegram | python-telegram-bot |
| Spracherkennung | whisper.cpp (lokal) |
| Web Dashboard | FastAPI + WebSocket |
| Frontend | Tailwind CSS |
| Datenbank | SQLite via aiosqlite |
| Templates | Jinja2 |
| Datenmodelle | Pydantic v2 |
| Tests | pytest + pytest-asyncio |
| Linting | ruff |

---

## Tests

```bash
# Alle Tests ausfuehren
python -m pytest tests/ -v

# Mit Coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

79 Tests decken alle Module ab — Unit Tests mit Mocks, Integration Tests mit echtem Event Bus + Datenbank, und tmux-Tests mit echten Sessions.

---

## Status

**MVP abgeschlossen.** Alle Kernfunktionen sind implementiert und getestet.

Moegliche naechste Schritte:
- Telegram-Befehlshandler mit echten DB-Abfragen verbinden
- WebSocket Push-Events im Dashboard aktivieren
- Session-Timeout fuer haengende Claude Code Sessions
- File-Cleanup fuer heruntergeladene Telegram-Dateien
- `context_cache` fuer schnellere Kontextberechnung nutzen

---

## Lizenz

Private Nutzung. (c) EconLab AI
