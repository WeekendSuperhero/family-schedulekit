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
    - Dad has Friday + Saturday (can use modulo rules for flexibility).
    - Sunday uses **modulo rules** based on calendar week number:
      - If `CW % 4 == 0`: Dad has Sunday, but must return children to Mom by **1 PM**.
      - Otherwise: Mom has Sunday.
    - **Advanced**: Any even-week day can use modulo rules for complex patterns (see Advanced Configuration below).

- **Handoffs**
  - Weekdays: at **school** (drop-off/pick-up).
  - **Special handoffs** can be configured for any weekday with specific times and guardians.
  - Example: Sunday **Dad → Mom by 1 PM** when Dad has custody.

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
    "special_handoffs": {
      "sunday": {
        "from_guardian": "dad",
        "to_guardian": "mom",
        "time": {
          "hour": 13,
          "minute": 0,
          "by": true
        },
        "description": "dad_to_mom_by_1pm"
      }
    }
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
          "modulo_rules": [
            {
              "modulo": 4,
              "remainder": 0,
              "guardian": "dad"
            }
          ],
          "otherwise": "mom"
        }
      }
    }
  },
  "holidays": {
    "2025-12-25": "mom",
    "2025-07-04": "dad"
  },
  "visualization": {
    "mom": "hot_pink",
    "dad": "midnight_blue",
    "holiday": "light_blue",
    "unknown": "gray"
  }
}
```

---

## 🔧 Advanced Configuration

### Modulo Rules for Complex Schedules

The schema supports flexible **modulo rules** for even-week days, allowing complex rotation patterns beyond simple alternating weeks.

#### Basic Modulo Rule Structure

```json
{
  "modulo_rules": [
    {
      "modulo": 4,
      "remainder": 0,
      "guardian": "dad"
    }
  ],
  "otherwise": "mom"
}
```

- **`modulo`**: The divisor for the modulo operation (≥2)
- **`remainder`**: The target remainder when CW % modulo is calculated (0 to modulo-1)
- **`guardian`**: Which parent gets custody when the rule matches
- **`otherwise`**: Fallback guardian when no rules match

#### Multiple Modulo Rules

You can chain multiple modulo rules for a single day. Rules are evaluated in order:

```json
"saturday": {
  "modulo_rules": [
    {
      "modulo": 3,
      "remainder": 0,
      "guardian": "mom"
    },
    {
      "modulo": 3,
      "remainder": 1,
      "guardian": "dad"
    }
  ],
  "otherwise": "dad"
}
```

This gives Mom every CW divisible by 3 (CW6, CW12, CW18...), Dad when CW%3==1 (CW4, CW10, CW16...), and Dad otherwise (CW8, CW14...).

#### Advanced Example: Different Modulo on Each Day

```json
"even_weeks": {
  "friday": {
    "modulo_rules": [
      {
        "modulo": 4,
        "remainder": 2,
        "guardian": "mom"
      }
    ],
    "otherwise": "dad"
  },
  "saturday": {
    "modulo_rules": [
      {
        "modulo": 3,
        "remainder": 0,
        "guardian": "mom"
      }
    ],
    "otherwise": "dad"
  },
  "sunday": {
    "modulo_rules": [
      {
        "modulo": 4,
        "remainder": 0,
        "guardian": "dad"
      }
    ],
    "otherwise": "mom"
  }
}
```

### Holiday Overrides

Define specific dates that override normal schedule rules:

```json
"holidays": {
  "2025-12-25": "mom",
  "2025-07-04": "dad",
  "2025-11-27": "dad"
}
```

Dates must be in `YYYY-MM-DD` format. When a date appears in holidays, it completely overrides weekday/weekend rules.

**Note:** The `holidays` field is deprecated in favor of the more flexible `swaps` system (see below).

### Date Swaps/Exceptions

Use `swaps` for schedule exceptions with automatic visual differentiation and optional notes:

```json
"swaps": {
  "2025-12-25": {
    "guardian": "mom",
    "note": "Christmas",
    "handoff": "at mom's house by 10am"
  },
  "2025-07-04": {
    "guardian": "dad",
    "color": "red",
    "note": "4th of July swap"
  },
  "2025-03-15": {
    "guardian": "dad",
    "note": "Spring break trade"
  }
}
```

**Swap Features:**

- **Automatic color shading**: By default, swap days use a lighter/darker shade of the guardian's color
- **Custom colors**: Override with `"color": "red"` or any named color/hex value
- **Notes**: Add context with the `note` field (shown in visualizations)
- **Custom handoffs**: Specify handoff details specific to this swap

**Visualization Colors:**
Configure swap shading and week start day in the `visualization` section:

```json
"visualization": {
  "mom": "hot_pink",
  "dad": "midnight_blue",
  "swap_shade_percent": 20,
  "start_weekday": "sunday"
}
```

- `swap_shade_percent`: Controls how much to lighten (for dark colors) or darken (for light colors) swap dates. Default is 20%.
- `start_weekday`: First day of week in PNG calendars. Options: `"monday"` (default) or `"sunday"`

### Special Handoff Rules

Configure specific handoff times and guardians for any weekday:

```json
"handoff": {
  "weekdays": "school",
  "special_handoffs": {
    "sunday": {
      "from_guardian": "dad",
      "to_guardian": "mom",
      "time": {
        "hour": 13,
        "minute": 0,
        "by": true
      },
      "description": "dad_to_mom_by_1pm"
    },
    "friday": {
      "from_guardian": "mom",
      "to_guardian": "dad",
      "time": {
        "hour": 15,
        "minute": 30
      },
      "description": "Weekend pickup at school"
    }
  }
}
```

**Time Format:**

- `hour`: Integer 0-23 (required)
- `minute`: Integer 0-59 (default: 0)
- `use_24h`: Boolean, use 24-hour format (default: false = 12-hour AM/PM)
- `by`: Boolean, indicates "by this time" vs "at this time" (default: false)

**Time Examples:**

```json
{"hour": 13, "minute": 0}              // 1:00 PM (or 1PM)
{"hour": 15, "minute": 30}             // 3:30 PM
{"hour": 18, "minute": 0, "use_24h": true}  // 18:00
{"hour": 13, "minute": 0, "by": true}  // by 1:00 PM
```

**Special handoff rules apply when:**

- The current day matches a configured weekday
- The guardian with custody matches `from_guardian`
- Then the handoff description will be included in the schedule

**Examples:**

Simple weekday handoffs:

```json
"handoff": {
  "weekdays": "school"
}
```

Detailed weekday handoffs with time:

```json
"handoff": {
  "weekdays": {
    "location": "school",
    "time": "3pm"
  }
}
```

Multiple special handoffs:

```json
"handoff": {
  "weekdays": "school",
  "special_handoffs": {
    "monday": {
      "from_guardian": "dad",
      "to_guardian": "mom",
      "time": {
        "hour": 18,
        "minute": 0
      },
      "description": "Dad drops off at Mom's house"
    },
    "thursday": {
      "from_guardian": "mom",
      "to_guardian": "dad",
      "time": {
        "hour": 17,
        "minute": 0
      }
    }
  }
}
```

### Visualization Colors

Customize PNG calendar colors using named color presets or hex strings:

```json
"visualization": {
  "mom": "coral",
  "dad": "mint_green",
  "holiday": "gold",
  "unknown": "light_gray"
}
```

**Available Named Colors:**

| Category         | Named Colors                                                   |
| ---------------- | -------------------------------------------------------------- |
| **Pinks**        | `pink`, `hot_pink`, `deep_pink`                                |
| **Blues**        | `blue`, `dark_blue`, `midnight_blue`, `light_blue`, `sky_blue` |
| **Greens**       | `green`, `mint_green`, `forest_green`                          |
| **Purples**      | `purple`, `lavender`                                           |
| **Oranges/Reds** | `orange`, `coral`, `red`, `crimson`                            |
| **Yellows**      | `yellow`, `gold`                                               |
| **Grays**        | `gray`, `grey`, `light_gray`, `light_grey`                     |

You can also use hex strings: `"#FF1493"`, `"#81C995"`, etc.

**Default Colors:**

- `mom`: `hot_pink` (`#FF1493`)
- `dad`: `midnight_blue` (`#191970`)
- `holiday`: `light_blue` (`#AECBF8`)
- `unknown`: `gray` (`#C8C8C8`)

