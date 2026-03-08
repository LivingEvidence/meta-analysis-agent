import asyncio
import json
import logging
import subprocess
from pathlib import Path

from app.config import settings

log = logging.getLogger(__name__)


async def ensure_docker_image() -> bool:
    """Check if the Docker image exists, build if not. Returns True if available."""
    try:
        result = subprocess.run(
            ["docker", "images", settings.DOCKER_IMAGE_NAME, "--format", "{{.Repository}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if settings.DOCKER_IMAGE_NAME in result.stdout:
            log.info("Docker image %s already exists", settings.DOCKER_IMAGE_NAME)
            return True

        log.info("Building Docker image %s ...", settings.DOCKER_IMAGE_NAME)
        subprocess.run(
            ["docker", "build", "-t", settings.DOCKER_IMAGE_NAME, str(settings.DOCKER_BUILD_CONTEXT)],
            check=True,
            timeout=600,
        )
        return True
    except FileNotFoundError:
        log.warning("Docker not found on PATH")
        return False
    except subprocess.TimeoutExpired:
        log.error("Docker build timed out")
        return False
    except subprocess.CalledProcessError as e:
        log.error("Docker build failed: %s", e)
        return False


async def execute_r_analysis(
    excel_path: str,
    sheet_name: str,
    measure: str,
    data_type: str,
    full_name: str,
    output_dir: str,
) -> dict:
    """Run the R meta-analysis script in Docker and return results."""

    excel_abs = str(Path(excel_path).resolve())
    excel_dir = str(Path(excel_abs).parent)
    excel_filename = Path(excel_abs).name
    r_scripts_dir = str(settings.R_SCRIPTS_DIR.resolve())
    output_abs = str(Path(output_dir).resolve())
    Path(output_abs).mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{excel_dir}:/data/input:ro",
        "-v",
        f"{r_scripts_dir}:/scripts:ro",
        "-v",
        f"{output_abs}:/data/output",
        settings.DOCKER_IMAGE_NAME,
        "Rscript",
        "/scripts/run_pairwise_meta_analysis.R",
        "--input",
        f"/data/input/{excel_filename}",
        "--sheet",
        sheet_name,
        "--measure",
        measure,
        "--data-type",
        data_type,
        "--full-name",
        full_name,
        "--output-dir",
        "/data/output",
        "--output-format",
        "json",
    ]

    log.info("Running R analysis: sheet=%s measure=%s", sheet_name, measure)
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    # Save logs
    log_dir = Path(output_abs).parent / "logs" if "figures" in output_abs else Path(output_abs) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{sheet_name}_stdout.log").write_text(stdout.decode(errors="replace"))
    (log_dir / f"{sheet_name}_stderr.log").write_text(stderr.decode(errors="replace"))

    if process.returncode != 0:
        err_msg = stderr.decode(errors="replace")
        log.error("R analysis failed (rc=%d): %s", process.returncode, err_msg[:500])
        return {"error": err_msg, "returncode": process.returncode}

    # Read results.json produced by R
    results_path = Path(output_abs) / "results.json"
    if results_path.exists():
        return json.loads(results_path.read_text())

    # Fallback: read summary.txt
    summary_path = Path(output_abs) / "summary.txt"
    if summary_path.exists():
        return {"summary": summary_path.read_text()}

    return {"summary": stdout.decode(errors="replace")}
