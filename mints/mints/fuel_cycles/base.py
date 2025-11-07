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
    def __init__(self,log_file=None):
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

    def load_config(self, config_path):
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
    def __init__(self, config_path: str | pa.Path = None,log_file=None):
        super().__init__(log_file)
        if config_path is None:
            absolute_module_dir = pa.Path(os.path.abspath(os.path.dirname(__file__)))
            config_path = absolute_module_dir / "HTRPrismatic_default.json"
        self.load_config(config_path)

class LWR(SimulationRun):
    def __init__(self, config_path=None,log_file=None):
        super().__init__(log_file)
        if config_path is None:
            absolute_module_dir = pa.Path(os.path.abspath(os.path.dirname(__file__)))
            config_path = absolute_module_dir / 'LWR_default.json'
        self.load_config(config_path)

class PHWR(SimulationRun):
    def __init__(self, config_path=None,log_file=None):
        super().__init__(log_file)
        if config_path is None:
            absolute_module_dir = pa.Path(os.path.abspath(os.path.dirname(__file__)))
            config_path = absolute_module_dir / 'PHWR_default.json'

        self.load_config(config_path)