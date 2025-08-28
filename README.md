# family-schedulekit

A reusable, machine-readable schema for defining **family custody / parenting schedules**.
Designed to be **AI-friendly** (JSON rules + examples) so you can generate clear messages, calendar entries, or visualizations for any given date.

---

## 🎯 Purpose

This project provides:
- A **neutral schema** for defining parenting time schedules.
- A **JSON template** for rules (weekdays, weekends, holidays, exceptions).
- **Worked examples** (with ISO 8601 calendar week rotation).
- Clear **handoff logic** for school days and special Sunday rules.

You can reuse this schema for any co-parenting arrangement by changing the `parties` and `rules`.

---

## 📖 Rules Summary

- **Weekdays**
  - Monday → Mom
  - Tuesday → Dad
  - Wednesday → Mom
  - Thursday → Dad

- **Weekends**
  - **Odd ISO weeks (CW1, CW3, CW5, …):** Mom has Friday–Sunday.
  - **Even ISO weeks (CW2, CW4, CW6, …):**
    - Dad has Friday + Saturday.
    - Sunday depends on the week number:
      - If `CW % 4 == 0`: Dad has Sunday, but must return children to Mom by **1 PM**.
      - Otherwise: Mom has Sunday.

- **Handoffs**
  - Weekdays: at **school** (drop-off/pick-up).
  - Sunday exception: **Dad → Mom by 1 PM** if it’s Dad’s Sunday.

- **Calendar Week System**
  - Uses **ISO 8601 week numbering** (CW1 begins on the Monday containing the first Thursday of the year).

---

## 📦 JSON Template

```json
{
  "parties": {
    "mom": "Jane",
    "dad": "John",
    "children": ["Roger", "Jamie"]
  },
  "calendar_week_system": "ISO8601",
  "handoff": {
    "weekdays": "school",
    "sunday_dad_to_mom": "by_1pm"
  },
  "rules": {
    "weekdays": {
      "monday": "mom",
      "tuesday": "dad",
      "wednesday": "mom",
      "thursday": "dad"
    },
    "weekends": {
      "odd_weeks": {
        "friday": "mom",
        "saturday": "mom",
        "sunday": "mom"
      },
      "even_weeks": {
        "friday": "dad",
        "saturday": "dad",
        "sunday": {
          "cw_mod4_equals_0": "dad",
          "otherwise": "mom"
        }
      }
    }
  },
  "holidays": {}
}
```

---

## 🚀 Installation

```bash
pip install family-schedulekit
```

Or for development:
```bash
make dev
```

---

## 📚 Usage

### CLI Commands

```bash
# Generate a new schedule configuration
family-schedulekit init --mom ParentA --dad ParentB --child Child1 --child Child2

# Resolve a specific date
family-schedulekit resolve 2025-02-23

# Resolve an entire week
family-schedulekit resolve --week-of 2025-02-23

# List available templates
family-schedulekit list-templates
```

### Python API

```python
from family_schedulekit import resolve_for_date, load_default_config
from datetime import date

config = load_default_config()
result = resolve_for_date(date(2025, 2, 23), config)
print(result)
# {'date': '2025-02-23', 'calendar_week': 8, 'guardian': 'dad', 'handoff': 'dad_to_mom_by_1pm'}
```

### AI Integration

Generate comprehensive context for AI assistants to understand and work with your schedule:

```bash
# Generate AI context with schema and examples
family-schedulekit ai-context --weeks 4 --output ai-context.json

# Or output to stdout for piping
family-schedulekit ai-context --date 2025-03-01 | jq .rules_summary
```

```python
from family_schedulekit import generate_ai_context
from datetime import date

# Generate context for AI assistants
context = generate_ai_context(
    target_date=date(2025, 3, 1),
    weeks_ahead=4,
    include_examples=True,
    include_schema=True
)

# Context includes:
# - JSON schema for validation
# - Human-readable rules
# - Resolved schedule examples
# - Decision-making examples
# - AI-specific instructions
```

The AI context includes everything needed for LLMs to:
- Make custody decisions for any date
- Draft schedule-aware messages
- Plan activities considering handoff times
- Resolve scheduling conflicts
- Generate calendar entries

---

## 📝 License

MIT License © 2025 Weekend Superhero LLC. See [LICENSE](LICENSE) for details.
