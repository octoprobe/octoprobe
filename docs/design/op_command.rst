cli interface: `op` 
===========================


.. note::

    Command line interface 'op' ('op' for 'octoprobe')


    The command 'op' may be used to control the tentacle. The same commands are provided as a python interface which allow to build `testbeds_` like `testbed_showcase` and `testbed_micropython`.


Power
------


Flashing PICO_INFRA or PICO_PROBE
-----------------------------------

.. note:: 

    Below commands work the same with `bootmode-infra` and `bootmode-probe`.


**Prepare to copy UF2 files onto the pico-disk**

.. code-block:: bash

    op bootmode-infra 
    Tentacle de64d401df5f-0d33 on USB 3-6.3.4.1 /dev/ttyACM1
      PICO_INFRA: Power off.
      PICO_INFRA: Press Boot Button.
      PICO_INFRA: Power on.
      PICO_INFRA: Release Boot Button.

      PICO_INFRA: Detected on port 3-6.3.4.1.1. Please flash:
        cp firmware.uf2 /media/maerki/RPI-RP2

**Prepare for flashing with picotool**

.. code-block:: bash

    op bootmode-infra --picotool-cmd
    Tentacle de64d401df5f-0d33 on USB 3-6.3.4.1 /dev/ttyACM0
      PICO_INFRA: Power off.
      PICO_INFRA: Press Boot Button.
      PICO_INFRA: Power on.
      PICO_INFRA: Release Boot Button.

      PICO_INFRA: Detected on port 3-6.3.4.1.1. Please flash:
        /home/maerki/octoprobe_downloads/binaries/x86_64/picotool load --update --bus 3 --address 67 --execute firmware.uf2

**Flash a given uf2-file**

.. code-block:: bash

    op flash-infra RPI_PICO-20240602-v1.23.0.uf2


PICO_PROBE power
-----------------

.. note:: 

     The PICO_PROBE provides **no** leds indicating power or bootmode. You may observer the state using `sudo dmesg --follow`

Depending on the software loaded on the PICO_PROBE, it may be used as UART+SWD or DAQ or micropython.

These commands allow access the PICO_PROBE.

**Default state: PICO_PROBE off and boot button unpressed**

.. code-block:: bash
   
    op power --off proberun --on probeboot

**Power on PICO_PROBE in application mode**
.. code-block:: bash

    # Power off, Application mode
    op power --off proberun --on probeboot
    # Power on
    op power --on proberun

**Power on PICO_PROBE in programming mode**

.. code-block:: bash

    # Power off, Programming mode
    op power --off proberun --off probeboot
    # Power on
    op power --on proberun

Power: Relay and leds
----------------------

Possible values for below command: infra|infraboot|probeboot|proberun|dut|led_error|led_active|relay1|relay2|relay3|relay4|relay5|relay6|relay7

.. code-block:: bash

    op power --on relay2 --off relay3

Special case: tentacle lost
-----------------------------

If PICO_INFRA is not powered on a tentacle, `op query` may not detect the serial number of the tentacle.

**Below command powers PICO_INFRA on ALL tentacles**

.. code-block:: bash

    op power --poweron