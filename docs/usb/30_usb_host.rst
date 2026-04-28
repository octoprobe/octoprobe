USB host controllers
==========================

I tested some PCI usb controllers. Here is the condensed outcome:

Renesas chipsets
-------------------

.. note::

   Old, proprietary firmware, unstable

Exsys EX-11192
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

https://www.exsys.de/en/2-port-usb-3.2-gen-1-pcie-card-with-self-power-3a-renesas/EX-11192
CHF 12

**Bad**: ??

Delock 90509
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

https://www.delock.com/produkt/90509/merkmale.html

1 x Renesas D720201

**Bad**: `xhci-pci-renesas 0000:01:00.0: Error while assigning device slot ID: No Slots Available Error`

Delock 89008
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

https://www.delock.com/produkt/89008/merkmale.html

4 x Renesas uPD720202

High end card. Each uPD720202 connects to one USB-A. Therefore the overhead of a hub not required.

**Bad**: `xhci-pci-renesas 0000:06:00.0: Error while assigning device slot ID: Command Aborted`




Ubuntu 25.10
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


This is how I installed the firmware:

.. code-block:: bash

    cp K2013080.mem
    sudo mkdir -p /lib/firmware/updates/$(uname -r)
    sudo install -D -m 0644 ./K2026090.mem /lib/firmware/updates/$(uname -r)/renesas_usb_fw.mem
    sudo update-initramfs -u -k $(uname -r)

Successful boot

.. code-block:: text

    [    3.700449] xhci-pci-renesas 0000:01:00.0: failed to load firmware renesas_usb_fw.mem, fallback to ROM
    [    3.700630] xhci-pci-renesas 0000:01:00.0: xHCI Host Controller
    [    3.700638] xhci-pci-renesas 0000:01:00.0: new USB bus registered, assigned bus number 3
    [    3.700713] xhci-pci-renesas 0000:01:00.0: Zeroing 64bit base registers, expecting fault
    [    3.816816] xhci-pci-renesas 0000:01:00.0: hcc params 0x014051cf hci version 0x100 quirks 0x0000000100000010
    [    3.817087] xhci-pci-renesas 0000:01:00.0: xHCI Host Controller
    [    3.817090] xhci-pci-renesas 0000:01:00.0: new USB bus registered, assigned bus number 4
    [    3.817093] xhci-pci-renesas 0000:01:00.0: Host supports USB 3.0 SuperSpeed


Crash

.. code-block:: text

    [    9.631421] usb 3-4.3.3: New USB device found, idVendor=303a, idProduct=1001, bcdDevice= 1.01
    [    9.631425] usb 3-4.3.3: New USB device strings: Mfr=1, Product=2, SerialNumber=3
    [    9.631427] usb 3-4.3.3: Product: USB JTAG/serial debug unit
    [    9.631429] usb 3-4.3.3: Manufacturer: Espressif
    [    9.631430] usb 3-4.3.3: SerialNumber: 70:04:1D:22:84:1C
    [    9.648239] xhci-pci-renesas 0000:01:00.0: Error while assigning device slot ID: No Slots Available Error
    [    9.648248] xhci-pci-renesas 0000:01:00.0: Max number of devices this xHCI host supports is 32.
    [    9.648251] usb 3-4.4-port1: couldn't allocate usb_device
    [    9.654179] cdc_acm 3-4.3.3:1.0: ttyACM20: USB ACM device


ASM3142 chipsets
-------------------

Delock 90106
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* https://www.brack.ch/delock-pci-express-karte-usb-3-1-gen-2-2x-usb-typ-a-1605007

  * https://www.delock.com/produkt/90106/merkmale.html
  * CHF 30
  * Chipset: Asmedia ASM3142

**Bad**: `usb 3-1.3.3: device descriptor read/64, error -110`

Delock 90298
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* https://www.brack.ch/delock-pci-express-karte-usb-3-1-gen2-2x-usb-typ-a-864493

  * https://www.delock.com/produkt/90298/merkmale.html
  * PCI-Express-Karte USB 3.1 Gen2 - 2x USB-Typ-A
  * 1 x ASM3142

**Bad**: `usb 5-1.4.3: device descriptor read/64, error -110`

VIA chipsets
-------------------

EX-11049_VL805
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* https://www.brack.ch/exsys-pci-express-karte-ex-11049-1460634
  
  * https://www.exsys.ch/pcie-usb-3.2-gen-1-karte-mit-2-2-ports-via-chipsatz-EX-11049
  * CHF 23
  * Chipsatz: VIA VL805

**Bad**: `usb 5-1.4.2.3: device descriptor read/all, error -71`

Exsys EX-11192
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* https://www.brack.ch/exsys-pci-express-karte-ex-11049-1460634

  * https://www.exsys.ch/pcie-usb-3.2-gen-1-karte-mit-2-2-ports-via-chipsatz-EX-11049
  * CHF 23
  * Chipsatz: VIA VL805

**Bad**: `device descriptor read/all, error -71`

Fresco Logic chipsets
-------------------------

Exsys EX-11192
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* https://www.brack.ch/delock-pci-express-karte-90304-usb-3-0-typ-a-879350

  * https://www.delock.com/produkt/90304/merkmale.html
  * CHF38 
  * Chipset: Fresco Logic FL1100

**SUCCESS**: The first PCI card I found which works!

However **Max nuber of devices is 32**:

.. code-block:: text

    [  101.320176] usb 3-2.2.3: new full-speed USB device number 33 using xhci_hcd
    [  101.404556] xhci_hcd 0000:02:00.0: Error while assigning device slot ID: No Slots Available Error
    [  101.404649] xhci_hcd 0000:02:00.0: Max number of devices this xHCI host supports is 32.
    [  101.404717] usb 3-2.4-port1: couldn't allocate usb_device
    [  101.405025] xhci_hcd 0000:02:00.0: Error while assigning device slot ID: No Slots Available Error
    [  101.405075] xhci_hcd 0000:02:00.0: Max number of devices this xHCI host supports is 32.
    [  101.405120] usb 3-2.3-port3: couldn't allocate usb_device
