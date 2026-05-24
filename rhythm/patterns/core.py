"""
Core rhythm primitives for building patterns.

This module provides the foundational classes that all patterns build upon.
Fork this file to create your own custom pattern types!
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import math


@dataclass
class Step:
    """A single step in a rhythm pattern.

    Attributes:
        position: Position in the sequence (0-indexed)
        velocity: Note velocity (0.0 - 1.0)
        duration: Duration as fraction of beat (default 0.5 = 8th note)
        muted: Whether the step is muted
    """
    position: int
    velocity: float = 1.0
    duration: float = 0.5
    muted: bool = False

    def __post_init__(self):
        self.velocity = max(0.0, min(1.0, self.velocity))
        self.duration = max(0.1, self.duration)


@dataclass
class Layer:
    """A single instrument layer in a pattern.

    Attributes:
        name: Instrument name (e.g., "kick", "snare")
        steps: List of Step objects
        velocity: Overall velocity multiplier
    """
    name: str
    steps: List[Step] = field(default_factory=list)
    velocity: float = 1.0

    def add_step(self, position: int, velocity: float = 1.0, duration: float = 0.5):
        """Add a step to this layer."""
        self.steps.append(Step(position, velocity, duration))
        # Keep steps sorted by position
        self.steps.sort(key=lambda s: s.position)

    def clear(self):
        """Remove all steps from this layer."""
        self.steps = []


@dataclass
class Pattern:
    """A complete rhythm pattern.

    Attributes:
        name: Pattern name
        bpm: Beats per minute
        time_signature: Tuple of (beats_per_bar, beat_value)
        layers: List of instrument layers
        swing: Swing amount (0.0 - 1.0)
    """
    name: str = "Untitled"
    bpm: int = 120
    time_signature: tuple = (4, 4)
    layers: List[Layer] = field(default_factory=list)
    swing: float = 0.0

    def add_layer(self, name: str, steps: Optional[List[Step]] = None, velocity: float = 1.0) -> Layer:
        """Add a new instrument layer to the pattern."""
        layer = Layer(name=name, steps=steps or [], velocity=velocity)
        self.layers.append(layer)
        return layer

    def get_layer(self, name: str) -> Optional[Layer]:
        """Get a layer by name."""
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def remove_layer(self, name: str) -> bool:
        """Remove a layer by name."""
        for i, layer in enumerate(self.layers):
            if layer.name == name:
                del self.layers[i]
                return True
        return False

    def get_total_steps(self) -> int:
        """Get total number of steps based on time signature."""
        beats, beat_value = self.time_signature
        # Assuming 16th notes as finest resolution
        return beats * 4

    def apply_swing(self, amount: float):
        """Apply swing to the pattern.

        Args:
            amount: Swing amount (0.0 = no swing, 1.0 = maximum swing)
        """
        self.swing = max(0.0, min(1.0, amount))

    def quantize(self, resolution: int = 16):
        """Quantize all steps to the given resolution.

        Args:
            resolution: Steps per beat (e.g., 16 = 16th notes)
        """
        total_steps = self.get_total_steps()
        for layer in self.layers:
            for step in layer.steps:
                # Snap to nearest grid position
                step.position = round(step.position * resolution / total_steps) * total_steps // resolution

    def play(self, loop: bool = False, bars: int = 1):
        """Play the pattern (placeholder - requires audio backend)."""
        print(f"🎵 Playing '{self.name}' at {self.bpm} BPM")
        print(f"   Time signature: {self.time_signature[0]}/{self.time_signature[1]}")
        print(f"   Layers: {', '.join(l.name for l in self.layers)}")
        print(f"   Swing: {self.swing * 100:.0f}%")
        if loop:
            print(f"   Looping for {bars} bar(s)...")

    def export_midi(self, filename: str):
        """Export pattern to MIDI file (placeholder)."""
        print(f"📁 Exporting '{self.name}' to {filename}")

    def __add__(self, other: 'Pattern') -> 'Pattern':
        """Combine two patterns (layers are merged)."""
        combined = Pattern(
            name=f"{self.name} + {other.name}",
            bpm=max(self.bpm, other.bpm),
            time_signature=self.time_signature,
            layers=self.layers + other.layers
        )
        return combined


def create_step_sequence(pattern_str: str) -> List[Step]:
    """Create steps from a simple string pattern.

    Args:
        pattern_str: String like "x-x-x-x-" where x=play, -=rest

    Returns:
        List of Step objects
    """
    steps = []
    for i, char in enumerate(pattern_str):
        if char.lower() == 'x':
            steps.append(Step(position=i))
    return steps


# Common rhythm primitives
KICK_4X4 = create_step_sequence("x---x---x---x---")
SNARE_BACKBEAT = create_step_sequence("----x-------x---")
HIHAT_8TH = create_step_sequence("x-x-x-x-x-x-x-x-")
HIHAT_16TH = create_step_sequence("x-x-x-x-x-x-x-x-")
