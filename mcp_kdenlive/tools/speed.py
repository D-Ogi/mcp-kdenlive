"""Speed tool: change clip playback speed (slow-motion / ramp)."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def set_clip_speed(ctx: Context, clip_id: int, speed_factor: float,
                       pitch_compensate: bool = False) -> str:
        """Set clip playback speed.

        Args:
            clip_id: Timeline clip ID.
            speed_factor: Speed multiplier (0.5 = half speed, 2.0 = double).
            pitch_compensate: Keep original audio pitch.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            speed_pct = speed_factor * 100.0
            ok = resolve._dbus.set_clip_speed(clip_id, speed_pct, pitch_compensate)
            if not ok:
                return f"ERROR: Could not set speed {speed_factor}x on clip {clip_id}"
            return f"Set speed {speed_factor}x ({speed_pct:.0f}%) on clip {clip_id}"
        except Exception as e:
            return f"ERROR: {e}"
