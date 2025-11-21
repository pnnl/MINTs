.. MINTs documentation master file, created by
   sphinx-quickstart on Wed Nov 12 10:08:09 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Material Inventory Nuclear Tracking Simulator (MINTs) Documentation
====================================================================

Welcome to the Material Inventory and Nuclear Tracking simulator (MINTs) documentation page.

The repository is divided into subpackages for `facilities`, `fuel_cycles`, and includes submodules for `containers` 
(implementations of the Material Balance Areas (MBAs) in the simulation), and `resouces` (items and material types used in the fuel cycle simulations).

Installation
--------------
The MINTS package can be installed via pip by cloning the repository and then using pip to install the package:

.. code-block:: bash

   git clone https://github.com/pnnl/MINTs.git
   cd MINTs/mints
   pip install -e .


Getting Started
------------------
Once the package is installed, you can begin running any of the implemented fuel cycle simulations by simply importing the package:

.. code-block:: python

   from mints.fuel_cycles import PHWR
   fuel_cycle = PHWR()
   number_of_weeks = 52
   fuel_cycle.run_simulation(number_of_weeks)

The Jupyter Notebook `MINTs_Demo.ipynb` in the MINTs reposistory provides more thorough examples for running and viewing the output of the built-in fuel cycles, and documentation
explaining how the configuration files work (and can be used for designing your own custom fuel cycles) can be found in the documentation of the Fuel Cycle subpackage.

Package Contents
-----------------
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   mints