---

## 🚀 Installation

Requires **Python 3.13+** (supports up to Python 3.14).

```bash
uv sync --extra dev
```

> `uv sync --extra dev` installs runtime dependencies along with ruff, pytest, mypy, Pillow, and argcomplete.

---

## 📚 Usage

### Configuration File

The CLI uses a configuration file to store your schedule settings. By default, configs are stored in:

```
~/.config/family-schedulekit/schedule.json
```

This follows the [XDG Base Directory specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) for user configuration files.

**Config Versioning**: All config files include a `version` field (currently `1.0.0`) to track schema changes and ensure compatibility as the project evolves.

### CLI Commands

```bash
# Generate a new schedule configuration (saves to ~/.config/family-schedulekit/schedule.json)
family-schedulekit init --mom ParentA --dad ParentB --child Child1 --child Child2

# Or specify a custom location
family-schedulekit init --mom ParentA --dad ParentB --child Child1 --child Child2 -o path/to/config.json

# Resolve a specific date (uses ~/.config/family-schedulekit/schedule.json by default)
family-schedulekit resolve 2025-02-23

# Resolve an entire week
family-schedulekit resolve --week-of 2025-02-23

# List available templates
family-schedulekit list-templates

# Export multi-format schedule files (defaults to most recent Monday, uses your config)
family-schedulekit export --weeks 6 --formats json png

# Or specify a custom start date
family-schedulekit export --start 2025-02-03 --weeks 6 --formats json png

# Use a different config file
family-schedulekit export --config path/to/config.json --weeks 6 --formats png
```

