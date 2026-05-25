# 🎵 Rhythm Patterns - Project Overview

## What Is This?

**Rhythm Patterns** is a collection of creative, reusable drum pattern templates designed for developers and musicians who want to:

- **Learn** rhythm programming fundamentals
- **Reuse** proven patterns in their projects
- **Remix** existing patterns to create new variations
- **Share** their own creations with the community

---

## 📦 What's Included

### Core Components

| Component | Description |
|-----------|-------------|
| `patterns/core.py` | Foundation classes (Pattern, Step, Layer) |
| `patterns/basic_4x4.py` | Simple 4-on-the-floor beat |
| `patterns/syncopated_groove.py` | Hip-hop/R&B groove with swing |
| `patterns/polyrhythmic_flow.py` | Complex polyrhythms for experimental music |
| `patterns/breakbeat_chaos.py` | High-energy DnB/breakbeat patterns |
| `patterns/visualize.py` | ASCII visualization tools |

### Supporting Files

| File | Purpose |
|------|---------|
| `README.md` | Full documentation |
| `QUICKSTART.md` | 5-minute getting started guide |
| `CONTRIBUTING.md` | How to contribute patterns |
| `LICENSE` | CC0 1.0 (public domain) |
| `pyproject.toml` | Project configuration |
| `examples/demo.py` | Interactive demo script |
| `tests/test_patterns.py` | Test suite (17 tests) |

---

## 🎯 Design Philosophy

### Easy to Fork

Every pattern is designed with forking in mind:

```python
# 1. Copy a pattern file
# 2. Modify the create_pattern() function
# 3. Done!
```

### Zero Dependencies

Core functionality uses only Python stdlib. Optional MIDI/audio backends can be added as needed.

### Well Documented

Every function has docstrings. Every pattern has usage examples.

### Test Coverage

All patterns include tests. Changes shouldn't break existing functionality.

---

## 🚀 Usage Examples

### Basic Usage

```python
from patterns.basic_4x4 import BASIC_4X4

BASIC_4X4.play()
BASIC_4X4.export_midi("beat.mid")
```

### Custom Pattern

```python
from patterns.core import Pattern

my_pattern = Pattern(name="My Beat", bpm=100)

# Add kick
kick = my_pattern.add_layer("kick")
kick.add_step(0)
kick.add_step(6)
kick.add_step(10)

# Add snare
snare = my_pattern.add_layer("snare")
snare.add_step(4, velocity=0.8)
snare.add_step(12, velocity=0.9)

my_pattern.play()
```

### Pattern Combos

```python
from patterns.basic_4x4 import BASIC_4X4
from patterns.syncopated_groove import SYNCOPATED_GROOVE

# Combine patterns
combined = BASIC_4X4 + SYNCOPATED_GROOVE
combined.play()
```

---

## 📊 Pattern Structure

Each pattern follows this anatomy:

```
Pattern Name
├── Metadata (name, bpm, time_signature, difficulty)
├── Layers
│   ├── Kick (positions, velocities)
│   ├── Snare (positions, velocities)
│   └── Hi-hat (positions, velocities)
├── Functions
│   ├── create_pattern() - Main factory
│   └── Variations (optional)
└── Demo (__main__ block)
```

---

## 🔧 Extending the System

### Add a New Pattern Type

1. Create `patterns/my_style.py`
2. Implement `create_pattern()` function
3. Export default instance
4. Add to `patterns/__init__.py`

### Add a New Instrument

```python
# In your pattern file
percussion = pattern.add_layer("conga", velocity=0.6)
percussion.add_step(2)
percussion.add_step(10)
```

### Add Export Formats

```python
# Example: Export to audio
def export_wav(pattern, filename):
    import numpy as np
    # Generate audio samples
    pass
```

---

## 🎼 Rhythm Concepts

### Time Signatures

The system supports any time signature:

```python
# 4/4 (common time)
pattern = Pattern(time_signature=(4, 4))

# 3/4 (waltz)
pattern = Pattern(time_signature=(3, 4))

# 7/8 (odd meter)
pattern = Pattern(time_signature=(7, 8))
```

### Swing/Groove

```python
# 0.0 = straight
# 0.5 = moderate swing
# 0.7 = heavy swing
pattern.swing = 0.7
```

### Polyrhythms

```python
# 3 against 4 (triplets over 4/4)
# 5 against 4 (quintuplets over 4/4)
# 7 against 4 (septuplets over 4/4)
```

---

## 📈 Roadmap

### Phase 1: Foundation ✅
- [x] Core pattern classes
- [x] Basic patterns (4 patterns)
- [x] Test suite
- [x] Documentation

### Phase 2: Expansion (Future)
- [ ] MIDI export (requires `mido`)
- [ ] Audio playback (requires `sounddevice`)
- [ ] Pattern generator AI
- [ ] Web interface

### Phase 3: Community (Future)
- [ ] Pattern sharing platform
- [ ] Mobile app
- [ ] DAW plugin (VST/AU)
- [ ] Integration with music software

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

Quick start:
```bash
git clone https://github.com/YOUR-USERNAME/rhythm-patterns.git
cd rhythm-patterns
pip install -e ".[dev]"
pytest tests/
```

---

## 📜 License

**CC0 1.0 Universal** - No rights reserved.

This work is dedicated to the public domain. Use it for anything you want!

---

## 🙏 Acknowledgments

Inspired by:
- Classic drum machines (808, 909, TR-808)
- Hip-hop production techniques
- Electronic music theory
- Open source music software

---

## 📞 Contact

- **Repository**: https://github.com/YOUR-USERNAME/rhythm-patterns
- **Issues**: https://github.com/YOUR-USERNAME/rhythm-patterns/issues
- **Discussions**: https://github.com/YOUR-USERNAME/rhythm-patterns/discussions

---

**Keep the rhythm alive! 🎵**
