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

    logger.debug(
        f"EXEC {args_text}"
    )
    logger.debug(f"  duration={time.monotonic()-begin_s:0.3f}s")
    logger.debug(f"  returncode={proc.returncode}")
    logger.debug(f"  stdout: {stdout}")
    logger.debug(f"  stderr: {stderr}")

    if proc.returncode != 0:
        logger.warning(f"{args_text}: Failed: returncode={proc.returncode}")
        logger.warning(f"STDERR: {stderr}")
        logger.warning(f"STDOUT: {stdout}")
        raise ValueError(f"{args_text}:\n\nstderr: {stderr}\n\nstdout: {stdout}")

    return stdout
