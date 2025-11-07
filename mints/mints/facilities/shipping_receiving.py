import numpy as np
import logging
from mints.containers import *
from mints.resources import *
from mints.facilities import SimulationFacility
from simpy.core import Environment



class Mine(SimulationFacility):
    ''' Uranium mine class
    name: name for the facility (ex. mine1)
    Contains shipping store for drums(U3O8) to be shipped
    '''
    def __init__(self, name, env, indexer, **kwargs):
        super().__init__(name, env, indexer)
        self.shipping_mba: MonitoredFilterStore = MonitoredFilterStore(env)

    @staticmethod
    def drum_weight():
        return np.random.normal(400, 0.1)

    def drum_fill(self, drum_throughput=7,drum_weight_mean_kg=400, drum_weight_std_kg=0.1, drum_weight_dist=np.random.normal, out_material: str | Material = TriuraniumOctoxide, **kwargs):
        '''Uranium mine processes
        Creates Drums of UO2 and places them in the shippingstore
        throughput {int} : The number of drums to be place in the shipping store (mined) in each timestep
        '''
        if isinstance(out_material, str):
            out_material = STR_TO_MAT[out_material]
        out_material: Material  = out_material()

        logging.info('drum fill is filling drums!')
        while True:
            for _ in range(drum_throughput):
                params=[drum_weight_mean_kg,drum_weight_std_kg]
                #drum1 = drum(self.indexer.next_drum(), drum_weight_dist(drum_weight_mean_kg,drum_weight_std_kg), self.env.now, self.name, out_material, 'drum', self.env.now)
                drum1 = Drum(self.indexer.next_drum(), Mine.drum_weight(), self.env.now, self.name, out_material, self.env.now)
                yield self.shipping_mba.put(drum1)
            logging.info(f't={self.env.now}: {self.name} mined {drum_throughput} drums')
            yield self.env.timeout(1)

    def dict_of_stores(self):
        return {'shipping_mba':self.shipping_mba}
    
    def initialize_processes(self, env: simpy.Environment, config, facilities=None):
        shipping = env.process(self.drum_fill(**config))
    

class Mat_shipper(SimulationFacility):
    def __init__(self,
                 name: str,
                 env: Environment,
                 indexer: Global_Index,
                 priority: int = 1,
                 ship_material: str | Material = UraniumHexaFlouride,
                 ship_enrichment: float = None, **kwargs):
        super().__init__(name, env, indexer)
        self.priority=priority
        self.shipping_mba: MonitoredFilterStore = MonitoredFilterStore(env)

        if isinstance(ship_material, str):
            ship_material = STR_TO_MAT[ship_material]

        self.material: Material = ship_material(enrich_pct=ship_enrichment)

    def drum_fill(self,drum_throughput=7):
        '''Makes containers of ship_material
        '''
        logging.info(f'{self.name} is shipping')
        while True:
            for _ in range(drum_throughput):
                drum1=Drum(self.indexer.next_drum(), Mine.drum_weight(), self.env.now, self.name, self.material, self.env.now)
                yield self.shipping_mba.put(drum1)
            logging.info(f'{drum_throughput} drums made at {self.name} time={self.env.now}')
            yield self.env.timeout(1)