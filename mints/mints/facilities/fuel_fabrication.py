import logging
import numpy as np

from simpy.core import Environment

from mints.facilities import SimulationFacility
from mints.containers import MonitoredContainer, MonitoredFilterStore
from mints.facilities.conversion import Conversion
from mints.resources import *

class Fuel_Fab(SimulationFacility):
    '''Facility for Fuel Fabrication: receives drums uo2 from shipper and manufactures
    pellets/rods/assemblies, assemblies are shipped from shipping store.
    receivingstore {MonitoredFilterStore}  :Contains drums of {uo2} shipped from shipper
    powderstore    {MonitoredContainer}    :Contains {uo2} (kg) for pellet manufacuring
    pelletstore    {MonitoredFilterStore}  :Contains pellet batches for rod manufacturing
    rodtstore      {MonitoredFilterStore}  :Contains rods for rod manufacturing
    shippingstore  {MonitoredFilterStore}  :Contains completed assemblies for shipping
    throughput     {int}                   :Max number of drums to order in each timestep (also max number of drums opened)
    '''
    def __init__(self,
                 name: str,
                 env: Environment,
                 indexer: Global_Index,
                 pellet_batch_size: float = 600,
                 priority: int = 1,
                 **kwargs):
        super().__init__(name, env, indexer)
        self.receiving_mba = MonitoredFilterStore(env)
        self.pelleting_mba = MonitoredFilterStore(env)
        self.rod_mba = MonitoredFilterStore(env)
        self.pelleting_UO2_powder_store = MonitoredContainer(env)
        self.pelleting_UO2_powder_lost = MonitoredContainer(env)
        self.shipping_mba = MonitoredFilterStore(env)

        self.pellet_batch_size = pellet_batch_size
        self.priority=priority
        
    def dict_of_stores(self):
        return {'receiving_mba':                self.receiving_mba,
                'pelleting_mba':                self.pelleting_mba,
                'rod_mba':                      self.rod_mba,
                'pelleting_UO2_powder_store':  self.pelleting_UO2_powder_store,
                'pelleting_UO2_powder_lost':    self.pelleting_UO2_powder_lost,
                'shipping_mba':                 self.shipping_mba}
    
    def receiving(self,
                  shipper: Conversion,
                  receiving_drum_throughput: int = 7,
                  receiving_max_inventory: int = 40,
                  **kwargs):
        '''
        Receiving process gets drums(not checked) from shipper,
        then opens drums and adds weight of material to bulk store
        '''
        while True:
            #order good from the shipper
            
            num_to_order=min(receiving_drum_throughput, receiving_max_inventory-self.receiving_mba.check_quantity())

            logging.info(f'{self.env.now}: Fuel Fab ordering goods from conversion -- num to order = {num_to_order}')

            #drums_received = yield shipper.shipping_mba.submit_order(num_to_order, form='drum', priority=self.priority)
            drums_received = yield shipper.shipping_mba.submit_order(num_to_order, priority=self.priority)

            #timeout so goods appear in the receiving mba next timestep
            yield self.env.timeout(1)

            if drums_received is not None:
                logging.info(f'fuel fab ordered {num_to_order} drums at {self.env.now} and received {len(drums_received)}')
                self.place_items(self.receiving_mba, drums_received)
            else:
                logging.info(f'{self.env.now}: Fuel fab received NOTHING from shipper')
          
            

    def pellet_press(self,
                     throughput_pellets: int = 124320,
                     pellet_press_input_material: Material | str = UraniumDioxide,
                     pellet_press_input_enrichment: float = None,
                     pellet_weight_mean_kg: float = .02,
                     pellet_weight_std_kg: float = .0005,
                     pellet_powder_loss_distribution=np.random.normal,
                     pellet_powder_loss_parameters=[0,0],
                     **kwargs):
        '''
        Pellet press gets bulk material from bulk store,
        then creates pellets(ITEM) and places them in the pellet store
        '''    
        if isinstance(pellet_press_input_material, str):
            pellet_press_input_material = STR_TO_MAT[pellet_press_input_material]
        pellet_press_input_material: Material = pellet_press_input_material(enrich_pct = pellet_press_input_enrichment)
        
        logging.info('pellet press is pressing')
        while True:
            #Get drums from receiving
            num_to_open = np.floor(min(throughput_pellets*pellet_weight_mean_kg/400*(1+pellet_powder_loss_parameters[0]), self.receiving_mba.check_quantity())).astype(int)

            # NOTE: KMP checkpoint
            #drums_from_receiving = yield self.receiving_mba.submit_order(num_to_open, form='drum', priority=self.priority)
            drums_from_receiving = yield self.receiving_mba.submit_order(num_to_open, priority=self.priority)

            #compute how many pellets to press
            pellets_to_make=np.floor(min(self.pelleting_UO2_powder_store.level/pellet_weight_mean_kg, throughput_pellets))
            if(pellets_to_make!=0):
                yield self.pelleting_UO2_powder_store.submit_order(pellets_to_make*pellet_weight_mean_kg, priority=self.priority)
                logging.info(f'pellet batch size = {self.pellet_batch_size}')

                #----This rounding needs to be handled differently----
                num_batches = np.floor(pellets_to_make // self.pellet_batch_size).astype(int)
                
                for _ in range(num_batches):
                    pel = HomogenousBatchedResource(self.indexer.next_pellet(),
                                                    self.env.now,
                                                    self.name,
                                                    pellet_press_input_material,
                                                    self.env.now,
                                                    batch_size=self.pellet_batch_size,
                                                    weight_distribution_parameters=[pellet_weight_mean_kg, pellet_weight_std_kg],
                                                    resource_type='pellet_batch')
                    self.pelleting_mba.put(pel)
                logging.info(f'{self.env.now}: Pellets added to store')

                #Open drums and place material in the powderstore
            if drums_from_receiving is not None:
                if not isinstance(drums_from_receiving, list):
                    actual_loss=pellet_powder_loss_distribution(*pellet_powder_loss_parameters)*drums_from_receiving.weight
                    self.pelleting_UO2_powder_lost.put(actual_loss)
                    self.pelleting_UO2_powder_store.put(drums_from_receiving.weight-actual_loss)
                else:
                    for next_drum in drums_from_receiving:
                        actual_loss=pellet_powder_loss_distribution(*pellet_powder_loss_parameters)*next_drum.weight
                        if(actual_loss>0):
                            self.pelleting_UO2_powder_lost.put(actual_loss)
                        self.pelleting_UO2_powder_store.put(next_drum.weight-actual_loss)

            logging.info(f'Fuel Fab Powder store has {self.pelleting_UO2_powder_store.level} kg at time= {self.env.now}')    
            
            yield self.env.timeout(1)

    
    def rod_fill(self, throughput_rods=4144, pellets_per_rod=30, **kwargs):
        '''
        Rod fill gets pellets from pellet store,
        then fills rods with pellets and places them in the rod store
        '''
        logging.info('rod fill online')
        # Retrieve a batch of pellets from the store (waits till first pellets are availiable)
        pellet_batch: BatchedResource = None
        pellet_batch_order: list[BatchedResource] = []
        aggregated_batches: BatchedResource = None
        while pellet_batch is None:
            yield self.env.timeout(1)
            pellet_batch: BatchedResource = yield self.pelleting_mba.submit_order(quantity=1, priority=self.priority)
        logging.info(f'{self.env.now}: Began filling rods (received first pellet batch)')

        batches_needed = (throughput_rods*pellets_per_rod) // self.pellet_batch_size

        while True:
            rods_made = 0
            new_pellet_order = yield self.pelleting_mba.submit_order(batches_needed, priority=self.priority)
            if new_pellet_order is not None:
                pellet_batch_order.extend(new_pellet_order)
            
            # Process available pellet batches to make rods
            rods_to_make = min(throughput_rods, len(pellet_batch_order) * self.pellet_batch_size // pellets_per_rod)
            
            if rods_to_make == 0:
                logging.info(f'{self.env.now}: No more pellets available, waiting for new order')
                yield self.env.timeout(1)
            else:
                # Aggregate all pellet batches
                if aggregated_batches == None:
                    aggregated_batches = pellet_batch_order.pop(0)
                while len(pellet_batch_order) > 0:
                    aggregated_batches.extend_batch(pellet_batch_order.pop(0))

                all_weights, aggregated_isotopics = aggregated_batches.sample(rods_to_make * pellets_per_rod)
                all_weights = np.split(all_weights, rods_to_make)
                all_indices = [self.indexer.next_rod() for _ in range(rods_to_make)]
                new_rods = [HomogenousBatchedResource(all_indices[i], self.env.now, self.name, aggregated_isotopics, self.env.now, pellets_per_rod, all_weights[i]) for i in range(rods_to_make)]
                self.place_items(self.rod_mba, new_rods)
                            
                logging.info(f'{rods_made} rods added to rodstore time={self.env.now}')
                yield self.env.timeout(1)  # Process the next batch
            
    def assembly_assembler(self, throughput_assemblies=112, rods_per_assembly=37, **kwargs):
        '''
        Gets rods from rod store,
        fills assemblies with rods and places them in shippingstore
        '''
        logging.info('assembly assembler is assembling')
        rods: list[BatchedResource] = []
        while True:
            # Try to order as many rods as needed to make throughput_assemblies
            rods_to_order = (throughput_assemblies * rods_per_assembly) - len(rods)
            new_rods = yield self.rod_mba.submit_order(rods_to_order)
            if new_rods is not None:
                rods.extend(new_rods)
            while len(rods) >= rods_per_assembly:
                # Make a fuel assembly
                rods_for_next_assembly = rods[:rods_per_assembly]
                del rods[:rods_per_assembly]
                a_id = self.indexer.next_assembly()

                #TODO: This assumes homogenous isotopics across rods; update for mixed case
                rod_weights = [r.aggregate_weights() for r in rods_for_next_assembly]
                isotopics = aggregate_isotopics([r.aggregate_isotopics() for r in rods_for_next_assembly])
                next_assembly = HomogenousBatchedResource(a_id, self.env.now, self.name, isotopics,self.env.now, batch_size=rods_per_assembly, weights=rod_weights, resource_type='fuel_assembly')
                yield self.shipping_mba.put(next_assembly)

            yield self.env.timeout(1)
            
    def initialize_processes(self, env, config, facilities):
        receiving = env.process(self.receiving(facilities[config['shipping_facility']], **config))
        pellet_press = env.process(self.pellet_press(**config))
        rod_fill = env.process(self.rod_fill(**config))
        assembly_assembler = env.process(self.assembly_assembler(**config))




