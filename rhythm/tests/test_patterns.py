"""
Tests for rhythm patterns.

These tests ensure patterns are valid and can be created/modified safely.
"""

import pytest
from patterns.core import Pattern, Step, Layer, create_step_sequence
from patterns.basic_4x4 import BASIC_4X4, create_pattern as create_basic
from patterns.syncopated_groove import SYNCOPATED_GROOVE, create_pattern as create_groove
from patterns.polyrhythmic_flow import POLYRHYTHMIC_FLOW, create_pattern as create_poly
from patterns.breakbeat_chaos import create_pattern as create_break


class TestCore:
    """Test core pattern classes."""

    def test_step_creation(self):
        """Test creating a step."""
        step = Step(position=0, velocity=1.0, duration=0.5)
        assert step.position == 0
        assert step.velocity == 1.0
        assert step.duration == 0.5

    def test_step_velocity_clamped(self):
        """Test that velocity is clamped to 0-1."""
        step1 = Step(position=0, velocity=1.5)
        step2 = Step(position=0, velocity=-0.5)
        assert step1.velocity == 1.0
        assert step2.velocity == 0.0

    def test_layer_creation(self):
        """Test creating a layer."""
        layer = Layer(name="test")
        assert layer.name == "test"
        assert len(layer.steps) == 0

    def test_pattern_creation(self):
        """Test creating a pattern."""
        pattern = Pattern(name="Test", bpm=120)
        assert pattern.name == "Test"
        assert pattern.bpm == 120

    def test_pattern_add_layer(self):
        """Test adding layers to a pattern."""
        pattern = Pattern()
        layer = pattern.add_layer("kick")
        assert len(pattern.layers) == 1
        assert layer.name == "kick"

    def test_pattern_combine(self):
        """Test combining two patterns."""
        pattern1 = Pattern(name="A", bpm=120)
        pattern1.add_layer("kick")

        pattern2 = Pattern(name="B", bpm=120)
        pattern2.add_layer("snare")

        combined = pattern1 + pattern2
        assert len(combined.layers) == 2


class TestBasic4x4:
    """Test the basic 4x4 pattern."""

    def test_pattern_exists(self):
        """Test that the basic pattern can be created."""
        pattern = create_basic()
        assert pattern is not None
        assert pattern.name == "Basic 4x4"

    def test_has_required_layers(self):
        """Test that pattern has kick, snare, and hihat."""
        pattern = BASIC_4X4
        layer_names = [l.name for l in pattern.layers]
        assert "kick" in layer_names
        assert "snare" in layer_names
        assert "hihat" in layer_names

    def test_bpm_override(self):
        """Test that BPM can be overridden."""
        pattern = create_basic(bpm=100)
        assert pattern.bpm == 100


class TestSyncopatedGroove:
    """Test the syncopated groove pattern."""

    def test_pattern_exists(self):
        """Test that the groove pattern can be created."""
        pattern = create_groove()
        assert pattern is not None

    def test_swing_applied(self):
        """Test that swing is applied."""
        pattern = create_groove(swing=0.6)
        assert pattern.swing == 0.6


class TestPolyrhythmicFlow:
    """Test the polyrhythmic flow pattern."""

    def test_pattern_exists(self):
        """Test that the poly pattern can be created."""
        pattern = create_poly()
        assert pattern is not None

    def test_complexity_levels(self):
        """Test different complexity levels."""
        for complexity in range(2, 6):
            pattern = create_poly(complexity=complexity)
            assert pattern is not None


class TestBreakbeatChaos:
    """Test the breakbeat chaos pattern."""

    def test_pattern_exists(self):
        """Test that the breakbeat pattern can be created."""
        pattern = create_break()
        assert pattern is not None

    def test_intensity_levels(self):
        """Test different intensity levels."""
        for intensity in ["low", "medium", "high"]:
            pattern = create_break(intensity=intensity)
            assert pattern is not None


class TestStepSequence:
    """Test the step sequence helper."""

    def test_create_from_string(self):
        """Test creating steps from string pattern."""
        steps = create_step_sequence("x-x-")
        assert len(steps) == 2
        assert steps[0].position == 0
        assert steps[1].position == 2

    def test_empty_string(self):
        """Test empty pattern string."""
        steps = create_step_sequence("----")
        assert len(steps) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
