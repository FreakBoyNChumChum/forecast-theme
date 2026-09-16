"""Open a PotreeConverter output in the PotreeDesktop Forecast installed.

Every caller already goes through ``launcher_prefs.resolve_app_root("potree")`` to find where
PotreeDesktop lives; this module is the one shared implementation of what happens next, so no
consumer keeps its own copy of the autoload-bridge/launch logic to fall out of sync by hand.

Deliberately Qt-free, like ``launcher_prefs``: nothing here needs a running QApplication.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: Files that mark a folder as PotreeConverter's output -- see ``find_cloud_file``.
CLOUD_MARKERS = ("metadata.json", "cloud.js")


def find_cloud_file(output_dir: Path) -> Path | None:
    """The first Potree-converted cloud under ``output_dir``, if one exists there.

    A folder only has one of these when PotreeConverter actually ran against it -- it is optional
    in every app that produces one, so a plain run with no converter available leaves nothing for
    this to find, same as it would with no Forecast/Potree installed at all.
    """
    for name in CLOUD_MARKERS:
        found = next(output_dir.rglob(name), None)
        if found is not None:
            return found
    return None


def setup_potree_bridge(potree_app_dir: str, cloud_file: Path) -> bool:
    """Point Potree's ``index.html`` at ``cloud_file`` on next load.

    Injects an ``autoload.js`` script tag into ``index.html`` if it is not there yet, and writes
    ``autoload.js`` to poll for the Potree viewer and load the cloud once it exists. Returns False
    if ``index.html`` is not where expected -- ``potree_app_dir`` is not really a Potree install.
    """
    app_path = Path(potree_app_dir)
    index_path = app_path / "index.html"
    autoload_js_path = app_path / "autoload.js"

    if not index_path.exists():
        return False

    content = index_path.read_text(encoding="utf-8")
    script_tag = '<script src="autoload.js"></script>'

    if script_tag not in content:
        index_path.write_text(
            content.replace("</body>", f"{script_tag}\n</body>"), encoding="utf-8")

    js_path = cloud_file.as_posix()
    autoload_js_path.write_text(
        f"""(function() {{
    var attempts = 0;
    var interval = setInterval(function() {{
        attempts++;
        if (window.Potree && window.viewer) {{
            clearInterval(interval);
            Potree.loadPointCloud("{js_path}", "Scan", function(e) {{
                viewer.scene.addPointCloud(e.pointcloud);
                viewer.fitToScreen();
            }});
        }}
        if (attempts > 100) clearInterval(interval);
    }}, 200);
}})();
""",
        encoding="utf-8",
    )
    return True


def launch_potree(potree_app_dir: str) -> None:
    """Start PotreeDesktop from its install folder.

    Prefers the desktop exe by name; falls back to the bundled Electron runtime, the shape a
    plain unpacked Potree payload takes when it has no standalone exe of its own.
    """
    base = Path(potree_app_dir)

    exe_path = next(
        (base / name for name in ("PotreeDesktop.exe", "PotreeDesktop_1.8.1_x64_windows.exe")
         if (base / name).exists()),
        None,
    )

    if exe_path is None:
        electron = base / "node_modules" / "electron" / "dist" / "electron.exe"
        if electron.exists():
            exe_path = electron

    if exe_path is None:
        raise FileNotFoundError("Potree executable not found.")

    cmd = [str(exe_path)]
    if "electron.exe" in exe_path.name.lower():
        cmd.append(str(base / "main.js"))

    subprocess.Popen(cmd, cwd=str(base))
