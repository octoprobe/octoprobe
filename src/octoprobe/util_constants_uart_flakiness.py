"""
UART flakyness

See ticket https://github.com/octoprobe/testbed_micropython/issues/67.

Several optimizations are done on guessing.

These constants allow to switch this optimizations on/off and if not required anymore: Remove them.
"""

SUBPROCESS_TENTACLE_DUT_TIMEOUT = True
"""
Switch the power of the DUT of before the subprocess gets killed.
"""

ENABLE_DUT_POWER_OFF_TIME_MIN = True

DUT_POWER_OFF_TIME_MIN_S = 20.0
"""
If a DUT is powered off, it should remain unpowered for some time.
"""
