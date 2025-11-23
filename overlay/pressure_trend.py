"""
Barometric pressure trend calculator for fishing report overlay.
Analyzes pressure changes to determine fishing conditions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PressureTrend:
    """Barometric pressure trend data for fishing."""
    current_pressure: float  # Current pressure in inHg
    trend: str  # "Rising", "Falling", "Steady"
    change_rate: float  # Change in inHg over analysis period
    fishing_rating: str  # "Excellent", "Good", "Fair", "Poor"
    trend_arrow: str  # "↑", "↓", "→" for display


def calculate_pressure_trend(
    current_pressure: Optional[float],
    previous_pressure: Optional[float] = None,
    mb_to_inhg: bool = False
) -> PressureTrend:
    """
    Calculate barometric pressure trend and fishing rating.
    
    Fish behavior patterns:
    - Falling pressure (>0.02 inHg drop): EXCELLENT - Fish feed heavily before storm
    - Steady pressure: GOOD - Normal feeding patterns
    - Rising pressure (>0.02 inHg rise): FAIR - Fish less active
    - High stable pressure (>30.20 inHg): POOR - Fish often inactive
    
    Args:
        current_pressure: Current barometric pressure
        previous_pressure: Previous pressure reading (ideally 3 hours prior)
        mb_to_inhg: If True, convert from millibars to inHg
    
    Returns:
        PressureTrend with analysis results
    """
    # Handle missing data
    if current_pressure is None:
        return PressureTrend(
            current_pressure=0.0,
            trend="Unknown",
            change_rate=0.0,
            fishing_rating="Unknown",
            trend_arrow="?"
        )
    
    # Convert from millibars to inHg if needed
    if mb_to_inhg:
        current_pressure = current_pressure * 0.02953
        if previous_pressure is not None:
            previous_pressure = previous_pressure * 0.02953
    
    # If no previous pressure, analyze current pressure only
    if previous_pressure is None:
        return _analyze_current_pressure(current_pressure)
    
    # Calculate pressure change
    change = current_pressure - previous_pressure
    
    # Determine trend (>0.02 inHg change is significant)
    if change < -0.02:
        trend = "Falling"
        trend_arrow = "↓"
        fishing_rating = "Excellent"  # Fish feed heavily before weather change
    elif change > 0.02:
        trend = "Rising"
        trend_arrow = "↑"
        # Rising after storm can be good, high stable is poor
        if current_pressure > 30.20:
            fishing_rating = "Fair"
        else:
            fishing_rating = "Good"
    else:
        trend = "Steady"
        trend_arrow = "→"
        # Steady pressure - check if it's high or normal
        if current_pressure > 30.20:
            fishing_rating = "Fair"
        else:
            fishing_rating = "Good"
    
    return PressureTrend(
        current_pressure=current_pressure,
        trend=trend,
        change_rate=change,
        fishing_rating=fishing_rating,
        trend_arrow=trend_arrow
    )


def _analyze_current_pressure(pressure: float) -> PressureTrend:
    """
    Analyze fishing conditions based on current pressure alone.
    
    Args:
        pressure: Current pressure in inHg
    
    Returns:
        PressureTrend with analysis
    """
    # Pressure ranges for fishing (inHg):
    # Low: <29.80 (storm approaching - excellent fishing before it hits)
    # Normal: 29.80-30.20 (good fishing)
    # High: >30.20 (fair to poor fishing)
    
    if pressure < 29.80:
        # Low pressure - likely storm approaching
        trend = "Low"
        fishing_rating = "Good"  # Assuming it was higher and falling
        trend_arrow = "↓"
    elif pressure > 30.20:
        # High pressure - stable weather
        trend = "High"
        fishing_rating = "Fair"
        trend_arrow = "↑"
    else:
        # Normal pressure range
        trend = "Steady"
        fishing_rating = "Good"
        trend_arrow = "→"
    
    return PressureTrend(
        current_pressure=pressure,
        trend=trend,
        change_rate=0.0,
        fishing_rating=fishing_rating,
        trend_arrow=trend_arrow
    )


def format_pressure(pressure: float, units: str = "imperial") -> str:
    """
    Format pressure for display.
    
    Args:
        pressure: Pressure value
        units: 'imperial' (inHg) or 'metric' (mb)
    
    Returns:
        Formatted pressure string
    """
    if units == "metric":
        # Convert inHg to millibars if needed
        if pressure < 100:  # Assume it's in inHg
            pressure = pressure / 0.02953
        return f"{pressure:.0f} mb"
    else:
        # Imperial (inHg)
        if pressure > 100:  # Assume it's in millibars
            pressure = pressure * 0.02953
        return f"{pressure:.2f} inHg"


__all__ = [
    "PressureTrend",
    "calculate_pressure_trend",
    "format_pressure",
]

