from pathlib import Path
import typer
from rich import print
from .renderer import render, inspect_video
app=typer.Typer(no_args_is_help=True,help="VYRO Video Render Engine")

@app.command()
def render_command(
    source: Path=typer.Argument(...,exists=True),
    output: Path=typer.Option(...,"--output"),
    workdir: Path=typer.Option(Path("output/work"),"--workdir"),
    assets_dir: Path|None=typer.Option(None,"--assets-dir"),
    voiceover: Path|None=typer.Option(None,"--voiceover"),
):
    manifest=render(source,output,workdir,assets_dir,voiceover)
    print(manifest)

@app.command()
def inspect(source: Path=typer.Argument(...,exists=True)):
    print(inspect_video(source))
