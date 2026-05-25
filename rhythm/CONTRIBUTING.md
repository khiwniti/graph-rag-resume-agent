# Contributing to Rhythm Patterns

Thanks for wanting to contribute! This guide will help you get started.

---

## 🌟 Quick Start

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR-USERNAME/rhythm-patterns.git`
3. **Create a branch**: `git checkout -b my-pattern`
4. **Make your changes**
5. **Test** your changes
6. **Push** and submit a PR

---

## 📝 Creating a New Pattern

### Step 1: Create the File

Create `patterns/my_awesome_pattern.py`:

```python
"""
My Awesome Pattern - Description

Brief description of what makes this pattern special.
Perfect for:
- Genre 1
- Genre 2

BPM: 120
Difficulty: ⭐⭐ Intermediate
"""

from .core import Pattern, Step

PATTERN_NAME = "My Awesome Pattern"
BPM = 120
TIME_SIGNATURE = (4, 4)
DIFFICULTY = 2


def create_pattern(bpm: int = BPM) -> Pattern:
    """Create the pattern.

    Args:
        bpm: Override the default BPM

    Returns:
        Pattern object
    """
    pattern = Pattern(
        name=PATTERN_NAME,
        bpm=bpm,
        time_signature=TIME_SIGNATURE
    )

    # Add your layers here
    kick = pattern.add_layer("kick", velocity=0.9)
    kick.add_step(0)
    kick.add_step(8)

    snare = pattern.add_layer("snare", velocity=0.8)
    snare.add_step(4)
    snare.add_step(12)

    return pattern


# Default instance
MY_AWESOME_PATTERN = create_pattern()


if __name__ == "__main__":
    MY_AWESOME_PATTERN.play()
```

### Step 2: Update `__init__.py`

Add your pattern to `patterns/__init__.py`:

```python
from .my_awesome_pattern import MY_AWESOME_PATTERN

__all__ = [
    # ... existing patterns
    "MY_AWESOME_PATTERN",
]
```

### Step 3: Add Tests

Add tests to `tests/test_patterns.py`:

```python
class TestMyAwesomePattern:
    def test_pattern_exists(self):
        from patterns.my_awesome_pattern import create_pattern
        pattern = create_pattern()
        assert pattern is not None

    def test_has_required_layers(self):
        from patterns.my_awesome_pattern import MY_AWESOME_PATTERN
        layer_names = [l.name for l in MY_AWESOME_PATTERN.layers]
        assert "kick" in layer_names
```

### Step 4: Run Tests

```bash
python -m pytest tests/ -v
```

---

## 🎨 Code Style

We use standard Python formatting:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
black patterns/
isort patterns/

# Run linter
mypy patterns/
```

---

## 📋 Pull Request Guidelines

### Before Submitting:

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Code is formatted (`black .`)
- [ ] Docstrings are complete
- [ ] Pattern has been tested in demo.py

### PR Template:

```markdown
## Description
What does this pattern do?

## Genre/Style
What music styles is this for?

## Example Usage
```python
from patterns.my_pattern import MY_PATTERN
MY_PATTERN.play()
```

## Checklist
- [ ] Tests added
- [ ] Documentation complete
- [ ] Demo updated
```

---

## 🐛 Reporting Bugs

1. Check existing issues first
2. Use the bug report template
3. Include:
   - Python version
   - Steps to reproduce
   - Expected vs actual behavior
   - Code example (if applicable)

---

## 💡 Feature Requests

We love new ideas! Open an issue with:
- What you want to achieve
- Why it's useful
- Example usage

---

## 🎯 Areas Needing Contribution

- [ ] More pattern variations (trap, house, techno, etc.)
- [ ] Instrument presets (808, 909, acoustic)
- [ ] Export formats (MIDI, WAV, audio)
- [ ] Visual pattern editor
- [ ] Pattern generator AI
- [ ] Mobile app integration

---

## 📜 License

By contributing, you agree that your contributions are licensed under CC0 1.0 (same as the project).

---

## 🙏 Thank You!

Your contribution helps make rhythm patterns better for everyone!
