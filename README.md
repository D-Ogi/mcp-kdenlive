# mcp-kdenlive

MCP server for Kdenlive — wraps [kdenlive-api](https://github.com/D-Ogi/kdenlive-api) for Claude Code and other LLM agents.

Gives an AI agent full NLE control over a running Kdenlive instance via D-Bus: import media, build timelines, add transitions, markers, effects, and render.

## Quick start

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "kdenlive": {
      "command": "python",
      "args": ["-m", "mcp_kdenlive"]
    }
  }
}
```

## Requirements

- Python 3.10+
- [kdenlive-api](https://github.com/D-Ogi/kdenlive-api)
- [MCP SDK](https://pypi.org/project/mcp/) (`mcp>=1.0.0`)
- Running [patched Kdenlive](https://github.com/D-Ogi/kdenlive) with D-Bus scripting API

```bash
pip install -r requirements.txt
```

## Tools

### Composite (use these first)

| Tool | Description |
|------|-------------|
| `build_timeline` | Full assembly from scene clips (import + sequence + transitions + audio + markers) |
| `replace_scene` | Swap one scene clip by number, keep position and transitions |
| `get_timeline_summary` | Text table of all clips on timeline |
| `add_transitions_batch` | Batch cross-dissolves between all clips on a track |
| `render_video` | Export timeline to video file |

### Atomic

| Domain | Tools |
|--------|-------|
| Project | `get_project_info`, `save_project`, `load_project` |
| Media | `get_media_pool`, `import_media`, `import_media_glob`, `create_bin_folder` |
| Timeline | `get_track_list`, `get_clip_info`, `insert_clip`, `append_clips`, `move_clip`, `delete_clip`, `add_track`, `trim_clip` |
| Transitions | `add_transition`, `remove_transition` |
| Markers | `get_markers`, `add_marker`, `delete_marker`, `delete_markers_by_color` |
| Replace | `replace_clip` |
| Checkpoints | `checkpoint_save`, `checkpoint_restore` |

## Related repos

- [kdenlive-api](https://github.com/D-Ogi/kdenlive-api) — DaVinci Resolve-compatible Python API
- [D-Ogi/kdenlive](https://github.com/D-Ogi/kdenlive) — Kdenlive fork with D-Bus scripting API
