import numpy as np
import numpy as np
import logging
from mints.facilities import SimulationFacility
from mints.facilities.shipping_receiving import Mine
from mints.containers import *
from mints.resources import *
from simpy.core import Environment
import matplotlib.pyplot as plt

class Conversion(SimulationFacility):
    '''Conversion facility class
    received drums are placed in receiving store, drums are moved to the chemistry mba and then broken into isotopes in sepetate stores by material weight
    Isotopes are moved from the chemistry process to product. Converted drums are created from isotopes is in product stores stores but material weight
    in_material  : Input material (mints.resources) to be converted
    out_material : Output material (mints.resources) to be shipped

    receivingstore {MonitoredFilterStore} :Contains drums of {in_material} shipped from shipper
    chemistry_mab_drums {MonitoredFilterStore} :Contains drums of {in_material} moved from recieving to chemisrty (unopened)
    chem_mba_process {Dictionary}{'Isotope':MonitoredContainer} :Dictionary of containers for isotopes in process in chemistry MBA
    chem_mba_product {Dictionary}{'Isotope':MonitoredContainer} :Dictionary of container for isotopes finished converting and ready to be packaged
    
    shippingstore  {MonitoredFilterStore} :Contains drums of {out_material} ready to be shipped
    priority {int} : Facilities priority when ordering {in_material} from shipper
    '''
    def __init__(self, name, env, indexer,
                 in_material: str | Material = UraniumDioxide,
                 out_material: str | Material = UraniumHexaFlouride,
                 in_enrichment: float = None,
                 out_enrichment: float = None,
                 drum_weight_mean_kg=400,
                 drum_weight_std_kg=0.1,
                 drum_weight_dist=np.random.normal,
                 priority=1,
                 shipping_max_inventory=30,
                 **kwargs):
        super().__init__(name, env, indexer)
        if isinstance(in_material, str):
            in_material = STR_TO_MAT[in_material](enrich_pct=in_enrichment)
        if isinstance(out_material, str):
            out_material = STR_TO_MAT[out_material](enrich_pct=out_enrichment)

        self.in_material: Material = in_material
        self.out_material: Material = out_material

        self.shipping_max_inventory = shipping_max_inventory
        # Receiving MBA
        self.receiving_mba = MonitoredFilterStore(env)

        # Chemistry MBA
        self.common_isotopes = self.in_material.isotopes.keys() & self.out_material.isotopes.keys()

        self.chemistry_mba_drums = MonitoredFilterStore(env) #Store for unopened drums in chem mba
        self.chem_mba_process: dict = {}   #Dictionary of isotopestores for the chemistry process(filled by in_material)
        self.chem_mba_toproduct: dict = {} #Dictionary of isotopestores to be packaged into out_material
        self.chem_mba_lostmaterial: dict = {} #Dictionary of isotopestores for the material lost during conversion
        for ii in self.common_isotopes:
            self.chem_mba_process[f'{ii}_in_process'] = MonitoredContainer(env,capacity=50000)
            self.chem_mba_toproduct[f'{ii}_to_product'] = MonitoredContainer(env,capacity=50000)
            self.chem_mba_lostmaterial[f'{ii}_lost_material'] = MonitoredContainer(env)
        
        

        logging.debug(f"FACILTY {self.name} common isotopes: {self.common_isotopes}")
        
        # Shipping MBA
        self.shipping_mba = MonitoredFilterStore(env,capacity=self.shipping_max_inventory)
        #self.shipping_mba = MonitoredFilterStore(env)
        self.priority: int = priority

        # Weight parameters around drum packing
        self.drum_weight_mean: float = drum_weight_mean_kg
        self.drum_weight_std: float = drum_weight_std_kg

        self._drum_weight: callable = drum_weight_dist

        #ratio of input u235 to output u235 (used to convert max_drum_throughput(output) to input quantities)
        self.in_out_ratio = in_material.isotopes['U235'] / out_material.isotopes['U235']

        #Combined dict of dynamic and static stores
        self.store_mba = {'receiving_mba':           self.receiving_mba,
                    'shipping_mba':             self.shipping_mba,
                    'chem_mba_items':            self.chemistry_mba_drums,
                    **self.chem_mba_lostmaterial,**self.chem_mba_process, **self.chem_mba_toproduct}

    def dict_of_stores(self):
        return self.store_mba
    
    def conversion_receiving(self, shipper: Mine,
                             receiving_drum_throughput=7,
                             receiving_max_inventory=40,
                             input_container_type='drum',
                             **kwargs):
        '''
        Orders in_material in (drums/cylinders) from shipper
        shipper         {MonitoredFilterStore} : shipping store of the shipper
        drum_throughput {int} : Max number of drums to order each timestep
        max_inventory   {int} : Max number of items {drums/cylinders} that can be stored in recieving
        '''
        while True:
            #order drums from the shipper
            num_to_order=min(receiving_drum_throughput,receiving_max_inventory-self.receiving_mba.check_quantity())
            logging.info(f't={self.env.now}: {self.name} ordered num_to_order ={num_to_order} {input_container_type}(s)')
            
            if(len(self.shipping_mba.items) <self.shipping_max_inventory):
                drums_received = yield shipper.shipping_mba.submit_order(num_to_order, priority=self.priority)
            else:
                drums_received=None

            #drums_received = yield shipper.shipping_mba.submit_order(num_to_order, priority=self.priority)

            #drums_received = yield shipper.shipping_mba.submit_order(num_to_order, form=input_container_type, priority=self.priority)
            if drums_received is not None:
                self.place_items(self.receiving_mba, drums_received)
                logging.info(f't={self.env.now}: {self.name} received {len(drums_received)} {input_container_type}(s)')
            else:
                logging.info(f't={self.env.now}: {self.name} received 0 {input_container_type}(s)')

            yield self.env.timeout(1) #timeout so goods "appear" in the store at the next time step

            #place drums in the recieving mba
           # if drums_received is not None:
                
            #    logging.info(f't={self.env.now}: {self.name} received {len(drums_received)}')
            #    logging.info(f't={self.env.now}: {self.name} placed {len(drums_received)} in receiving_mba ')
        
    def conversion_chemistry(self,
                             conversion_max_drum_throughput=6,
                             process_loss_distribution=np.random.normal,
                             process_loss_parameters=[0,0],
                             output_container_type='drum',
                             input_container_type='drum',
                             **kwargs):
        '''
        Gets items {drums/cylinders} of in_material from recieving. Opens items and places respective isotopes in chemistry process stores.
        Moves isotopes from chemistry process stores to chemistry product stores. Fills items {drums/cylinders} with isotopes from chemistry product stores.
        max_drum_througput {int} :Maximum number of drums that can be filled in one timestep
        process_loss {float} : Process loss, (1+process_loss) material is taken from stores for each 1 material converted 
        '''
        while True:
            #Move items from recieving MBA to the Chemisty MBA where they can be opened
   
            num_to_get=min(self.receiving_mba.check_quantity(), np.ceil(conversion_max_drum_throughput*self.in_out_ratio).astype(int))
            logging.info(f't={self.env.now}: {self.name} chemistry_mab ordered num_to_order ={num_to_get} {input_container_type}(s)')
            #drums_to_chem_mba = yield self.receiving_mba.submit_order(num_to_get, form=input_container_type, priority=self.priority)
            drums_to_chem_mba = yield self.receiving_mba.submit_order(num_to_get, priority=self.priority)
            if drums_to_chem_mba is not None:
                logging.info(f't={self.env.now}: {self.name} moved {len(drums_to_chem_mba)} {input_container_type}(s) to conversion_chem')
                self.place_items(self.chemistry_mba_drums, drums_to_chem_mba)
            else:
                logging.info(f't={self.env.now}: {self.name} moved 0 {input_container_type} to conversion_chem')

            #Compute material to move from  intermediate products to drums
            #Estimate of the number of drums of converted product
            mat_to_convert=conversion_max_drum_throughput*self.drum_weight_mean #If the material being convert is 100% a single isotope this would be the amount
            for ii in self.common_isotopes:
                #what = np.floor(self.chem_mba_process[f'{ii}_in_process'].level / (400*(1+process_loss_parameters[0])*self.out_material.isotopes[ii])).astype(int)*400
                kg_per_drum = (self.drum_weight_mean * self.out_material.isotopes[ii])
                current_kg = self.chem_mba_process[f'{ii}_in_process'].level
                drums_possible = np.floor(current_kg / kg_per_drum)
                kg_possible = drums_possible * self.drum_weight_mean
                logging.debug(f"{self.name} [t = {self.env.now}]: We currently have {current_kg} of {ii}")
                logging.debug(f"{self.name} [t = {self.env.now}]: We need {kg_per_drum} kg of {ii} to make one drum of {self.out_material.name}.")
                logging.debug(f"{self.name} [t = {self.env.now}]: I think this the amount of drums we can make given our current amount of {ii}: {drums_possible}")

                mat_to_convert=min(mat_to_convert, kg_possible)
            
            logging.debug(f"{self.name} [t = {self.env.now}]: Mat_to_convert = {mat_to_convert}")
            #order material from intermediate products
            if(mat_to_convert !=0):
                for ii in self.common_isotopes:
                    #Order enough material to cover the expected process loss
                    weight_to_get=mat_to_convert*self.out_material.isotopes[ii]
                    logging.debug(f"{self.name} [t = {self.env.now}]: Getting {weight_to_get}kg of {ii}")
                    converted_isotope = yield self.chem_mba_process[f'{ii}_in_process'].submit_order(weight_to_get, priority=self.priority)
                    actual_loss=converted_isotope*process_loss_distribution(*process_loss_parameters) #processing loss at this step
                    self.chem_mba_toproduct[f'{ii}_to_product'].put(converted_isotope-actual_loss)
                    logging.debug(f"{self.name} [t = {self.env.now}]: Putting {converted_isotope}kg of {ii} to product feed")
                    if(actual_loss>0):
                        self.chem_mba_lostmaterial[f'{ii}_lost_material'].put(actual_loss)

            #Fill drums up to max_drum_throughput
            logging.debug(f"{self.name} [t = {self.env.now}]: Now moving on to drum fill")
            drums_filled=0
            out_of_material=False
            while(drums_filled<conversion_max_drum_throughput):
                dweight = self._drum_weight(self.drum_weight_mean, self.drum_weight_std)
                logging.debug(f"{self.name} [t = {self.env.now}]: Next drum weight = {dweight}kg")

                # check that enough material exists to fill the drum
                for ii in self.common_isotopes:
                    if self.chem_mba_toproduct[f'{ii}_to_product'].level < dweight*self.out_material.isotopes[ii]:
                        logging.debug(f"{self.name} [t = {self.env.now}]: We ran out of {ii} -- level = {self.chem_mba_toproduct[f'{ii}_to_product'].level}, needed = {dweight*self.out_material.isotopes[ii]}")
                        out_of_material=True

                if(not out_of_material):
                    # get the correct isotopes from their respective stores
                    for ii in self.common_isotopes:
                        yield self.chem_mba_toproduct[f'{ii}_to_product'].get(dweight*self.out_material.isotopes[ii])

                    next_drum = Item(self.indexer.next_drum(), dweight, self.env.now, self.name, self.out_material,output_container_type, self.env.now)
                    yield self.shipping_mba.put(next_drum)
                    drums_filled+=1
                    logging.debug(f't={self.env.now}: A drum was filled at {self.name} with weight {next_drum.weight}')
                else:
                    break
            logging.info(f't={self.env.now}: {self.name} filled {drums_filled} {output_container_type}')
           
            #Open drums and place material in process
            num_to_open=min(self.chemistry_mba_drums.check_quantity(), conversion_max_drum_throughput)
            logging.info(f"t={self.env.now}: {self.name} number to open = {num_to_open}, {input_container_type}(s)")

            
            #drums_to_open = yield self.chemistry_mba_drums.submit_order(num_to_open, form=input_container_type, priority=self.priority)
            drums_to_open = yield self.chemistry_mba_drums.submit_order(num_to_open, priority=self.priority)

            #if(len(self.shipping_mba.items) <self.shipping_max_inventory): #test if shipping is full slow down input process
            #    drums_to_open = yield self.chemistry_mba_drums.submit_order(num_to_open, priority=self.priority)
            #else:
            #    drums_to_open=None

            if drums_to_open is not None:
                logging.info(f't={self.env.now}: {self.name} opened {len(drums_to_open)} {input_container_type}(s)')
                for next_drum in drums_to_open:
                    for ii in self.common_isotopes:
                        self.chem_mba_process[f'{ii}_in_process'].put(next_drum.weight*next_drum.what.isotopes[ii])



            yield self.env.timeout(1)

    def initialize_processes(self, env, config, facilities):
        receiving = env.process(self.conversion_receiving(facilities[config['shipping_facility']], **config))
        chemistry = env.process(self.conversion_chemistry(**config))