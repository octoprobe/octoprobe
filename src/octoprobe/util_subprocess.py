import logging
import pathlib
import subprocess
import time

logger = logging.getLogger(__file__)


def subprocess_run(args: list[str], cwd: pathlib.Path, timeout_s: float = 10.0) -> str:
    """
    Wrappsr around 'subprocess()'
    """
    assert isinstance(args, list)
    assert isinstance(cwd, pathlib.Path)
    assert isinstance(timeout_s, float | None)

    args_text = " ".join(args)

    begin_s = time.monotonic()
    try:
        proc = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        logger.info(f"EXEC {e!r}")
        logger.exception(e)
        raise

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    def log(f) -> None:
        f(f"EXEC {args_text}")
        f(f"  duration={time.monotonic()-begin_s:0.3f}s")
        f(f"  returncode={proc.returncode}")
        f(f"  stdout: {stdout}")
        f(f"  stderr: {stderr}")

    log(logger.debug)
    if proc.returncode != 0:
        log(logger.warning)
        raise ValueError(f"EXEC failed with returncode={proc.returncode}: {args_text}")

    return stdout
