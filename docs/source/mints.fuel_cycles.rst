Fuel Cycles Package
==========================

This package contains the implementation of the fuel cycle simulation process, which is the primary framework of MINTS.
The implementation is structured as a base `SimulationRun`, which contains the code for running the simulation, loading the configuration of the desired fuel cycle, and writing outputs if desired.
In addition to the base `SimulationRun` class, there are also implementations of specific fuel cycles object for PHWR, LWR, and Prismatic HTR fuel cycles.
These subclasses simply wrap the base init method and load the default fuel cycle configurations included with this package if no custom configuration is specified.

Fuel Cycle Configuration Files
--------------------------------

Each fuel cycle is defined in a json configuration file which defines which facilities are in the simulation, how they interact with each other, and other variables such as inventory capacities and throughput quantities for different processes.
This is broken up into two primary categories:

* `simulation_parameters`, which defines variables related to the overall simulation process, and
* `facilities`, which is a list of facilities in the fuel cycle and their associated parameters.

For example, in the PHWR fuel cycle the full specification for the fuel fabrication facility looks like:

.. code-block:: json

   {
               "type": "Fuel_Fab",
               "name": "fuel_fabrication_1",
               "parameters": {
                  "priority": 1,
                  "pellet_batch_size": 600,
                  "shipping_facility": "conversion_1",
                  "receiving_drum_throughput": 7,
                  "receiving_max_inventory": 40,
                  "throughput_pellets": 124320,
                  "pellet_press_input_material": "UO2",
                  "pellet_weight_mean_kg": 0.02,
                  "pellet_weight_std_kg": 0.0005,
                  "throughput_rods": 4144,
                  "pellets_per_rod":30,
                  "throughput_assemblies": 112,
                  "rods_per_assembly": 37
               }
         }

In this example, we specify the type of facility as a fuel fabrication facility, and give it a name (`fuel_fabrication_1`) for record keeping and for linking to other facilities.
We then specify a list called `parameters`, which contains things such as throughput variables for each facility process as well as weight distribution parameters and material types.
Here we also specify the `priority` of the facility, which determines how much priority the facility will be given relative to other faciltiies when placing requests for items from other facilities.
Here we also specify which facilities it receives material from.
In this case, the fuel fab facility is receiving input material from `conversion_1`. but this could be any conversion faciltity or also a list of facility names.


Fuel Cycle Module
------------------------------

.. automodule:: mints.fuel_cycles.base
   :members:
   :show-inheritance:
   :undoc-members:

