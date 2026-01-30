"""MCP Resources — on-demand context the agent can read."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

COOKBOOK = """\
# Kdenlive MCP Cookbook

## Workflow: Full Timeline Assembly

1. Call `build_timeline(video_dir, pattern, audio_path, transition_frames)`
   - Imports all matching clips, sequences them, adds transitions + markers + audio
   - Returns clip table with timecodes
2. Verify with `get_timeline_summary()`
3. Fix issues with atomic tools: `insert_clip`, `move_clip`, `trim_clip`, `delete_clip`
4. Save with `save_project()`

## Workflow: Replace a Scene

1. Call `replace_scene(scene_number, new_file)`
   - Imports new clip, swaps it in at the same position/duration
2. Verify with `get_timeline_summary()`
3. Re-add transitions if needed: `add_transition(clip_a, clip_b, 13)`

## Workflow: Add Transitions

- Single: `add_transition(clip_id_a, clip_id_b, duration)`
- All clips on a track: `add_transitions_batch(track_id, duration)`
- Remove: `remove_transition(clip_id)`

## Workflow: Markers

- Add: `add_marker(frame, label, color, note)`
- List: `get_markers()`
- Delete one: `delete_marker(frame)`
- Delete by color: `delete_markers_by_color(color)`
- Colors: Purple, Blue, Cyan, Green, Yellow, Orange, Red

## Workflow: Checkpoints (Undo)

1. Before risky operations: `checkpoint_save(label)`
2. If something goes wrong: `checkpoint_restore(label)`
3. Checkpoints are saved as copies of the .kdenlive project file

## ID System

- **bin_id** (str): identifies a clip in the media pool (bin)
- **clip_id** (int): identifies a clip instance on the timeline
- A single media pool clip can appear multiple times on the timeline with different clip_ids
- Use `get_media_pool()` to see bin_ids, `get_timeline_summary()` to see clip_ids

## Units

- **Input**: always frame numbers (integers)
- **Output**: timecodes (HH:MM:SS:FF) + frame numbers where useful
- Project FPS: typically 25fps (use `get_project_info()` to confirm)
- 13 frames @ 25fps = 0.52s (standard transition duration)
- 125 frames @ 25fps = 5.00s (standard scene duration)

## Track Indexing

- Track IDs are integers assigned by Kdenlive
- Use `get_track_list()` to discover track IDs
- `GetItemListInTrack` uses 1-based indexing (like DaVinci Resolve)

## Error Handling

- All tools return "ERROR: ..." on failure (not exceptions)
- Check for "ERROR" prefix in tool output before proceeding
- Common errors: clip not found, track not found, file not importable

## Token Budget

- `get_timeline_summary` for 38 clips: ~750 tokens
- `get_media_pool` for 80 clips: ~1200 tokens
- `build_timeline` full assembly: ~500 tokens output
- Prefer composite tools (1 call) over atomic tools (N calls)
"""


def register(mcp: FastMCP):

    @mcp.resource("kdenlive://cookbook")
    def cookbook() -> str:
        """Full workflow cookbook for Kdenlive MCP — recipes, ID system, units, error handling."""
        return COOKBOOK
