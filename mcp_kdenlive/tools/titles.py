"""MCP tool: add_title — create title card clips on the timeline."""

from __future__ import annotations

from mcp.server.fastmcp import Context

# Minimal kdenlivetitle XML template
TITLE_XML_TEMPLATE = """\
<kdenlivetitle width="{w}" height="{h}" LC_NUMERIC="C">
 <item type="QGraphicsTextItem" z-index="0">
  <position x="{x}" y="{y}"/>
  <content
    font="{font}" font-size="{font_size}" font-weight="{font_weight}"
    font-color="{color}" alignment="{alignment}"
    text="{text}"/>
 </item>
 {bg_item}
</kdenlivetitle>"""

BG_RECT = (
    '<item type="QGraphicsRectItem" z-index="-1">'
    '<content rect="0,0,{w},{h}" brushcolor="{bg_color}"/></item>'
)


def register(mcp, helpers):
    @mcp.tool()
    def add_title(
        ctx: Context,
        text: str,
        track_id: int,
        position: int,
        duration: int,
        style: dict | None = None,
    ) -> str:
        """Create a title card and place it on the timeline.

        Generates a kdenlivetitle clip (text overlay), adds it to the
        media pool, and inserts it on the specified track.

        Args:
            text: Title text (supports newlines via \\n).
            track_id: Target video track ID.
            position: Start position in frames.
            duration: Duration in frames.
            style: Optional dict with keys: font, font_size, font_weight,
                   color, bg_color, alignment (0=left,1=center,2=right),
                   position_y (top/center/bottom).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            project = helpers.get_project(ctx)
            pool = helpers.get_media_pool(ctx)
            tl = helpers.get_timeline(ctx)
            fps = helpers.get_fps(ctx)
            dbus = resolve._dbus

            # Project resolution
            w = dbus.get_project_resolution_width()
            h = dbus.get_project_resolution_height()

            # Style defaults
            s = {
                "font": "Sans Serif",
                "font_size": "80",
                "font_weight": "700",
                "color": "#ffffff",
                "bg_color": "",
                "alignment": "1",       # center
                "position_y": "center",  # top / center / bottom
            }
            if style:
                s.update({k: str(v) for k, v in style.items()})

            # Vertical position
            y_map = {
                "top": int(h) // 6,
                "center": int(h) // 2 - 40,
                "bottom": int(h) * 3 // 4,
            }
            y = y_map.get(s["position_y"], y_map["center"])
            x = 0  # alignment handles horizontal

            # Background rect (optional)
            bg_item = ""
            if s["bg_color"]:
                bg_item = BG_RECT.format(w=w, h=h, bg_color=s["bg_color"])

            # Escape XML special chars in text
            import html
            safe_text = html.escape(text)

            title_xml = TITLE_XML_TEMPLATE.format(
                w=w, h=h, x=x, y=y,
                font=s["font"], font_size=s["font_size"],
                font_weight=s["font_weight"], color=s["color"],
                alignment=s["alignment"], text=safe_text,
                bg_item=bg_item,
            )

            # Create title clip in bin
            clip_name = text[:30].replace("\n", " ")
            bin_id = dbus.create_title_clip(title_xml, duration, clip_name)
            if not bin_id or bin_id == "-1":
                return "ERROR: Failed to create title clip in bin"

            import time
            time.sleep(0.3)  # D-Bus async settle

            # Insert on timeline
            clip_id = dbus.insert_clip(bin_id, track_id, position)
            if clip_id < 0:
                return f"ERROR: Title created (bin {bin_id}) but insert failed"

            tc_start = helpers.format_tc(position, fps)
            tc_end = helpers.format_tc(position + duration, fps)
            return (
                f"Title '{clip_name}' created.\n"
                f"- Bin ID: {bin_id}\n"
                f"- Timeline clip ID: {clip_id}\n"
                f"- Position: {tc_start} → {tc_end} ({duration} frames)\n"
                f"- Track: {track_id}"
            )
        except Exception as e:
            return f"ERROR: {e}"
