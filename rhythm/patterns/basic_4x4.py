"""
Basic 4/4 Pattern - The Foundation

A simple, solid 4-on-the-floor beat. Perfect for:
- Lo-fi hip hop
- Ambient tracks
- Background music
- Learning the system

BPM: 120
Difficulty: ⭐ Beginner
"""

from .core import Pattern, Step, Layer

# Pattern metadata
PATTERN_NAME = "Basic 4x4"
BPM = 120
TIME_SIGNATURE = (4, 4)
DIFFICULTY = 1


def create_pattern(bpm: int = BPM) -> Pattern:
    """Create the basic 4x4 pattern.

    Args:
        bpm: Override the default BPM

    Returns:
        Pattern object ready to play or export
    """
    pattern = Pattern(
        name=PATTERN_NAME,
        bpm=bpm,
        time_signature=TIME_SIGNATURE
    )

    # Kick drum - 4 on the floor
    kick_layer = pattern.add_layer("kick", velocity=0.9)
    for pos in [0, 4, 8, 12]:  # Every quarter note
        kick_layer.add_step(pos, velocity=0.9)

    # Snare - backbeat on 2 and 4
    snare_layer = pattern.add_layer("snare", velocity=0.8)
    for pos in [4, 12]:  # Beats 2 and 4
        snare_layer.add_step(pos, velocity=0.8)

    # Hi-hat - 8th notes
    hihat_layer = pattern.add_layer("hihat", velocity=0.5)
    for pos in range(0, 16, 2):  # Every 2 steps (8th notes)
        hihat_layer.add_step(pos, velocity=0.5)

    return pattern


# Default instance
BASIC_4X4 = create_pattern()


if __name__ == "__main__":
    # Demo: play the pattern
    BASIC_4X4.play()
    BASIC_4X4.export_midi("basic_4x4.mid")
