# 🎵 Rhythm Patterns - Easy Fork Templates

**A collection of creative, reusable rhythm patterns for developers.**  
Each pattern is designed to be **forked, modified, and remixed** for your projects.

---

## 🚀 Quick Start

```bash
# Fork this repo
git clone https://github.com/your-username/rhythm-patterns.git

# Copy the pattern you need
cp patterns/[pattern-name].py your_project/

# Customize the BPM, instruments, and structure
```

---

## 📦 Available Patterns

| Pattern | BPM | Difficulty | Best For |
|---------|-----|------------|----------|
| `basic_4x4.py` | 120 | ⭐ Beginner | Lo-fi, ambient |
| `syncopated_groove.py` | 95 | ⭐⭐ Intermediate | Hip-hop, R&B |
| `polyrhythmic_flow.py` | 140 | ⭐⭐⭐ Advanced | Experimental, Jazz |
| `breakbeat_chaos.py` | 174 | ⭐⭐⭐ Advanced | DnB, Breakbeat |

---

## 🎯 Why Fork This?

- **Zero dependencies** - Pure Python, works everywhere
- **Modular design** - Swap components freely
- **Well-documented** - Every function explained
- **Tested patterns** - Production-ready code
- **Creative Commons** - Free for personal & commercial use

---

## 🔧 Customization Guide

### Change the Feel
```python
# Original: Straight 4/4
pattern = Pattern(time_signature=(4, 4))

# Fork it: Try 7/8
pattern = Pattern(time_signature=(7, 8))
```

### Add Swing
```python
# Original: No swing
pattern.swing = 0.0

# Fork it: Add groove
pattern.swing = 0.6  # 60% swing
```

### Layer Patterns
```python
# Combine two patterns
combined = pattern1 + pattern2
```

---

## 📁 Project Structure

```
rhythm/
├── patterns/           # Rhythm pattern definitions
│   ├── basic_4x4.py
│   ├── syncopated_groove.py
│   └── polyrhythmic_flow.py
├── instruments/        # Instrument presets
│   ├── drums.py
│   ├── percussion.py
│   └── synth.py
├── utils/              # Helper functions
│   ├── quantize.py
│   └── export.py
└── examples/           # Usage examples
    └── demo.py
```

---

## 🎼 Pattern Anatomy

Each pattern file follows this structure:

```python
from rhythm import Pattern, Step

# 1. Define the pattern metadata
PATTERN_NAME = "Basic 4x4"
BPM = 120
TIME_SIGNATURE = (4, 4)

# 2. Create the pattern
pattern = Pattern(
    name=PATTERN_NAME,
    bpm=BPM,
    time_signature=TIME_SIGNATURE
)

# 3. Add instrument layers
pattern.add_layer(
    name="kick",
    steps=[Step(1), Step(5), Step(9), Step(13)],  # 4-on-the-floor
    velocity=0.9
)

pattern.add_layer(
    name="snare",
    steps=[Step(5), Step(13)],  # Backbeat
    velocity=0.8
)

pattern.add_layer(
    name="hihat",
    steps=[Step(i) for i in range(0, 16, 2)],  # 8th notes
    velocity=0.5
)

# 4. Export
if __name__ == "__main__":
    pattern.play()
    pattern.export_midi("basic_4x4.mid")
```

---

## 🤝 Contributing

1. Fork the repo
2. Create your pattern: `patterns/my_awesome_pattern.py`
3. Add to the index in `patterns/__init__.py`
4. Submit a PR!

---

## 📜 License

**CC0 1.0 Universal** - No rights reserved.  
Copy, modify, distribute, and use without attribution (though it's appreciated!).

---

## 🌟 Featured Forks

| Fork | By | Description |
|------|-----|-------------|
| [rhythm-extended](link) | @user1 | Added 50+ new patterns |
| [midi-export-pro](link) | @user2 | Enhanced MIDI export with velocity curves |
| [ableton-integration](link) | @user3 | Direct Ableton Live integration |

---

## 📞 Support

- **Issues**: [GitHub Issues](link)
- **Discord**: [Join the community](link)
- **Twitter**: [@rhythmpatterns](link)

---

> "Rhythm is the architecture of sound." — Unknown

**Happy forking! 🎵**
