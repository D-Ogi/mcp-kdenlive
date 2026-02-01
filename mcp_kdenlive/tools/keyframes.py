"""Effect keyframe tools: get, add, remove, update keyframes on clip effects."""

from __future__ import annotations

from mcp.server.fastmcp import Context


# Keyframe type name → integer mapping for D-Bus transport
_TYPE_MAP = {
    "linear": 0,
    "discrete": 1,
    "smooth": 3,       # smooth_natural in MLT
    "bounce_in": 4,
    "bounce_out": 5,
    "cubic_in": 6,
    "cubic_out": 7,
    "exponential_in": 8,
    "exponential_out": 9,
    "circular_in": 10,
    "circular_out": 11,
    "elastic_in": 12,
    "elastic_out": 13,
}


def register(mcp, helpers):

    @mcp.tool()
    def get_effect_keyframes(ctx: Context, clip_id: int,
                             effect_index: int = 0) -> str:
        """Get all keyframes for an effect on a timeline clip.

        Args:
            clip_id: Timeline clip ID.
            effect_index: 0-based index of the effect in the stack (default 0 = first effect).

        Returns a markdown table: frame | type | value
        """
        try:
            resolve = helpers.get_resolve(ctx)
            fps = resolve.GetProjectManager().GetCurrentProject().GetFps()
            kfs = resolve._dbus.get_effect_keyframes(clip_id, effect_index)
            if not kfs:
                return f"No keyframes on clip {clip_id} effect #{effect_index} (effect may not exist or has no keyframes)."
            header = "| frame | timecode | type | value |"
            sep = "|-------|----------|------|-------|"
            lines = [header, sep]
            for kf in kfs:
                frame = kf.get("frame", "")
                kf_type = kf.get("type", "")
                value = kf.get("value", "")
                tc = helpers.format_tc(int(frame), fps) if frame != "" else ""
                lines.append(f"| {frame} | {tc} | {kf_type} | {value} |")
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def add_effect_keyframe(ctx: Context, clip_id: int,
                            frame: int, value: float = 0.0,
                            effect_index: int = 0,
                            keyframe_type: str = "linear") -> str:
        """Add a keyframe to an effect on a timeline clip.

        Args:
            clip_id: Timeline clip ID.
            frame: Frame position (relative to clip start in the source).
            value: Normalized value 0.0–1.0 (maps to the effect's primary parameter range).
            effect_index: 0-based index of the effect in the stack (default 0).
            keyframe_type: Interpolation type: "linear", "discrete", "smooth",
                "bounce_in", "bounce_out", "cubic_in", "cubic_out",
                "exponential_in", "exponential_out", "circular_in",
                "circular_out", "elastic_in", "elastic_out".
        """
        try:
            resolve = helpers.get_resolve(ctx)
            kf_type_int = _TYPE_MAP.get(keyframe_type, -1)
            ok = resolve._dbus.add_effect_keyframe(
                clip_id, effect_index, frame, value, kf_type_int)
            if not ok:
                return f"ERROR: Could not add keyframe at frame {frame} on clip {clip_id} effect #{effect_index}"
            return f"Added {keyframe_type} keyframe at frame {frame} (value={value:.3f}) on clip {clip_id} effect #{effect_index}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def remove_effect_keyframe(ctx: Context, clip_id: int,
                               frame: int,
                               effect_index: int = 0) -> str:
        """Remove a keyframe from an effect on a timeline clip.

        Args:
            clip_id: Timeline clip ID.
            frame: Frame position of the keyframe to remove.
            effect_index: 0-based index of the effect in the stack (default 0).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.remove_effect_keyframe(clip_id, effect_index, frame)
            if not ok:
                return f"ERROR: Could not remove keyframe at frame {frame} on clip {clip_id} effect #{effect_index}"
            return f"Removed keyframe at frame {frame} from clip {clip_id} effect #{effect_index}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def update_effect_keyframe(ctx: Context, clip_id: int,
                               old_frame: int, new_frame: int,
                               value: float = -1.0,
                               effect_index: int = 0) -> str:
        """Move a keyframe and/or update its value.

        Args:
            clip_id: Timeline clip ID.
            old_frame: Current frame position of the keyframe.
            new_frame: New frame position (same as old_frame to only update value).
            value: New normalized value 0.0–1.0 (-1 to keep existing value).
            effect_index: 0-based index of the effect in the stack (default 0).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.update_effect_keyframe(
                clip_id, effect_index, old_frame, new_frame, value)
            if not ok:
                return f"ERROR: Could not update keyframe at frame {old_frame} on clip {clip_id} effect #{effect_index}"
            parts = []
            if old_frame != new_frame:
                parts.append(f"moved {old_frame}→{new_frame}")
            if value >= 0:
                parts.append(f"value={value:.3f}")
            detail = ", ".join(parts) if parts else "no changes"
            return f"Updated keyframe on clip {clip_id} effect #{effect_index}: {detail}"
        except Exception as e:
            return f"ERROR: {e}"
