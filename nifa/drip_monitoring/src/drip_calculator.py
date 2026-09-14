"""IV Drip rate & volume monitoring calculations.

Provides accurate mathematical conversions and monitoring algorithms for:
- Converting between mL/h flow rate and drops/minute (gtt/min)
- Tracking infused and remaining volume
- Calculating remaining infusion time (ETA / Run-out time)
- Calculating flow variance against target prescription
"""

from typing import Dict, Any, Optional, Tuple


class DripCalculator:
    """Calculates IV drip rates, fluid volumes, and infusion progression."""

    @staticmethod
    def flow_rate_to_drops_per_min(flow_rate_ml_h: float, drop_factor: int = 20) -> float:
        """Convert flow rate in mL/h to drops per minute (gtt/min).

        Formula: gtt/min = (flow_rate_ml_h * drop_factor) / 60
        """
        if flow_rate_ml_h < 0:
            return 0.0
        if drop_factor <= 0:
            raise ValueError("Drop factor must be a positive integer.")
        return round((flow_rate_ml_h * drop_factor) / 60.0, 1)

    @staticmethod
    def drops_per_min_to_flow_rate(drops_per_min: float, drop_factor: int = 20) -> float:
        """Convert drops per minute (gtt/min) to flow rate in mL/h.

        Formula: mL/h = (drops_per_min * 60) / drop_factor
        """
        if drops_per_min < 0:
            return 0.0
        if drop_factor <= 0:
            raise ValueError("Drop factor must be a positive integer.")
        return round((drops_per_min * 60.0) / drop_factor, 1)

    @staticmethod
    def calculate_remaining_volume(total_volume_ml: float, infused_volume_ml: float) -> float:
        """Calculate remaining fluid volume in the IV container."""
        if total_volume_ml < 0:
            raise ValueError("Total volume must be non-negative.")
        remaining = total_volume_ml - max(0.0, infused_volume_ml)
        return round(max(0.0, remaining), 1)

    @staticmethod
    def calculate_volume_percentage(remaining_volume_ml: float, total_volume_ml: float) -> float:
        """Calculate the remaining volume as a percentage of total volume."""
        if total_volume_ml <= 0:
            return 0.0
        pct = (remaining_volume_ml / total_volume_ml) * 100.0
        return round(max(0.0, min(100.0, pct)), 1)

    @staticmethod
    def calculate_time_to_completion(
        remaining_volume_ml: float, current_flow_rate_ml_h: float
    ) -> Tuple[Optional[float], str]:
        """Calculate estimated time to completion (ETA) in hours and return a human-readable string.

        Returns:
            (hours_float, formatted_eta_str)
            e.g. (2.5, "2h 30m") or (None, "Inf (Flow Stopped)")
        """
        if remaining_volume_ml <= 0.0:
            return (0.0, "Completed")
        if current_flow_rate_ml_h <= 0.0:
            return (None, "Stopped / Occluded")

        hours_float = remaining_volume_ml / current_flow_rate_ml_h
        total_minutes = int(round(hours_float * 60))
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            formatted = f"{hours}h {minutes}m"
        else:
            formatted = f"{minutes}m"

        return (round(hours_float, 2), formatted)

    @staticmethod
    def calculate_flow_deviation(actual_flow_rate_ml_h: float, prescribed_rate_ml_h: float) -> float:
        """Calculate the percentage deviation of actual flow rate from prescribed rate.

        Positive value = faster than prescribed (over-infusion).
        Negative value = slower than prescribed (under-infusion).
        """
        if prescribed_rate_ml_h <= 0:
            return 0.0
        deviation = ((actual_flow_rate_ml_h - prescribed_rate_ml_h) / prescribed_rate_ml_h) * 100.0
        return round(deviation, 1)

    @staticmethod
    def calculate_infused_volume_delta(flow_rate_ml_h: float, elapsed_seconds: float) -> float:
        """Calculate volume infused over a duration of elapsed_seconds at given flow_rate_ml_h."""
        if flow_rate_ml_h <= 0 or elapsed_seconds <= 0:
            return 0.0
        return round(flow_rate_ml_h * (elapsed_seconds / 3600.0), 3)

    @classmethod
    def compute_infusion_summary(
        cls,
        total_volume_ml: float,
        infused_volume_ml: float,
        current_flow_rate_ml_h: float,
        prescribed_rate_ml_h: float,
        drop_factor: int = 20,
    ) -> Dict[str, Any]:
        """Produce a complete telemetry summary dictionary for dashboard display."""
        remaining_vol = cls.calculate_remaining_volume(total_volume_ml, infused_volume_ml)
        pct_remaining = cls.calculate_volume_percentage(remaining_vol, total_volume_ml)
        drops_per_min = cls.flow_rate_to_drops_per_min(current_flow_rate_ml_h, drop_factor)
        eta_hours, eta_str = cls.calculate_time_to_completion(remaining_vol, current_flow_rate_ml_h)
        flow_dev = cls.calculate_flow_deviation(current_flow_rate_ml_h, prescribed_rate_ml_h)

        return {
            "total_volume_ml": total_volume_ml,
            "infused_volume_ml": round(infused_volume_ml, 1),
            "remaining_volume_ml": remaining_vol,
            "volume_percentage": pct_remaining,
            "flow_rate_ml_h": round(current_flow_rate_ml_h, 1),
            "prescribed_rate_ml_h": prescribed_rate_ml_h,
            "drop_factor": drop_factor,
            "drops_per_min": drops_per_min,
            "eta_hours": eta_hours,
            "eta_display": eta_str,
            "flow_deviation_pct": flow_dev,
            "is_completed": remaining_vol <= 0.0,
        }
