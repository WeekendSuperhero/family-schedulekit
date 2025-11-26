# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2025-11-19

### Added

- Initial PyPI release
- CLI commands for schedule management (`init`, `resolve`, `export`, `list-templates`, `list-colors`, `ai-context`)
- PNG calendar visualization with customizable colors
- AI context generation for LLM integration
- Support for 147 CSS3 color names
- YAML and JSON config file support
- XDG Base Directory specification compliance for config storage
- Shell completion support via `argcomplete`

### Features

- ISO 8601 week-based scheduling system
- Modulo rules for complex rotation patterns
- Holiday and swap exceptions with automatic color shading
- Special handoff configurations for specific weekdays
- Python API for programmatic access
- Type-safe schema validation with Pydantic
- Multi-format export (JSON, PNG)

### Documentation

- Comprehensive README with examples
- API documentation
- CLI usage examples
- Template system documentation

## [Unreleased]

### Added

- **Gradient handoff visualization**: PNG exports now display smooth color gradients for special handoffs with time information
  - Gradients show custody transition visually (e.g., guardian_2 color → guardian_1 color completing at handoff time)
  - 2-hour gradient window before handoff time for clear visualization
  - Automatically enabled when `config` is passed to `render_schedule_image()`
  - Only appears when special handoff conditions are met (resolver adds description to record)
- Comprehensive tests for gradient handoff feature

### Changed

- `render_schedule_image()` now accepts optional `config` parameter for gradient rendering
- Exporter automatically passes config to enable gradient feature in CLI exports

### Planned

- Additional export formats (iCal, CSV)
- Web-based visualization
- Interactive schedule builder
- More built-in templates
- Timezone support

---

For older versions and detailed commit history, see the [GitHub releases](https://github.com/weekendsuperhero/family-schedulekit/releases).
