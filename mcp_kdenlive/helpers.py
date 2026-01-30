"""Shared helpers: context accessors, markdown formatters, timecode utils."""

from __future__ import annotations

from mcp.server.fastmcp import Context


# ---------------------------------------------------------------------------
# Context accessors
# ---------------------------------------------------------------------------

def get_resolve(ctx: Context):
    """Return the Resolve singleton stored in lifespan context."""
    return ctx.request_context.lifespan_context["resolve"]


def get_project(ctx: Context):
    """Return the current Project."""
    return get_resolve(ctx).GetProjectManager().GetCurrentProject()


def get_timeline(ctx: Context):
    """Return the current Timeline."""
    return get_project(ctx).GetCurrentTimeline()


def get_media_pool(ctx: Context):
    """Return the MediaPool of the current project."""
    return get_project(ctx).GetMediaPool()


# ---------------------------------------------------------------------------
# Timecode formatting
# ---------------------------------------------------------------------------

def format_tc(frames: int, fps: float = 25.0) -> str:
    """Convert frame number to HH:MM:SS:FF timecode string."""
    from kdenlive_api.utils import frames_to_timecode
    return frames_to_timecode(frames, fps)


def get_fps(ctx: Context) -> float:
    """Return project fps."""
    return get_project(ctx).GetFps()


# ---------------------------------------------------------------------------
# Markdown table builders
# ---------------------------------------------------------------------------

def clips_table(items: list, fps: float = 25.0, show_transition: bool = False) -> str:
    """Build a markdown table from a list of TimelineItem objects.

    Returns a string like:
        | # | clip_id | start | end | dur | filename | transition |
        |---|---------|-------|-----|-----|----------|------------|
        | 0 | 42      | ...   | ... | 125 | file.mp4 | --         |
    """
    if show_transition:
        header = "| # | clip_id | start | end | dur | filename | transition |"
        sep = "|---|---------|-------|-----|-----|----------|------------|"
    else:
        header = "| # | clip_id | start | end | dur | filename |"
        sep = "|---|---------|-------|-----|-----|----------|"

    lines = [header, sep]
    for i, item in enumerate(items):
        s = item.GetStart()
        e = item.GetEnd()
        d = item.GetDuration()
        name = item.GetName()
        row = f"| {i} | {item.clip_id} | {format_tc(s, fps)} | {format_tc(e, fps)} | {d} | {name} |"
        if show_transition:
            row = row[:-1] + " -- |"
        lines.append(row)
    return "\n".join(lines)


def media_table(items: list, fps: float = 25.0) -> str:
    """Build a markdown table from a list of MediaPoolItem objects."""
    header = "| bin_id | name | type | duration_frames | duration_tc |"
    sep = "|--------|------|------|-----------------|-------------|"
    lines = [header, sep]
    for item in items:
        props = item.GetClipProperty(None) if hasattr(item, "GetClipProperty") else {}
        bin_id = item.bin_id if hasattr(item, "bin_id") else item.GetMediaId()
        name = item.GetName()
        mtype = props.get("type", "video") if isinstance(props, dict) else "video"
        dur = item.GetDuration()
        tc = format_tc(dur, fps)
        lines.append(f"| {bin_id} | {name} | {mtype} | {dur} | {tc} |")
    return "\n".join(lines)


def markers_table(markers: dict, fps: float = 25.0) -> str:
    """Build a markdown table from Timeline.GetMarkers() result.

    markers is {frame: {color, duration, note, name, customData}}.
    """
    header = "| frame | timecode | color | label |"
    sep = "|-------|----------|-------|-------|"
    lines = [header, sep]
    for frame in sorted(markers.keys()):
        info = markers[frame]
        tc = format_tc(frame, fps)
        color = info.get("color", "")
        label = info.get("name", "") or info.get("note", "")
        lines.append(f"| {frame} | {tc} | {color} | {label} |")
    return "\n".join(lines)


def tracks_table(tracks: list) -> str:
    """Build a markdown table from GetAllTracksInfo() result."""
    header = "| track_id | type | name | clips | total_frames |"
    sep = "|----------|------|------|-------|--------------|"
    lines = [header, sep]
    for t in tracks:
        tid = t.get("id", t.get("track_id", ""))
        is_audio = t.get("audio")
        ttype = "audio" if is_audio in (True, "true") else "video"
        tname = t.get("name", "")
        nclips = t.get("clips", 0)
        total = t.get("total_frames", 0)
        lines.append(f"| {tid} | {ttype} | {tname} | {nclips} | {total} |")
    return "\n".join(lines)
