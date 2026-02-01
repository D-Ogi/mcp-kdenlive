"""Composition tools: list, info, move, resize, delete, list types."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def get_compositions(ctx: Context) -> str:
        """List all compositions on the timeline.

        Returns a markdown table: id | type | track_id | start | end | dur
        """
        try:
            resolve = helpers.get_resolve(ctx)
            fps = resolve.GetProjectManager().GetCurrentProject().GetFps()
            comps = resolve._dbus.get_compositions()
            if not comps:
                return "No compositions found on timeline."
            return helpers.compositions_table(comps, fps)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def get_composition_info(ctx: Context, compo_id: int) -> str:
        """Get detailed info about a specific composition.

        Args:
            compo_id: The composition's timeline ID.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            fps = resolve.GetProjectManager().GetCurrentProject().GetFps()
            info = resolve._dbus.get_composition_info(compo_id)
            if not info:
                return f"ERROR: Composition {compo_id} not found."
            pos = int(info.get("position", 0))
            dur = int(info.get("duration", 0))
            lines = [
                f"**Composition {compo_id}**",
                f"- type: {info.get('type', '?')}",
                f"- track: {info.get('trackId', '?')}",
                f"- position: {helpers.format_tc(pos, fps)} (frame {pos})",
                f"- duration: {dur} frames ({helpers.format_tc(dur, fps)})",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def move_composition(ctx: Context, compo_id: int, track_id: int, position: int) -> str:
        """Move a composition to a new track/position.

        Args:
            compo_id: The composition's timeline ID.
            track_id: Target track ID.
            position: New position in frames.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.move_composition(compo_id, track_id, position)
            if not ok:
                return f"ERROR: Could not move composition {compo_id}."
            fps = resolve.GetProjectManager().GetCurrentProject().GetFps()
            tc = helpers.format_tc(position, fps)
            return f"Moved composition {compo_id} to track {track_id} at {tc}."
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def resize_composition(ctx: Context, compo_id: int, new_duration: int,
                           from_right: bool = True) -> str:
        """Resize a composition to a new duration.

        Args:
            compo_id: The composition's timeline ID.
            new_duration: Desired duration in frames.
            from_right: If True, trims from the right edge. If False, from the left.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            result = resolve._dbus.resize_composition(compo_id, new_duration, from_right)
            if result == -1:
                return f"ERROR: Could not resize composition {compo_id}."
            return f"Resized composition {compo_id} to {result} frames."
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def delete_composition(ctx: Context, compo_id: int) -> str:
        """Delete a composition from the timeline.

        Args:
            compo_id: The composition's timeline ID.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.delete_composition(compo_id)
            if not ok:
                return f"ERROR: Could not delete composition {compo_id}."
            return f"Deleted composition {compo_id}."
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def get_composition_types(ctx: Context) -> str:
        """List all available composition/transition types.

        Returns a markdown table: id | name
        """
        try:
            resolve = helpers.get_resolve(ctx)
            types = resolve._dbus.get_composition_types()
            if not types:
                return "No composition types found."
            header = "| id | name |"
            sep = "|----|------|"
            lines = [header, sep]
            for t in types:
                tid = t.get("id", "")
                tname = t.get("name", "")
                lines.append(f"| {tid} | {tname} |")
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: {e}"
