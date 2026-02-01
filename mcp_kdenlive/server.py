"""MCP server for Kdenlive — stdio transport, FastMCP."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure kdenlive_api is importable (sibling repo in workspace)
_api_dir = str(Path(__file__).resolve().parents[2] / "kdenlive-api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Instructions — injected into agent context at MCP handshake (~200 tokens)
# ---------------------------------------------------------------------------
INSTRUCTIONS = """\
Kdenlive MCP gives you full NLE control over a running Kdenlive instance via D-Bus.

MENTAL MODEL — identical to DaVinci Resolve API:
  Resolve → ProjectManager → Project → MediaPool → Timeline → TimelineItem

COMPOSITE TOOLS (use these first):
  build_timeline    — full assembly from scene clips (import + sequence + transitions + audio + markers)
  replace_scene     — swap one scene clip by number, keep position and transitions
  detect_scenes     — FFmpeg scene detection on a bin clip, returns cut timestamps
  get_timeline_summary — text table of all clips on timeline (~20 tokens/row)
  add_transitions_batch — batch cross-dissolves between all clips on a track
  render_video      — export timeline to video file

PREVIEW TOOLS (visual inspection — returns JPEG file paths):
  render_frame        — composited timeline thumbnail at a given frame
  render_bin_frame    — single frame from a media pool clip
  render_contact_sheet — grid of evenly-spaced frames from a bin clip (requires Pillow)
  render_crop         — 1:1 pixel crop of a timeline frame for QC (requires Pillow)

ATOMIC TOOLS (use when composite tools don't cover your case):
  import_media, import_media_glob, get_media_pool, create_bin_folder,
  insert_clip, append_clips, move_clip, trim_clip, split_clip, slip_clip, delete_clip, add_track,
  get_track_list, get_clip_info, get_project_info, save_project, load_project,
  add_transition, remove_transition,
  add_effect, remove_effect, get_clip_effects, set_clip_opacity,
  get_effect_keyframes, add_effect_keyframe, remove_effect_keyframe, update_effect_keyframe,
  set_clip_speed,
  set_clip_volume, get_clip_volume, set_audio_fade, set_track_mute, get_track_mute, get_audio_levels,
  add_marker, delete_marker, delete_markers_by_color, get_markers,
  add_clip_marker, get_clip_markers, delete_clip_marker, delete_clip_markers_by_color,
  replace_clip, relink_clip,
  checkpoint_save, checkpoint_restore, undo, redo, undo_status,
  get_zone, set_zone, set_zone_in, set_zone_out, extract_zone,
  get_sequences, get_active_sequence, set_active_sequence,
  add_title,
  get_compositions, get_composition_info, move_composition, resize_composition,
  delete_composition, get_composition_types,
  get_clip_proxy_status, set_clip_proxy, delete_clip_proxy, rebuild_clip_proxy,
  group_clips, ungroup_clips, get_group_info, remove_from_group,
  get_subtitles, add_subtitle, edit_subtitle, delete_subtitle, export_subtitles,
  get_subtitle_styles, set_subtitle_style, delete_subtitle_style, set_subtitle_style_name,
  get_selection, set_selection, add_to_selection, clear_selection, select_all, select_current_track, select_items_in_range

RULES:
  - Kdenlive must be running (D-Bus runtime, not file-based)
  - State is text (get_timeline_summary) AND visual (preview tools)
  - Frames on input, timecodes on output
  - Prefer composite tools — they handle full workflows in one call
  - After replace_scene or build_timeline: ALWAYS render_frame to visually verify the result
  - When evaluating clips: use render_bin_frame or render_contact_sheet before deciding

WHEN IN DOUBT: call get_timeline_summary to see current state.
For detailed recipes and preview workflow: read the kdenlive://cookbook resource.
"""


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Create the Resolve singleton once at startup."""
    from kdenlive_api import Resolve

    resolve = Resolve()
    yield {"resolve": resolve}


mcp = FastMCP("kdenlive", instructions=INSTRUCTIONS, lifespan=lifespan)

# ---------------------------------------------------------------------------
# Register tool modules (atomic + composite)
# ---------------------------------------------------------------------------
from mcp_kdenlive import helpers
from mcp_kdenlive.tools import (
    project,
    media,
    timeline,
    transitions,
    effects,
    markers,
    replace,
    checkpoints,
    composite,
    speed,
    audio,
    titles,
    preview,
    subtitles,
    keyframes,
    compositions,
    zones,
    sequences,
    proxy,
    groups,
    selection,
)

for mod in [project, media, timeline, transitions, effects, markers, replace, checkpoints, composite, speed, audio, titles, preview, subtitles, keyframes, compositions, zones, sequences, proxy, groups, selection]:
    mod.register(mcp, helpers)

# ---------------------------------------------------------------------------
# Register prompts (user-facing slash commands)
# ---------------------------------------------------------------------------
from mcp_kdenlive import prompts

prompts.register(mcp)

# ---------------------------------------------------------------------------
# Register resources (on-demand context)
# ---------------------------------------------------------------------------
from mcp_kdenlive import resources

resources.register(mcp)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
