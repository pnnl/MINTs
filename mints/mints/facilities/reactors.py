
import numpy as np
import logging
from mints.containers import *
from mints.resources import *
from mints.facilities import SimulationFacility
from mints.facilities.fuel_fabrication import Fuel_Fab
from simpy.core import Environment

class PHWR_Reactor(SimulationFacility):
    '''
    Reactor class has store for fresh fuel assemblies,spent fuel assembiles
    and the core
    '''
    def __init__(self,
                 name: str,
                 env: Environment,
                 indexer: Global_Index,
                 load_time: int = 1,
                 priority: int = 1,
                 **kwargs):
        super().__init__(name, env, indexer)
        self.receiving_mba = MonitoredFilterStore(env)
        self.spent_fuel_mba = MonitoredFilterStore(env)
        self.core_mba = MonitoredFilterStore(env)
        self.load_time = load_time
        self.priority=priority

    def dict_of_stores(self):
        return {'receiving_mba':    self.receiving_mba,
                'spent_fuel_mba':   self.spent_fuel_mba,
                'core_mba':         self.core_mba}
    
    def reactor_receiving(self, shipper: Fuel_Fab, receiving_assemblies_throughput: int = 112, receiving_max_inventory: int = 300, **kwargs):
        '''
        Reactor receiving gets assemblies from shipper and places them in
        fresh fuel store
        '''
        while True:
            num_to_order=min(receiving_assemblies_throughput, receiving_max_inventory-self.receiving_mba.check_quantity())
            received_assemblies = yield shipper.shipping_mba.submit_order(num_to_order, form='fuel_assembly', priority=self.priority)
            
            #timeout so goods appear at the begining of the next timestep
            yield self.env.timeout(1)
            
            if received_assemblies is not None:
                self.place_items(self.receiving_mba, received_assemblies)
                logging.info(f'{self.env.now}: Reactor ordered {num_to_order} and received {len(received_assemblies)}')
            #self.receiving_mba._save_inventory_record()
            
        
     
    def reactor_load(self, reload_batch_size: int = 112, core_capacity: int = 4560, depletion_pu_pct: float = .0023, **kwargs):
        '''
        Reactor load takes assemblies from fresh fuel store and places in
        core. If core is full an assebly is first removed (FIFO by default)
        All pellets in assembly are "transmuted" to spent fuel when removed from the core
        This is very CANDU and LWR will be very different
        Reactor "turns on" when 4560 asseblies are loaded
        '''   
        assemblies_to_load: list[BatchedResource] = []
        while True:
            #How many asseblies can be loaded into the core (what does a reactor opperator do if there are not enough)
            requested_assemblies = yield self.receiving_mba.submit_order(reload_batch_size, form='fuel_assembly', priority=self.priority)
            if requested_assemblies is not None:
                assemblies_to_load.extend(requested_assemblies)

            while len(assemblies_to_load) > 0:
                next_assembly = assemblies_to_load.pop(0)
                # Can also batch this
                if(self.core_mba.check_quantity() >= core_capacity):
                    logging.info('core is full, unloading 1 assembly')
                    spent_assembly_list = yield self.core_mba.submit_order(1)
                    spent_assembly=spent_assembly_list[0]
                    #transmute to spent fuel
                    # TODO: Repeat the aggregation process here
                    spent_assembly.what = UraniumDioxide(pu_pct = depletion_pu_pct)
                    # for r_id in spent_assembly.rods:
                    #     r_id.what = UO2r
                    #     for p_id in r_id.pellets:
                    #         p_id['isotopes']=UO2r

                    yield self.spent_fuel_mba.put(spent_assembly)
                    logging.info(f'assembly {spent_assembly.id} unloaded from reactor')
                    logging.info(f'Spent fuel has {self.spent_fuel_mba.check_quantity()} assemblies')
                    yield self.core_mba.put(next_assembly)
                    logging.info(f'assembly {next_assembly.id} added to the core')
                else:
                    yield self.core_mba.put(next_assembly)
                    logging.info(f'assembly {next_assembly.id} added to the core')
                    logging.info(f'core has {self.core_mba.check_quantity()} assemblies')
                    if(self.core_mba.check_quantity(form='fuel_assembly') == core_capacity):
                        print(f"Reactor is online (time = {self.env.now})")
                        logging.info('***********************************************')
                        logging.info('*******************Reactor is online***********')
                        logging.info('***********************************************')
            #logging.info(f'core has {self.core_mba.check_quantity(form='fuel_assembly')} assemblies at time = {self.env.now}')
            yield self.env.timeout(self.load_time)

    def initialize_processes(self, env: Environment, config: dict, facilities: dict):
         receiving = env.process(self.reactor_receiving(facilities[config['shipping_facility']], **config))
         loading = env.process(self.reactor_load(**config))

