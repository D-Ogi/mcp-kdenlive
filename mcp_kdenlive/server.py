"""MCP server for Kdenlive — stdio transport, FastMCP."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager

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

ATOMIC TOOLS (use when composite tools don't cover your case):
  import_media, import_media_glob, get_media_pool, create_bin_folder,
  insert_clip, append_clips, move_clip, trim_clip, split_clip, delete_clip, add_track,
  get_track_list, get_clip_info, get_project_info, save_project, load_project,
  add_transition, remove_transition,
  add_effect, remove_effect, get_clip_effects, set_clip_opacity,
  set_clip_speed,
  add_marker, delete_marker, delete_markers_by_color, get_markers,
  replace_clip, checkpoint_save, checkpoint_restore,
  add_title

RULES:
  - Kdenlive must be running (D-Bus runtime, not file-based)
  - State is text (get_timeline_summary), not screenshots
  - Frames on input, timecodes on output
  - Prefer composite tools — they handle full workflows in one call

WHEN IN DOUBT: call get_timeline_summary to see current state.
For detailed recipes: read the kdenlive://cookbook resource.
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
    titles,
)

for mod in [project, media, timeline, transitions, effects, markers, replace, checkpoints, composite, speed, titles]:
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
