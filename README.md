# Material Inventory Nuclear Tracking Simulator (MINTs)

The Material Inventory Nuclear Tracking Simulator (MINTs) is a discrete event simulation software modeling the flow of material through a nuclear fuel cycle, modeling material flow down to the individual item level. The simulation currently includes functionality for pressurized heavy water reactor (PHWR) fuel cycles, light water reactor (LWR) fuel cycles, and Prismatic High-Temperature Reactor (HTR) fuel cycles.

The MINTs software can be installed as a python package by navigating to the `mints` directory and running `pip install -e.`

The notebook `MINTs_Demo.ipynb` provides a high-level guide to getting started with MINTs, and our [full documentation can be found on Read the Docs](https://mints.readthedocs.io/en/latest/).

## Project Abstract
Safeguards implementation planning requires a deep understanding of the material flow within a fuel cycle. This can be facilitated by nuclear fuel cycle simulation. For forward-planning safeguards implementations for reactors not yet in operations, it is especially key to understand material flow at the item, stratum, facility, and fuel cycle scales to best-implement safeguards. However, with a lack of historical safeguards-relevant information, simulation becomes a critical (and sometimes the only) tool available for planning. The Material Inventory and Nuclear Tracking simulator (MINTs) is a discrete event simulator designed to simulate nuclear material flow across a nuclear fuel cycle at the item, stratum, facility, and whole-cycle scale.

Further details can be found in our publication at the 2025 Advances in Nuclear Nonproliferation Technology and Policy Conference: **Link will be added once available.**  


### License
MIT License

Copyright (c) 2025, Battelle Memorial Institute

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### Disclaimer
This material was prepared as an account of work sponsored by an agency of the United States Government. Neither the United States Government nor the United States Department of Energy, nor the Contractor, nor any or their employees, nor any jurisdiction or organization that has cooperated in the development of these materials, makes any warranty, express or implied, or assumes any legal liability or responsibility for the accuracy, completeness, or usefulness or any information, apparatus, product, software, or process disclosed, or represents that its use would not infringe privately owned rights. 

Reference herein to any specific commercial product, process, or service by trade name, trademark, manufacturer, or otherwise does not necessarily constitute or imply its endorsement, recommendation, or favoring by the United States Government or any agency thereof, or Battelle Memorial Institute. The views and opinions of authors expressed herein do not necessarily state or reflect those of the United States Government or any agency thereof. 

PACIFIC NORTHWEST NATIONAL LABORATORY operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY under Contract DE-AC05-76RL01830 
