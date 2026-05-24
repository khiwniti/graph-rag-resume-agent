"""
Syncopated Groove - Hip-Hop / R&B

Features off-beat accents and ghost notes for that head-nodding feel.
Perfect for:
- Hip-hop beats
- R&B productions
- Neo-soul tracks
- Chillhop

BPM: 95
Difficulty: ⭐⭐ Intermediate
"""

from .core import Pattern, Step, Layer

# Pattern metadata
PATTERN_NAME = "Syncopated Groove"
BPM = 95
TIME_SIGNATURE = (4, 4)
DIFFICULTY = 2


def create_pattern(bpm: int = BPM, swing: float = 0.6) -> Pattern:
    """Create the syncopated groove pattern.

    Args:
        bpm: Override the default BPM
        swing: Swing amount (0.0-1.0, default 0.6 for that groove)

    Returns:
        Pattern object ready to play or export
    """
    pattern = Pattern(
        name=PATTERN_NAME,
        bpm=bpm,
        time_signature=TIME_SIGNATURE,
        swing=swing
    )

    # Kick - syncopated pattern
    kick_layer = pattern.add_layer("kick", velocity=0.9)
    kick_positions = [0, 5, 10, 12]  # Off-beat accents
    for pos in kick_positions:
        kick_layer.add_step(pos, velocity=0.9 if pos == 0 else 0.7)

    # Snare - classic backbeat with ghost notes
    snare_layer = pattern.add_layer("snare", velocity=0.8)
    snare_layer.add_step(4, velocity=1.0)   # Main backbeat
    snare_layer.add_step(12, velocity=0.9)  # Second backbeat
    snare_layer.add_step(14, velocity=0.4)  # Ghost note

    # Hi-hat - swung 8th notes with accent
    hihat_layer = pattern.add_layer("hihat", velocity=0.5)
    for pos in range(0, 16, 2):
        velocity = 0.7 if pos % 4 == 0 else 0.4  # Accent first 8th
        hihat_layer.add_step(pos, velocity=velocity)

    # Optional: Add a ride cymbal layer (commented out by default)
    # ride_layer = pattern.add_layer("ride", velocity=0.4)
    # for pos in range(0, 16, 4):
    #     ride_layer.add_step(pos, velocity=0.4)

    return pattern


# Default instance
SYNCOPATED_GROOVE = create_pattern()


# Variation: Double-time feel
def create_double_time(bpm: int = BPM * 2) -> Pattern:
    """Create a double-time variation."""
    pattern = create_pattern(bpm=bpm, swing=0.5)
    pattern.name = "Syncopated Groove (Double-Time)"
    return pattern


if __name__ == "__main__":
    # Demo: play the pattern
    SYNCOPATED_GROOVE.play()
    SYNCOPATED_GROOVE.export_midi("syncopated_groove.mid")

    # Demo: try different swing values
    for swing_amt in [0.0, 0.4, 0.6, 0.8]:
        pattern = create_pattern(swing=swing_amt)
        print(f"\n--- Swing: {swing_amt * 100:.0f}% ---")
        pattern.play()
