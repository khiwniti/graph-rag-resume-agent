#!/usr/bin/env python3
"""
Rhythm Patterns Demo

Showcase of all available patterns and how to use them.
Run this file to see the patterns in action!
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from patterns.basic_4x4 import BASIC_4X4, create_pattern as create_basic
from patterns.syncopated_groove import SYNCOPATED_GROOVE, create_pattern as create_groove
from patterns.polyrhythmic_flow import POLYRHYTHMIC_FLOW, create_pattern as create_poly
from patterns.breakbeat_chaos import BREAKBEAT_CHAOS, create_pattern as create_break


def demo_all_patterns():
    """Play through all available patterns."""
    patterns = [
        ("Basic 4x4 (Beginner)", BASIC_4X4),
        ("Syncopated Groove (Intermediate)", SYNCOPATED_GROOVE),
        ("Polyrhythmic Flow (Advanced)", POLYRHYTHMIC_FLOW),
        ("Breakbeat Chaos (Expert)", BREAKBEAT_CHAOS),
    ]

    print("🎵 RHYTHM PATTERNS DEMO 🎵")
    print("=" * 50)

    for name, pattern in patterns:
        print(f"\n{'─' * 50}")
        print(f"🎼 {name}")
        print(f"{'─' * 50}")
        pattern.play()
        print()


def demo_customization():
    """Show how to customize patterns."""
    print("\n\n🔧 CUSTOMIZATION DEMO 🔧")
    print("=" * 50)

    # Change BPM
    print("\n1. Changing BPM:")
    slow = create_basic(bpm=80)
    slow.play()

    fast = create_basic(bpm=160)
    fast.play()

    # Add swing
    print("\n2. Adding Swing:")
    groovy = create_groove(swing=0.7)
    groovy.play()

    # Change intensity
    print("\n3. Changing Intensity:")
    chill = create_break(intensity="low")
    chill.play()

    intense = create_break(intensity="high")
    intense.play()


def demo_export():
    """Show export functionality."""
    print("\n\n📁 EXPORT DEMO 📁")
    print("=" * 50)

    # Export all patterns
    BASIC_4X4.export_midi("output/basic_4x4.mid")
    SYNCOPATED_GROOVE.export_midi("output/syncopated_groove.mid")
    POLYRHYTHMIC_FLOW.export_midi("output/polyrhythmic_flow.mid")
    BREAKBEAT_CHAOS.export_midi("output/breakbeat_chaos.mid")

    print("\n✅ All patterns exported to 'output/' directory")


def main():
    """Run the demo."""
    demo_all_patterns()
    demo_customization()
    demo_export()

    print("\n\n🎉 Demo complete!")
    print("\nNext steps:")
    print("  1. Fork this repo")
    print("  2. Modify existing patterns")
    print("  3. Create your own patterns")
    print("  4. Share with the community!")


if __name__ == "__main__":
    main()
