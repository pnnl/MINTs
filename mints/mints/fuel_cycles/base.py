import warnings
import pandas as pd
import pathlib as pa
import os
import json
import time

from mints.facilities.shipping_receiving import Mine
from mints.facilities.conversion import Conversion
from mints.facilities.fuel_fabrication import Fuel_Fab
from mints.facilities.reactors import *
from mints.facilities.utils import monitor_facility_inventory
from mints.facilities.enrichment import Enrichment
from simpy.core import Environment

from mints.resources import Global_Index
from mints.facilities import SimulationFacility

class SimulationRun:
    """
    The SimulationRun class is a generic implementation of a fuel cycle implementation.
    This class implements the functionality for loading the configuration file for the fuel cycle, executing the
    simulation, and writing simulation results to an output file.
    """
    def __init__(self, log_file: str | pa.Path = None):
        """Initialize the fuel cycle simulation object.

        Args:
            log_file (str or Path, optional): Path to the desired log file. Defaults to None.
        """
        self.env = Environment()
        self.global_index = Global_Index()
        self.facilities: list[SimulationFacility] = []

        if log_file:
            print('Logging enabled')
            logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO)

    def write_results(self, fpath: str | pa.Path):
        """Save all simulation history/inventories to a hdf5 store at fpath

        NOTE: Depending on speed/storage restrictions, we may eventually make this
        use parquet or feather, but for now this is more readable.

        Args:
            fpath (str | Path): Path of output store location
        """
        warnings.simplefilter("ignore", category=pd.errors.PerformanceWarning)
        if isinstance(fpath, str):
            fpath = pa.Path(fpath)

        if fpath.suffix != '.h5':
            fpath = fpath.with_suffix('.h5')
            SyntaxWarning(f"Filetype should be h5; renaming ({fpath})")

        with pd.HDFStore(fpath, mode='w') as store:
            for facility in self.facilities.values():
                store_dict = facility.dict_of_stores()
                for store_name, store_obj in store_dict.items():
                    df = store_obj.generate_inventory_table()
                    key = f"/{facility.name}/{store_name}"
                    store.put(key, df)
                    print(f"Saved {key} to {fpath}")

                    ins_and_outs_df = store_obj.generate_ins_and_outs_table()
                    key = f"/{facility.name}/{store_name}_ins_and_outs"
                    store.put(key, ins_and_outs_df)
                    print(f"Saved {key} to {fpath}")

    def load_config(self, config_path: str | pa.Path):
        """Load the configuration file which defines the fuel cycle.

        The details of each fuel cycle implementation are outlined in a config file which is
        unique to each fuel cycle. The fuel cycle configuration file must specify each of the
        facilities in the fuel cycle in addition to any process parameters associated with
        each of the facilities.

        Args:
            config_path (str | Path): Path to the config file to use

        Raises:
            NotImplementedError: If facility mentioned in configuration file is not yet impeplemented in the MINTS package.
        """
        with open(config_path, 'r') as file:
            config = json.load(file)

        self.facilities: dict[str, SimulationFacility] = {}
        self.facility_configs: dict[str, dict] = {}
        for facility_config in config['facilities']:
            facility_type = facility_config['type']
            name = facility_config['name']
            params = facility_config['parameters']
            self.facility_configs[name] = params

            if facility_type == 'Mine':
                self.facilities[name] = Mine(name, self.env, self.global_index, **params)
            elif facility_type == 'Conversion':
                self.facilities[name] = Conversion(name, self.env, self.global_index, **params)
            elif facility_type == 'Fuel_Fab':
                self.facilities[name] = Fuel_Fab(name, self.env, self.global_index, **params)
            elif facility_type == 'PHWR_Reactor':
                self.facilities[name] = PHWR_Reactor(name, self.env, self.global_index, **params)
            elif facility_type == 'LWR_Reactor':
                self.facilities[name] = LWR_Reactor(name, self.env, self.global_index, **params)
            elif facility_type == 'Enrichment':
                self.facilities[name] = Enrichment(name, self.env, self.global_index, **params)
            else:
                raise NotImplementedError(f"No implemented facility matches {facility_type}")

        self.simulation_params: dict = config['simulation_parameters']

    def run_simulation(self, final_time: int):
        """Run the fuel cycl simulation.

        Args:
            final_time (int): Number of timesteps to run the simulation.
        """
        # Initialize processes
        for name, facility in self.facilities.items():
            config = self.facility_configs[name]
            facility.initialize_processes(self.env, config, self.facilities)

        inv_monitors = [self.env.process(monitor_facility_inventory(self.env, f)) for f in self.facilities.values()]

        # Start simulation
        print("Starting simulation")
        start = time.time()
        self.env.run(until = final_time)
        end = time.time()
        print(f'Simulation complete; Running time={end-start}')

class HTRPrismatic(SimulationRun):
    """Fuel Cycle simulation for High Temperature Prismatic Reactor fuel cycles

        The default parameters of the HTRPrismatic fuel cycle are specified in the HTRPrismatic_default.json
        file in this same folder. This file can be copied and modified to allow for simulation of additional
        configurations of the HTR Prismatic Fuel Cycle.
    """
    def __init__(self,
                 config_path: str | pa.Path = None,
                 log_file: str | pa.Path = None):
        """Instantiate the HTR Prismatic fuel cycle

        Args:
            config_path (str | pa.Path, optional): Path to a custom config file, otherwise default settings will be used. Defaults to None.
            log_file ((str | pa.Path), optional): Path to desired log file. Defaults to None.
        """
        super().__init__(log_file)
        if config_path is None:
            absolute_module_dir = pa.Path(os.path.abspath(os.path.dirname(__file__)))
            config_path = absolute_module_dir / "HTRPrismatic_default.json"
        self.load_config(config_path)

class LWR(SimulationRun):
    """Fuel Cycle simulation for Light Water Reactor fuel cycles

        The default parameters of the LWR fuel cycle are specified in the LWR_default.json
        file in this same folder. This file can be copied and modified to allow for simulation of additional
        configurations of a Light Water Reactor fuel cycle.
    """
    def __init__(self,
                 config_path: str | pa.Path = None,
                 log_file: str | pa.Path = None):
        """Instantiate the LWR  fuel cycle

        Args:
            config_path (str | pa.Path, optional): Path to a custom config file, otherwise default settings will be used. Defaults to None.
            log_file ((str | pa.Path), optional): Path to desired log file. Defaults to None.
        """
        super().__init__(log_file)
        if config_path is None:
            absolute_module_dir = pa.Path(os.path.abspath(os.path.dirname(__file__)))
            config_path = absolute_module_dir / 'LWR_default.json'
        self.load_config(config_path)

class PHWR(SimulationRun):
    """Fuel Cycle simulation for Pressurized Heavy Water Reactor fuel cycles

        The default parameters of the PHWR fuel cycle are specified in the PHWR_default.json
        file in this same folder. This file can be copied and modified to allow for simulation of additional
        configurations of the PHWR Fuel cycle.
    """
    def __init__(self,
                 config_path: str | pa.Path = None,
                 log_file: str | pa.Path = None):
        """Instantiate the PHWR  fuel cycle

        Args:
            config_path (str | pa.Path, optional): Path to a custom config file, otherwise default settings will be used. Defaults to None.
            log_file ((str | pa.Path), optional): Path to desired log file. Defaults to None.
        """
        super().__init__(log_file)
        if config_path is None:
            absolute_module_dir = pa.Path(os.path.abspath(os.path.dirname(__file__)))
            config_path = absolute_module_dir / 'PHWR_default.json'

        self.load_config(config_path)