class LWR_Reactor(SimulationFacility):
    '''
    Reactor class has store for fresh fuel assemblies,spent fuel assembiles
    and the core
    receivingstore {MonitoredFilterStore} :Contains fuel assemblies shipped from shipper
    reactor_mba {MonitoredFilterStore} :Contains fuel assemblies moved from recieving to the loading area
    core_mba1   {MonitoredFilterStore} :Contains fuel assemblies in the reactors outermost zone
    core_mba2   {MonitoredContainer}   :Contains fuel assemblies in the reactors core, moved from zone1
    core_mba3   {MonitoredContainer}   :Contains fuel assemblies in the reactors core, moved from zone2
    priority        {int}: Facilities priority when ordering {in_material} from {shipper}
    load_time       {int}: Number of Weeks between reactor reloads
    feed_material       {mints.material}: Feed material for the cascade
    '''
    def __init__(self, name, env, indexer, reactor_load_time=1, priority=1, **kwargs):
        super().__init__(name, env, indexer)
        self.receiving_mba = MonitoredFilterStore(env)
        self.reactor_mba = MonitoredFilterStore(env)
        self.spent_fuel_mba = MonitoredFilterStore(env)
        #LWR core is represented with three "regions" as fuel is ofter burned 3 times in different
        #Locations in the reactor (outside,middle,center)
        self.core_mba1 = MonitoredFilterStore(env)
        self.core_mba2  = MonitoredFilterStore(env)
        self.core_mba3 = MonitoredFilterStore(env)
        
        self.load_time = reactor_load_time #Time between reloading/shuffling the core
        self.priority=priority

    def dict_of_stores(self):
        return {'receiving_mba':      self.receiving_mba,
                'reactor_mba':        self.reactor_mba,
                'spent_fuel_mba':     self.spent_fuel_mba,
                'core_mba1':          self.core_mba1,
                'core_mba2':          self.core_mba2,
                'core_mba3':          self.core_mba3,}

    def reactor_receiving(self, shipper: Fuel_Fab, receiving_assemblies_throughput: int = 60, receiving_max_inventory: int = 200, **kwargs):
        '''
        Reactor receiving gets assemblies from shipper and places them in
        recieving store
        '''
        while True:
            num_to_order=min(receiving_assemblies_throughput, receiving_max_inventory-self.receiving_mba.check_quantity())
            received_assemblies = yield shipper.shipping_mba.submit_order(num_to_order, form='fuel_assembly', priority=self.priority)
            if received_assemblies is not None:
                self.place_items(self.receiving_mba, received_assemblies)

            yield self.env.timeout(1)
        
     
    def reactor_load(self,
                     reload_batch_size: int = 59,
                     core_capacity: int = 177,
                     core_1_pu_pct: float = .003,
                     core_2_pu_pct: float = .002,
                     core_3_pu_pct: float = .001,
                     **kwargs):
        '''
        Reactor load takes assemblies from receiving and places them in the reactor_mab_store. Once num_per_zone
        asseblies are availiable a loading opperation will load the assemblies into the core and shuffle assemblies in
        the core. If an assembly has been burned 3 times it is moved to spent fuel
        core_capacity {int}: Number of Assemblies in the core when full
        '''
        num_per_zone=np.floor(core_capacity/3).astype(int) #number of asseblies in each zone of the core
        reactor_online=False
        reactor_next_reload=1

        #Move fresh assemblies from receiving MBA to Reactor_mba
        while True:
            num_to_move=num_per_zone-self.reactor_mba.check_quantity()
            received_assemblies = yield self.receiving_mba.submit_order(num_to_move, form='fuel_assembly', priority=self.priority)
            if received_assemblies is not None:
                self.place_items(self.reactor_mba, received_assemblies)
                #logging.info(f'{self.env.now}: reactor_mba ordred {num_to_move} and received {len(received_assemblies)} from receiving')

            if(True):
                if(self.env.now==reactor_next_reload):
                    if(self.reactor_mba.check_quantity()>=num_per_zone): #IF there are enough fresh fuel asseblies for relaod
                        #Unload core_mba3 and move to spent fuel
                        num_to_move=min(self.core_mba3.check_quantity(),num_per_zone)
                        spent_assemblies=yield self.core_mba3.submit_order(num_to_move,form='fuel_assembly',priority=self.priority)
                        if(self.core_mba3.check_quantity()>0):
                            print('-----Problem in Unloading core3-----')
                        #transmute the fuel to spent fuel
                        if spent_assemblies is not None:
                            for assembly in spent_assemblies:
                                assembly.what = UraniumDioxide(pu_pct = core_1_pu_pct)
                            self.place_items(self.spent_fuel_mba,spent_assemblies)

                        #Move Fuel from core mba2 ->core mba3
                        num_to_move=min(self.core_mba2.check_quantity(),num_per_zone)
                        assemblies_to_mba3=yield self.core_mba2.submit_order(num_to_move,form='fuel_assembly',priority=self.priority)
                        if(self.core_mba2.check_quantity()>0):
                            print('-----Problem in Unloading core2-----')

                        #transmute the fuel
                        if assemblies_to_mba3 is not None:
                            for assembly in assemblies_to_mba3:
                                assembly.what = UraniumDioxide(pu_pct=core_2_pu_pct)
                            self.place_items(self.core_mba3,assemblies_to_mba3)

                        #Move Fuel from core mba1 ->core mba2
                        num_to_move=min(self.core_mba1.check_quantity(),num_per_zone)
                        assemblies_to_mba2=yield self.core_mba1.submit_order(num_to_move,form='fuel_assembly',priority=self.priority)
                        if(self.core_mba1.check_quantity()>0):
                            print('-----Problem in Unloading core1-----')
                        #transmute the fuel
                        if assemblies_to_mba2 is not None:
                            for assembly in assemblies_to_mba2:
                                assembly.what = UraniumDioxide(pu_pct=core_3_pu_pct)
                                #for rod in assembly.rods:
                                #    for pellet in rod.pellets:
                                #        pellet['isotopes']=UO2_lwr1.isotopes
                            self.place_items(self.core_mba2,assemblies_to_mba2)

                        #Move Fuel from fresh fuel to core1
                        assemblies_to_mba1=yield self.reactor_mba.submit_order(num_per_zone,form='fuel_assembly',priority=self.priority)
                        self.place_items(self.core_mba1,assemblies_to_mba1)


                        #Check that all the core mbas are full
                        if(self.core_mba1.check_quantity_present()==num_per_zone and self.core_mba2.check_quantity_present()==num_per_zone and self.core_mba3.check_quantity_present()==num_per_zone):
                            reactor_start_time=self.env.now
                            reactor_next_reload=reactor_start_time+self.load_time
                            print(f'-------------{self.name} is Online t={self.env.now}-------------')
                        else:
                            print(f'-----------{self.name} not full time={self.env.now}-----')
                            reactor_online=False
                            reactor_next_reload+=1

                    else:
                        reactor_online=False
                        reactor_next_reload+=1
                
            yield self.env.timeout(1)

    def initialize_processes(self, env, config, facilities):
        receiving = env.process(self.reactor_receiving(facilities[config['shipping_facility']], **config))
        loading = env.process(self.reactor_load(**config))