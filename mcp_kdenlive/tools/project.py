"""Project-level tools: info, save, load, render."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def get_project_info(ctx: Context) -> str:
        """Get current project settings: name, fps, resolution, path, track counts, duration."""
        try:
            proj = helpers.get_project(ctx)
            tl = proj.GetCurrentTimeline()
            fps = proj.GetFps()
            w, h = proj.GetResolution()
            name = proj.GetName()
            path = proj.GetProjectPath()

            video_tracks = tl.GetTrackCount("video") if tl else 0
            audio_tracks = tl.GetTrackCount("audio") if tl else 0
            duration = tl.GetTotalDuration() if tl else 0
            dur_tc = helpers.format_tc(duration, fps) if tl else "00:00:00:00"

            lines = [
                f"**Project:** {name}",
                f"**Path:** {path}",
                f"**FPS:** {fps}",
                f"**Resolution:** {w}x{h}",
                f"**Video tracks:** {video_tracks}",
                f"**Audio tracks:** {audio_tracks}",
                f"**Duration:** {dur_tc} ({duration} frames)",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def save_project(ctx: Context, file_path: str = "") -> str:
        """Save the current project. If file_path is given, does Save As.

        Args:
            file_path: Optional path for Save As. Empty string saves in place.
        """
        try:
            proj = helpers.get_project(ctx)
            if file_path:
                ok = proj.SaveAs(file_path)
                return f"Saved to {file_path}" if ok else "ERROR: SaveAs failed"
            else:
                ok = proj.Save()
                return f"Saved to {proj.GetProjectPath()}" if ok else "ERROR: Save failed"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def render_video(ctx: Context, output_path: str = "") -> str:
        """Start rendering the timeline to a video file.

        Args:
            output_path: Output file path. If empty, uses project default.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            if output_path:
                resolve._dbus.render(output_path)
            else:
                proj = helpers.get_project(ctx)
                proj.StartRendering()
            return "Render started" + (f" -> {output_path}" if output_path else "")
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def load_project(ctx: Context, file_path: str) -> str:
        """Load a Kdenlive project file.

        Args:
            file_path: Absolute path to .kdenlive file.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            pm = resolve.GetProjectManager()
            proj = pm.LoadProject(file_path)
            if proj is None:
                return f"ERROR: Could not load {file_path}"
            fps = proj.GetFps()
            w, h = proj.GetResolution()
            name = proj.GetName()
            return f"Loaded '{name}' ({fps}fps, {w}x{h})"
        except Exception as e:
            return f"ERROR: {e}"
