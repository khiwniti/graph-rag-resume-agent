# 🎵 Quick Start Guide

Get started with rhythm patterns in under 5 minutes!

---

## Step 1: Fork or Clone

```bash
# Fork the repo on GitHub, then clone:
git clone https://github.com/YOUR-USERNAME/rhythm-patterns.git
cd rhythm-patterns
```

---

## Step 2: Install (Optional)

```bash
# For basic usage (no installation needed - pure Python!)
python examples/demo.py

# For development:
pip install -e ".[dev]"

# With MIDI support:
pip install -e ".[dev,midi]"
```

---

## Step 3: Use a Pattern

```python
from patterns.basic_4x4 import BASIC_4X4

# Play it
BASIC_4X4.play()

# Export to MIDI
BASIC_4X4.export_midi("my_beat.mid")
```

---

## Step 4: Customize

### Change the BPM

```python
from patterns.basic_4x4 import create_pattern

slow = create_pattern(bpm=80)
fast = create_pattern(bpm=160)
```

### Add Swing

```python
from patterns.syncopated_groove import create_pattern

groovy = create_pattern(swing=0.7)  # 70% swing
```

### Create Your Own

```python
from patterns.core import Pattern, Step

# Create empty pattern
my_pattern = Pattern(name="My Beat", bpm=120)

# Add a kick drum
kick = my_pattern.add_layer("kick")
kick.add_step(0)   # Beat 1
kick.add_step(8)   # Beat 3

# Add a snare
snare = my_pattern.add_layer("snare")
snare.add_step(4)  # Beat 2
snare.add_step(12) # Beat 4

# Add hi-hats
hihat = my_pattern.add_layer("hihat")
for i in range(0, 16, 2):
    hihat.add_step(i)

# Play it!
my_pattern.play()
```

---

## Step 5: Share!

1. Save your pattern to `patterns/my_awesome_pattern.py`
2. Add it to `patterns/__init__.py`
3. Push to your fork
4. Submit a PR!

---

## Common Tasks

### 🎯 Create a half-time feel
```python
pattern.bpm = original_pattern.bpm // 2
```

### 🎯 Create a double-time feel
```python
pattern.bpm = original_pattern.bpm * 2
```

### 🎯 Add a rest (mute steps)
```python
for step in pattern.get_layer("hihat").steps:
    if step.position == 6:  # Mute position 6
        step.muted = True
```

### 🎯 Change velocity
```python
for step in pattern.get_layer("kick").steps:
    step.velocity = 0.5  # Softer kick
```

---

## Need Help?

- Check `examples/demo.py` for full usage examples
- Read `README.md` for the full documentation
- Open an issue on GitHub for bugs or feature requests

---

**Happy rhythm making! 🎵**
