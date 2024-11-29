
## Introduction
---
This project is meant for software controlled testing of an embedded target
The inital scope was just interfacing with debug probes and serial ports, but has expanded to include interfacing with test and
measurement equipment



## Installation Instructions
---
### Tkinter

#### Linux machine

To get a valid Tkinter install, this command worked for me

```
sudo apt-get install python3-tk
```

#### Windows
should be more straightforward


### VISA
To use `pyvisa` you will need to configure a backend for the VISA interface.
You can read good instruction [here](https://pyvisa.readthedocs.io/en/latest/introduction/configuring.html)


