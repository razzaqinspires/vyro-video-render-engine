from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

from .renderer import inspect_video, render, render_timeline

app = typer.Typer(no_args_is_help=True, help="VYRO Video Render Engine")


@app.command("render")
def render_command(
    source: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(..., "--output", "-o"),
    workdir: Path = typer.Option(Path("output/work"), "--workdir"),
    assets_dir: Path = typer.Option(Path("assets"), "--assets-dir"),
    preset: str = typer.Option("medium", "--preset"),
    crf: int = typer.Option(20, "--crf", min=15, max=28),
) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    if "timeline" in payload:
        payload = payload["timeline"]
    manifest = render_timeline(payload, output, workdir, assets_dir, preset=preset, crf=crf)
    print(manifest)


@app.command("render-legacy")
def render_legacy_command(
    source: Path = typer.Argument(..., exists=True, readable=True),
    output: Path = typer.Option(..., "--output", "-o"),
    workdir: Path = typer.Option(Path("output/work"), "--workdir"),
    assets_dir: Path = typer.Option(Path("assets"), "--assets-dir"),
) -> None:
    manifest = render(source, output, workdir, assets_dir)
    print(manifest)


@app.command("inspect")
def inspect(source: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    print(inspect_video(source))


if __name__ == "__main__":
    app()
