"""
Polyrhythmic Flow - Experimental / Jazz

Overlapping rhythmic patterns creating complex, evolving textures.
Perfect for:
- Experimental electronic
- Jazz fusion
- Math rock
- Progressive music

BPM: 140
Difficulty: ⭐⭐⭐ Advanced
"""

from __future__ import annotations

from typing import List
from .core import Pattern, Step, Layer

# Pattern metadata
PATTERN_NAME = "Polyrhythmic Flow"
BPM = 140
TIME_SIGNATURE = (4, 4)
DIFFICULTY = 3


def create_pattern(bpm: int = BPM, complexity: int = 3) -> Pattern:
    """Create the polyrhythmic pattern.

    Args:
        bpm: Override the default BPM
        complexity: Number of overlapping polyrhythms (2-5)

    Returns:
        Pattern object ready to play or export
    """
    pattern = Pattern(
        name=PATTERN_NAME,
        bpm=bpm,
        time_signature=TIME_SIGNATURE
    )

    # Base layer: 4/4 kick
    kick_layer = pattern.add_layer("kick", velocity=0.8)
    kick_layer.add_step(0, velocity=0.9)
    kick_layer.add_step(8, velocity=0.7)

    # Polyrhythm 1: 3 over 4
    if complexity >= 2:
        poly3_layer = pattern.add_layer("poly_3", velocity=0.6)
        for i in range(3):
            pos = (i * 16 // 3) % 16
            poly3_layer.add_step(pos, velocity=0.6)

    # Polyrhythm 2: 5 over 4
    if complexity >= 3:
        poly5_layer = pattern.add_layer("poly_5", velocity=0.5)
        for i in range(5):
            pos = (i * 16 // 5) % 16
            poly5_layer.add_step(pos, velocity=0.5)

    # Polyrhythm 3: 7 over 4
    if complexity >= 4:
        poly7_layer = pattern.add_layer("poly_7", velocity=0.4)
        for i in range(7):
            pos = (i * 16 // 7) % 16
            poly7_layer.add_step(pos, velocity=0.4)

    # Polyrhythm 4: 11 over 4
    if complexity >= 5:
        poly11_layer = pattern.add_layer("poly_11", velocity=0.3)
        for i in range(11):
            pos = (i * 16 // 11) % 16
            poly11_layer.add_step(pos, velocity=0.3)

    # Snare: irregular pattern
    snare_layer = pattern.get_layer("snare") or pattern.add_layer("snare", velocity=0.8)
    snare_positions = [4, 11, 13]  # Irregular placement
    for pos in snare_positions:
        snare_layer.add_step(pos, velocity=0.8 if pos == 4 else 0.6)

    # Hi-hats: 16th notes with velocity variation
    hihat_layer = pattern.add_layer("hihat", velocity=0.4)
    for i in range(16):
        # Velocity based on position (accent beats 0, 4, 8, 12)
        vel = 0.6 if i % 4 == 0 else 0.35
        hihat_layer.add_step(i, velocity=vel)

    return pattern


# Default instance
POLYRHYTHMIC_FLOW = create_pattern()


# Utility: Generate polyrhythm of any ratio
def create_polyrhythm(n: int, over: int = 4, length: int = 16) -> List[Step]:
    """Create an n:over polyrhythm.

    Args:
        n: Number of beats in the polyrhythm
        over: What it's played over (usually 4 for 4/4)
        length: Total steps in the pattern

    Returns:
        List of Step objects
    """
    steps = []
    for i in range(n):
        pos = (i * length // n) % length
        steps.append(Step(position=pos, velocity=1.0 / n))
    return steps


if __name__ == "__main__":
    # Demo: play with different complexity levels
    for complexity in range(2, 6):
        pattern = create_pattern(complexity=complexity)
        print(f"\n--- Complexity: {complexity} polyrhythms ---")
        pattern.play()

    # Demo: export full version
    POLYRHYTHMIC_FLOW.export_midi("polyrhythmic_flow.mid")
