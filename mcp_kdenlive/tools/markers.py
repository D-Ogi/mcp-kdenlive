"""Marker tools: add, delete, list, delete by color."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def get_markers(ctx: Context) -> str:
        """List all timeline markers/guides.

        Returns a markdown table: frame | timecode | color | label
        """
        try:
            tl = helpers.get_timeline(ctx)
            fps = helpers.get_fps(ctx)
            markers = tl.GetMarkers()
            if not markers:
                return "No markers on timeline."
            return helpers.markers_table(markers, fps)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def add_marker(ctx: Context, frame: int, label: str, color: str = "Purple", note: str = "") -> str:
        """Add a marker/guide on the timeline.

        Args:
            frame: Frame position.
            label: Marker name/label.
            color: Color name (Purple, Blue, Cyan, Green, Yellow, Orange, Red).
            note: Optional note text.
        """
        try:
            tl = helpers.get_timeline(ctx)
            fps = helpers.get_fps(ctx)
            ok = tl.AddMarker(frame, color, label, note)
            if not ok:
                return f"ERROR: Could not add marker at frame {frame}"
            tc = helpers.format_tc(frame, fps)
            return f"Added marker '{label}' at {tc} (frame {frame})"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def delete_marker(ctx: Context, frame: int) -> str:
        """Delete a marker at a specific frame.

        Args:
            frame: Frame position of the marker to delete.
        """
        try:
            tl = helpers.get_timeline(ctx)
            ok = tl.DeleteMarker(frame)
            if not ok:
                return f"ERROR: No marker at frame {frame}"
            return f"Deleted marker at frame {frame}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def delete_markers_by_color(ctx: Context, color: str) -> str:
        """Delete all markers of a given color.

        Args:
            color: Color name (Purple, Blue, Cyan, Green, Yellow, Orange, Red).
        """
        try:
            tl = helpers.get_timeline(ctx)
            ok = tl.DeleteMarkersByColor(color)
            if not ok:
                return f"ERROR: Could not delete markers with color '{color}'"
            return f"Deleted all '{color}' markers"
        except Exception as e:
            return f"ERROR: {e}"
