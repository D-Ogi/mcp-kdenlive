"""Sequence tools: list, get active, switch sequences (multi-timeline)."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def get_sequences(ctx: Context) -> str:
        """List all sequences (timelines) in the project.

        Returns a markdown table: uuid | name | duration | tracks | active
        """
        try:
            resolve = helpers.get_resolve(ctx)
            fps = resolve.GetProjectManager().GetCurrentProject().GetFps()
            seqs = resolve._dbus.get_sequences()
            if not seqs:
                return "No sequences found."
            header = "| uuid | name | duration | tracks | active |"
            sep = "|------|------|----------|--------|--------|"
            lines = [header, sep]
            for s in seqs:
                uuid = s.get("uuid", "")
                name = s.get("name", "")
                dur = int(s.get("duration", 0))
                dur_tc = helpers.format_tc(dur, fps)
                tracks = s.get("tracks", "")
                active_raw = s.get("active", "")
                active = "yes" if str(active_raw).lower() in ("true", "1") else "no"
                lines.append(f"| {uuid} | {name} | {dur_tc} ({dur}f) | {tracks} | {active} |")
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def get_active_sequence(ctx: Context) -> str:
        """Get info about the currently active sequence.

        Returns the active sequence's UUID, name, duration, and track count.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            fps = resolve.GetProjectManager().GetCurrentProject().GetFps()
            seq = resolve._dbus.get_active_sequence()
            if not seq:
                return "No active sequence."
            uuid = seq.get("uuid", "")
            name = seq.get("name", "")
            dur = int(seq.get("duration", 0))
            dur_tc = helpers.format_tc(dur, fps)
            tracks = seq.get("tracks", "")
            return f"Active sequence: '{name}' (uuid={uuid}, duration={dur_tc} / {dur}f, {tracks} tracks)"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def set_active_sequence(ctx: Context, uuid: str) -> str:
        """Switch to a different sequence (timeline) by UUID.

        Args:
            uuid: Sequence UUID (from get_sequences).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.set_active_sequence(uuid)
            if not ok:
                return f"ERROR: Could not switch to sequence '{uuid}' (not found or failed to open)"
            return f"Switched to sequence '{uuid}'"
        except Exception as e:
            return f"ERROR: {e}"
