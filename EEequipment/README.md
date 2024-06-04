This repo will be for controlling various EE equipment

I will try to keep things standard, but due to instrument differences code implementations may be different between equipment


## equipment interfaces

- **spd3303x**
  - `pyvisa`
- **usbrelay**
  - `usb`
- **xdm1041**
  - `serial`
- **xds110**
  - This actually runs various script files through `os`
  - No actual communication with the device