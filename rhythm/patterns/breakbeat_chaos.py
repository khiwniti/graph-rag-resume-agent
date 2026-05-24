"""
Breakbeat Chaos - DnB / Breakbeat

High-energy broken beats with rapid fills and syncopation.
Perfect for:
- Drum & Bass
- Breakbeat
- Jungle
- Footwork

BPM: 174
Difficulty: ⭐⭐⭐ Advanced
"""

from .core import Pattern, Step, Layer

# Pattern metadata
PATTERN_NAME = "Breakbeat Chaos"
BPM = 174
TIME_SIGNATURE = (4, 4)
DIFFICULTY = 3


def create_pattern(bpm: int = BPM, intensity: str = "high") -> Pattern:
    """Create the breakbeat pattern.

    Args:
        bpm: Override the default BPM
        intensity: "low", "medium", or "high"

    Returns:
        Pattern object ready to play or export
    """
    pattern = Pattern(
        name=PATTERN_NAME,
        bpm=bpm,
        time_signature=TIME_SIGNATURE
    )

    # Velocity scaling based on intensity
    vel_scale = {"low": 0.6, "medium": 0.8, "high": 1.0}.get(intensity, 1.0)

    # Kick: Broken pattern with double kicks
    kick_layer = pattern.add_layer("kick", velocity=0.9 * vel_scale)
    kick_positions = [0, 3, 8, 10, 14]  # Broken beat pattern
    for pos in kick_positions:
        kick_layer.add_step(pos, velocity=0.9 * vel_scale if pos in [0, 8] else 0.7 * vel_scale)

    # Snare: Complex pattern with ghost notes
    snare_layer = pattern.add_layer("snare", velocity=0.8 * vel_scale)
    snare_pattern = [
        (4, 1.0),    # Main backbeat
        (12, 0.9),   # Second backbeat
        (6, 0.4),    # Ghost note
        (14, 0.5),   # Ghost note
        (15, 0.3),   # Quick ghost
    ]
    for pos, vel in snare_pattern:
        snare_layer.add_step(pos, velocity=vel * vel_scale)

    # Hi-hats: Rapid 16th notes with accents
    hihat_layer = pattern.add_layer("hihat", velocity=0.5 * vel_scale)
    for i in range(16):
        # Accent pattern: strong on 0, 4, 8, 12; medium on even; soft on odd
        if i % 4 == 0:
            vel = 0.7 * vel_scale
        elif i % 2 == 0:
            vel = 0.5 * vel_scale
        else:
            vel = 0.3 * vel_scale
        hihat_layer.add_step(i, velocity=vel)

    # Ride: Optional layer for variation
    # ride_layer = pattern.add_layer("ride", velocity=0.4 * vel_scale)
    # for i in range(0, 16, 4):
    #     ride_layer.add_step(i, velocity=0.4 * vel_scale)

    # Tom fill: Quick fill at the end
    if intensity == "high":
        fill_layer = pattern.add_layer("tom_fill", velocity=0.7 * vel_scale)
        fill_pattern = [12, 13, 14, 15]  # Rapid 16th note fill
        for i, pos in enumerate(fill_pattern):
            fill_layer.add_step(pos, velocity=0.7 * vel_scale - (i * 0.1))

    return pattern


# Default instance
BREAKBEAT_CHAOS = create_pattern()


# Variation: Amen-style break
def create_amen_style(bpm: int = BPM) -> Pattern:
    """Create an Amen-style break variation."""
    pattern = create_pattern(bpm=bpm, intensity="high")
    pattern.name = "Amen-Style Break"

    # Modify kick to be more Amen-like
    kick_layer = pattern.get_layer("kick")
    kick_layer.clear()
    for pos in [0, 5, 8, 11]:  # Classic Amen kick pattern
        kick_layer.add_step(pos, velocity=0.9)

    return pattern


# Variation: Two-step garage
def create_two_step(bpm: int = BPM) -> Pattern:
    """Create a two-step garage variation."""
    pattern = create_pattern(bpm=bpm, intensity="medium")
    pattern.name = "Two-Step Garage"

    # Simplify to two-step pattern
    kick_layer = pattern.get_layer("kick")
    kick_layer.clear()
    kick_layer.add_step(0, velocity=1.0)
    kick_layer.add_step(6, velocity=0.8)
    kick_layer.add_step(12, velocity=0.7)

    return pattern


if __name__ == "__main__":
    # Demo: play different intensities
    for intensity in ["low", "medium", "high"]:
        pattern = create_pattern(intensity=intensity)
        print(f"\n--- Intensity: {intensity} ---")
        pattern.play()

    # Demo: Amen-style
    amen = create_amen_style()
    print("\n--- Amen-Style ---")
    amen.play()

    # Export
    BREAKBEAT_CHAOS.export_midi("breakbeat_chaos.mid")
