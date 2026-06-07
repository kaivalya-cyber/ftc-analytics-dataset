#!/usr/bin/env python3
"""
match_replay.py — Generate an animated GIF replay of a match score timeline.
Creates images/match_replay.gif showing a bar chart race of the closest matches.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
IMAGES_DIR = Path(__file__).parent.parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)

matches = pd.read_csv(DATA_DIR / "matches.csv")

# Find closest matches (by score differential) across seasons
close_matches = matches.copy()
close_matches["abs_diff"] = (close_matches["red_score"] - close_matches["blue_score"]).abs()
best = close_matches.nsmallest(30, "abs_diff").sort_values(["season", "event_key", "match_number"])

# Build frames: cumulative average score progression
frames = []
for i in range(1, len(best) + 1):
    subset = best.iloc[:i]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"M{m['match_number']}" for _, m in subset.iterrows()],
        y=subset["red_score"].values,
        name="Red Alliance",
        marker_color="#E74C3C",
        opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        x=[f"M{m['match_number']}" for _, m in subset.iterrows()],
        y=subset["blue_score"].values,
        name="Blue Alliance",
        marker_color="#3498DB",
        opacity=0.85,
    ))
    
    fig.update_layout(
        title=f"Closest Matches — Top 30 by Score Differential<br><sup>Red vs Blue scores</sup>",
        template="plotly_dark",
        height=500,
        barmode="group",
        bargap=0.15,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", tickangle=-45),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Score"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    frames.append(fig)

# Save as static image (final frame) for README
final_path = IMAGES_DIR / "closest_matches.png"
frames[-1].write_image(str(final_path), width=1200, height=500, scale=2)
print(f"  ✓ Saved closest_matches.png ({len(best)} matches, avg diff: {best['abs_diff'].mean():.1f})")

# Try to generate animated GIF if imageio is available
try:
    import imageio
    import tempfile
    import os
    
    tmp_files = []
    for i, fig in enumerate(frames):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_files.append(tmp.name)
        tmp.close()
        fig.write_image(tmp.name, width=800, height=400, scale=1)
    
    gif_path = IMAGES_DIR / "match_replay.gif"
    with imageio.get_writer(str(gif_path), mode="I", duration=0.3, loop=0) as writer:
        for tmp in tmp_files:
            writer.append_data(imageio.imread(tmp))
            os.unlink(tmp)
    
    print(f"  ✓ Saved match_replay.gif ({len(frames)} frames)")
except ImportError:
    print("  ⓘ imageio not installed — skipping GIF generation. Install with: pip install imageio")

print("\n✅ Match replay images generated in images/")
