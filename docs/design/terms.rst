Terms
=====

Generic terms
-------------

* `HIL`: Hardware in the loop tests
* `Gadget`: Something that may be collected to a micropython board: A sensor, actor, display or even a Modbus dongle.
* `MCU`: MicroController Unit. As listed on `MicroPython Downloads`_.

.. _`MicroPython Downloads`:  https://micropython.org/download


Octoprobe specific terms
------------------------

* `Octoprobe`: Invented term: An octopus holding MCU/Gadgets in its tentacles.
* `Octobus`: Invented term: All tentacles are connected by the `octobus`: A 40 wire ribbon cable.
* `Tentacle`: Octoprobe contains tentacles. This is hardware/PCB. Every tentacle may host MCU or gadgets.

 * The tenacle is devided by

  * `Infrastructure`: The generic part of a tentacle.
  * `DUT`: The part where the MCU or the gadget will be mounted.

* `DUT`: Device Under Test. Or in this context MCU under test.
* `FUT`: Feature Under Test. For example Timer, I2c, Uart.

* `Testbed`: A testbed defines how tentacles are used to run tests. A testbed design consists of schematics of the DUT-side of the tentacles.

 * A testbed is identified by its unique name, for example 'testbed_showcase'.
 * A testbed may be instantiated multiple times. For example once in CH-Wetzikon and once in AU-Melbourne.
 * A test is ALWAYS written against a specific testbed!
