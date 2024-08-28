"""
# Problem

Some code does not run in the debugger. For example if the code calls `sys.settrace()` (A debugger may not be started withing a debugger)

## Vscode Solution

https://code.visualstudio.com/docs/python/debugging
  * debugpy may be called with `--configure-subProcess false`.
  * vscode launch.json: `"subProcess": false,`

This then will NOT debug spawned subprocesses.

## Background how debugby implements debugging of subprocesses

See: https://github.com/microsoft/debugpy/blob/main/doc/Subprocess%20debugging.md
See: https://github.com/microsoft/debugpy/issues/781

Reverse engineering of the implementation of debugpy:
* debugpy adds arguments to the python process. For example:
    python3 -BS example.py
  will become
    python3 -BS .../pydevd.py --port=47633 --ppid=58478 --filer example.py

* The subprocess is `.../pydevd.py`. This process will:
  * Remove the additional parameters
  * mock all fork/exec related function.

The mocking will be triggered from `def is_python(path):`. The mocking itself is done in `def monkey_patch_module`.
See https://github.com/microsoft/debugpy/blob/main/src/debugpy/_vendored/pydevd/_pydev_bundle/pydev_monkey.py
"""

import logging

logger = logging.getLogger(__file__)


def un_monkey_patch():
    """
    Prevent vstudio by debugging subprocesses.
    This will be applied for ALL SUBSEQUENT subprocesses!

    This is done by reverting the mocks
    from https://github.com/microsoft/debugpy/blob/main/src/debugpy/_vendored/pydevd/_pydev_bundle/pydev_monkey.py.
    """
    touched = False
    for module_name in ("os", "_posixsubprocess", "subprocess", "_subprocess"):
        try:
            module = __import__(module_name)
        except ModuleNotFoundError:
            continue
        prefix_original = "original_"
        for function_name_mock in module.__dict__.keys():
            if not function_name_mock.startswith(prefix_original):
                continue
            function_name = function_name_mock[len(prefix_original) :]
            logger.debug(f"revert mock {function_name_mock} -> {function_name}")
            setattr(module, function_name, getattr(module, function_name_mock))
            touched = True
    if touched:
        logger.info(
            "We are running in vscode and prevent subprocesses to be debugged: Applied 'un_monkey_patch()'!"
        )
