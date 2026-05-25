#!/usr/bin/env python3
"""
Visualize rhythm patterns as ASCII grid.

This module provides simple ASCII visualization of rhythm patterns
for quick preview and debugging.
"""

from typing import List
from .core import Pattern, Step


def visualize_step_grid(pattern: Pattern, show_velocities: bool = False) -> str:
    """
    Create an ASCII visualization of the pattern's rhythm grid.

    Args:
        pattern: The Pattern to visualize
        show_velocities: If True, show velocity as character intensity

    Returns:
        ASCII string representation of the rhythm grid
    """
    lines = []
    total_steps = pattern.get_total_steps()

    # Header
    lines.append(f"🎵 {pattern.name}")
    lines.append(f"   BPM: {pattern.bpm} | Time: {pattern.time_signature[0]}/{pattern.time_signature[1]} | Swing: {pattern.swing:.0%}")
    lines.append("")

    # Grid visualization
    for layer in pattern.layers:
        if not layer.steps:
            continue

        # Layer name (padded)
        name = f"   {layer.name[:8]:<8}"
        line = name + " | "

        # Build the step line
        chars = []
        for i in range(total_steps):
            # Check if there's a step at this position
            step = None
            for s in layer.steps:
                if s.position == i:
                    step = s
                    break

            if step and not step.muted:
                if show_velocities and step.velocity > 0.8:
                    chars.append("█")
                elif show_velocities and step.velocity > 0.5:
                    chars.append("▓")
                elif show_velocities:
                    chars.append("░")
                else:
                    chars.append("●")
            elif step and step.muted:
                chars.append("○")
            else:
                # Check if this is a beat boundary
                if i % 4 == 0:
                    chars.append("│")
                else:
                    chars.append("─")

        # Add bar lines every 4 steps
        formatted = ""
        for i, char in enumerate(chars):
            if i > 0 and i % 4 == 0:
                formatted += " "
            formatted += char

        line += formatted
        lines.append(line)

    # Legend
    lines.append("")
    lines.append("   Legend: ● = hit, │ = beat, ─ = rest, ░/▓/█ = velocity")
    lines.append("")

    return "\n".join(lines)


def visualize_pattern_summary(patterns: List[Pattern]) -> str:
    """
    Create a summary table of multiple patterns.

    Args:
        patterns: List of patterns to summarize

    Returns:
        ASCII table string
    """
    if not patterns:
        return "No patterns provided."

    # Table header
    lines = [
        "┌──────┬─────────────────────┬──────┬────────────┬──────────────┬─────────┐",
        "│ #    │ Name                │ BPM  │ Time Sig   │ Layers       │ Difficulty │",
        "├──────┼─────────────────────┼──────┼────────────┼──────────────┼─────────┤",
    ]

    for i, pattern in enumerate(patterns, 1):
        layer_names = ", ".join(l.name for l in pattern.layers[:3])
        if len(pattern.layers) > 3:
            layer_names += f" (+{len(pattern.layers) - 3})"

        difficulty = "⭐" * getattr(pattern, 'difficulty', 1)

        name = pattern.name[:19]
        bpm = str(pattern.bpm)
        time_sig = f"{pattern.time_signature[0]}/{pattern.time_signature[1]}"

        lines.append(f"│ {i:2}   │ {name:<19} │ {bpm:>4} │ {time_sig:<10} │ {layer_names[:12]:<12} │ {difficulty:<7} │")

    lines.append("└──────┴─────────────────────┴──────┴────────────┴──────────────┴─────────┘")

    return "\n".join(lines)


def demo_visualization():
    """Demo: visualize all available patterns."""
    from .basic_4x4 import BASIC_4X4
    from .syncopated_groove import SYNCOPATED_GROOVE
    from .polyrhythmic_flow import POLYRHYTHMIC_FLOW
    from .breakbeat_chaos import BREAKBEAT_CHAOS

    patterns = [BASIC_4X4, SYNCOPATED_GROOVE, POLYRHYTHMIC_FLOW, BREAKBEAT_CHAOS]

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     RHYTHM PATTERNS - ASCII VISUALIZATION                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Summary table
    print("📊 Pattern Summary")
    print()
    print(visualize_pattern_summary(patterns))
    print()

    # Individual visualizations
    for pattern in patterns:
        print(visualize_step_grid(pattern))
        print()


if __name__ == "__main__":
    demo_visualization()
