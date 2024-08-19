# Terms

## Generic terms

* `HIL`: Hardware in the loop tests
* `Gadget`: Something that may be collected to a micropython board: A sensor, actor, display or even a Modbus dongle.
* `MCU`: MicroController Unit. As listed on [Micropython Downloads](https://micropython.org/download/).

## Octoprobe specific terms

* `Octoprobe`: Invented term: An octopus holding MCU/Gadgets in its tentacles.
* `Octobus`: Invented term: All tentacles are connected by the `octobus`: A 40 wire ribbon cable.
* `Tentacle`: Octoprobe contains tentacles. This is hardware/PCB. Every tentacle may host MCU or gadgets.
* `DUT`: Device Under Test. Or in this context MCU under test.
* `FUT`: Feature Under Test. For example Timer, I2c, Uart.
* `Infrastructure`: The generic part of a tentacle.

* `Infrastructure`: (TODO: Use another term!) A infrastructure defines how tentacles are used to run tests: Schematics of the DUT-side of the tentacles.

  A test is ALWAYS written against a infrastructure!