> ℹ️ PNG export requires Pillow, which is included with the base install.

**PNG Color Scheme**: Calendar visualizations use color-coded cells to distinguish guardians:

- **Mom**: Hot Pink (`#FF1493` / DeepPink)
- **Dad**: Dark Blue (`#191970` / MidnightBlue)
- **Holiday override**: Light Blue (`#AECBF8`)

The colors are chosen for high contrast and accessibility, with automatic text color selection (black or white) based on background luminance.

### Working with `uv`

If you use [uv](https://docs.astral.sh/uv/):

```bash
# Sync project dependencies (runtime + dev extras)
uv sync --extra dev

# Run commands in the managed environment
uv run --extra dev pytest
uv run family-schedulekit export --start 2025-02-03 --weeks 6 --formats png
```

The workspace `uv.lock` should be committed so collaborators resolve the exact versions.

### Shell Completions

Auto-complete subcommands and options using [`argcomplete`](https://github.com/kislyuk/argcomplete):

```bash
# Enable once per shell session
eval "$(register-python-argcomplete family-schedulekit)"

# Or install permanently (Bash)
register-python-argcomplete family-schedulekit >> ~/.bash_completion
```

For `zsh`, add the following to your `~/.zshrc` (once):

```bash
autoload -U bashcompinit && bashcompinit
eval "$(register-python-argcomplete family-schedulekit)"
```

Reload your shell (`source ~/.zshrc`) and completions will be available.

Fish users can leverage `argcomplete`'s `register-python-argcomplete --shell fish` to generate functions.

### Python API

```python
from family_schedulekit import resolve_for_date, load_default_config
from datetime import date

config = load_default_config()
result = resolve_for_date(date(2025, 2, 23), config)
print(result)
# {'date': '2025-02-23', 'calendar_week': 8, 'guardian': 'dad', 'handoff': 'dad_to_mom_by_1pm'}
```

#### Custom PNG Colors

You can customize calendar visualization colors programmatically:

```python
from family_schedulekit.visualizer import render_schedule_image
from family_schedulekit.exporter import resolve_range
from family_schedulekit import load_default_config
from datetime import date
from pathlib import Path

config = load_default_config()
records = resolve_range(date(2025, 2, 3), weeks=6, cfg=config)

# Custom color palette (named colors, hex strings, or RGB tuples)
custom_palette = {
    "mom": "coral",          # Named color
    "dad": "mint_green",     # Named color
    "holiday": "#FFD700"     # Hex string
    # Can also use RGB tuples: "mom": (242, 139, 130)
}

render_schedule_image(
    records=records,
    start=date(2025, 2, 3),
    weeks=6,
    out_path=Path("custom_schedule.png"),
    palette=custom_palette
)
```

Default colors:

- `mom`: `#FF1493` (DeepPink / Hot Pink)
- `dad`: `#191970` (MidnightBlue / Dark Blue)
- `holiday`: `#AECBF8` (Light Blue)
- `unknown`: `#C8C8C8` (Gray)

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
