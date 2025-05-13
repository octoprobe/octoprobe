from __future__ import annotations

import logging
import pathlib
import subprocess
import time

logger = logging.getLogger(__file__)


class SubprocessExitCodeException(Exception):
    pass


def subprocess_run(
    args: list[str],
    cwd: pathlib.Path,
    env: dict[str, str] | None = None,
    logfile: pathlib.Path | None = None,
    timeout_s: float = 10.0,
    success_returncodes: list[int] | None = None,
) -> None:
    """
    Wrappsr around 'subprocess()'
    """
    assert isinstance(args, list)
    assert isinstance(cwd, pathlib.Path)
    assert isinstance(env, dict | None)
    assert isinstance(logfile, pathlib.Path | None)
    assert isinstance(timeout_s, float | None)
    assert isinstance(success_returncodes, list | None)
    if success_returncodes is None:
        success_returncodes = [0]

    if env is not None:
        for key, value in env.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    args_text = " ".join(args)

    begin_s = time.monotonic()
    try:
        if logfile is not None:
            logger.info(f"EXEC {args_text}")
            logger.info(f"EXEC     stdout: {logfile}")
            logfile.parent.mkdir(parents=True, exist_ok=True)
            with logfile.open("w") as f:
                f.write(f"{' '.join(args)}\n\n\n")
                f.flush()
                proc = subprocess.run(
                    # Common args
                    args=args,
                    check=False,
                    text=True,
                    cwd=str(cwd),
                    env=env,
                    timeout=timeout_s,
                    # Specific args
                    stdout=f,
                    stderr=subprocess.STDOUT,
                )
                f.write(f"\n\nreturncode={proc.returncode}\n")
                f.write(f"duration={time.monotonic() - begin_s:0.3f}s\n")
        else:
            proc = subprocess.run(
                # Common args
                args=args,
                check=False,
                text=True,
                cwd=str(cwd),
                env=env,
                timeout=timeout_s,
                # Specific args
                capture_output=True,
            )
    except subprocess.TimeoutExpired as e:
        logger.info(f"EXEC {e!r}")
        # logger.exception(e)
        raise

    def log(f) -> None:
        f(f"EXEC {args_text}")
        f(f"  returncode: {proc.returncode}")
        f(f"  success_codes: {success_returncodes}")
        f(f"  duration: {time.monotonic() - begin_s:0.3f}s")
        if logfile is not None:
            f(f"  logfile: {logfile}")
        else:
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            f(f"  stdout: {stdout}")
            f(f"  stderr: {stderr}")

    if proc.returncode not in success_returncodes:
        log(logger.warning)
        msg = f"EXEC failed with returncode={proc.returncode}: {args_text}"
        if logfile is not None:
            msg += f"\nlogfile={logfile}"
        raise SubprocessExitCodeException(msg)

    log(logger.debug)
