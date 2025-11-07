from simpy.core import Environment
from mints.resources import Global_Index
from mints.containers import MonitoredFilterStore

class SimulationFacility: 
    """'SimulationFacility' is a base class for MINTs simulations to extend.

    Raises:
        NotImplementedError: Error is raised if the facility does not implement the required :py:meth:'dict_of_stores' method
        NotImplementedError: Error is reaise if the facility does not implement the required :py:meth:'initialize_process' method
    """    ''''''
    def __init__(self, name, env, indexer, **kwargs):
        """Constructor for :class:'SimulationFacility'

        Args:
            name (String): Name of the facility
            env (Simpy.Environment): Simpy simulation environment
            indexer (Global_Index): MINTS Global_Index gives unique idecies to all items created during simulation

        """        
        self.name: str = name
        self.env: Environment = env
        self.indexer: Global_Index = indexer
    
    def place_items(self,store: MonitoredFilterStore, items: list):
        """Places the items in :var:'items' into the MonitoredFilterStore *store* and updates the *items* arrival times 
        to the current simulation time.

        Args:
            store (MonitoredFilterStore): The MINTS/MonitoredFilterStore to place the items into.
            items (list): The items to be placed in the store.
        """        
        if not isinstance(items, list):
            items.arrival_time=self.env.now
            store.put(items)
        else:
            for item in items:
                item.arrival_time=self.env.now
                store.put(item)
        return
    
    def dict_of_stores(self) -> dict:
        """Return a dictionary of stores used by facility

        Raises:
            NotImplementedError: _description_

        Returns:
            dict: Stores / MBAs in facility
        """
        raise NotImplementedError("Facilities must implement method to retrieve dictionary of stores")

    def initialize_processes(self, env: Environment, config: dict, facilities: dict):
        """Initialize all simpy environment processes for this facility

        Args:
            env (Environment): Simpy simulation environment
            config (dict): Dictionary of keyword parameters for facility and processes
            facilities (dict): Dictionary of other facilities in simulation
        """
        raise NotImplementedError("Facilities must implement initialize_process method")
