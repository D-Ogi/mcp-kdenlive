"""Effect tools: add, remove, list effects on timeline clips."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def add_effect(ctx: Context, clip_id: int, effect_id: str,
                   params: dict[str, str] | None = None) -> str:
        """Add an effect/filter to a timeline clip with optional parameters.

        Common effects for fill-frame: "qtblend" with rect="0 0 W H 1", distort="1".

        Args:
            clip_id: Timeline clip ID.
            effect_id: MLT effect ID (e.g. "qtblend", "affine", "brightness").
            params: Optional parameter dict (key=value pairs).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.add_clip_effect(clip_id, effect_id, params)
            if not ok:
                return f"ERROR: Could not add effect '{effect_id}' to clip {clip_id}"
            param_str = ""
            if params:
                param_str = " with " + ", ".join(f"{k}={v}" for k, v in params.items())
            return f"Added effect '{effect_id}' to clip {clip_id}{param_str}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def remove_effect(ctx: Context, clip_id: int, effect_id: str) -> str:
        """Remove an effect from a timeline clip.

        Args:
            clip_id: Timeline clip ID.
            effect_id: MLT effect ID to remove (e.g. "qtblend").
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.remove_clip_effect(clip_id, effect_id)
            if not ok:
                return f"ERROR: Could not remove effect '{effect_id}' from clip {clip_id}"
            return f"Removed effect '{effect_id}' from clip {clip_id}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def get_clip_effects(ctx: Context, clip_id: int) -> str:
        """List all effects on a timeline clip.

        Args:
            clip_id: Timeline clip ID.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            effects = resolve._dbus.get_clip_effects(clip_id)
            if not effects:
                return f"Clip {clip_id}: no effects"
            return f"Clip {clip_id} effects: {effects}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def set_clip_opacity(ctx: Context, clip_id: int, opacity: float = 1.0,
                         keyframes: dict[int, float] | None = None) -> str:
        """Set clip opacity (transparency). Uses qtblend effect internally.

        Args:
            clip_id: Timeline clip ID.
            opacity: Opacity 0.0 (transparent) to 1.0 (opaque). Ignored if keyframes provided.
            keyframes: Optional dict {frame: opacity} for animated opacity.
                       Frame is relative to clip start. Example: {0: 0.0, 25: 1.0} for 1s fade-in.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            params: dict[str, str] = {}
            if keyframes:
                # MLT keyframe syntax: "frame=value;frame=value"
                kf_str = ";".join(
                    f"{f}={int(v * 100)}" for f, v in sorted(keyframes.items())
                )
                params["opacity"] = kf_str
            else:
                params["opacity"] = str(int(opacity * 100))
            ok = resolve._dbus.add_clip_effect(clip_id, "qtblend", params)
            if not ok:
                return f"ERROR: Could not set opacity on clip {clip_id}"
            if keyframes:
                return f"Set animated opacity on clip {clip_id}: {params['opacity']}"
            return f"Set opacity {opacity:.0%} on clip {clip_id}"
        except Exception as e:
            return f"ERROR: {e}"
