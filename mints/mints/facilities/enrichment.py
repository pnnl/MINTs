import numpy as np
import numpy as np
import logging
from mints.facilities import SimulationFacility
from mints.facilities.conversion import Conversion
from mints.containers import *
from mints.resources import *

class Enrichment(SimulationFacility):
    '''Enrichment facility class
    received containers of {in_material} are placed in receiving store, and then moved to the cascade_mba. Containers are opened and place
    in the cascade stores. Prodcut {product_material} and tails {tail_material} are moved from cascade stores to containers
    for shipping or storage

    receivingstore {MonitoredFilterStore} :Contains containers of {in_material} shipped from shipper
    cascade_mba {MonitoredFilterStore} :Contains containers of {in_material} moved from recieving to the cascade mba (unopened)
    oxygenstore    {MonitoredContainer}   :Contains Oxygen(kg)  represents the isope in process in the cascade
    u235store      {MonitoredContainer}   :Contains u235(kg)    represents the isope in process in the cascade
    u238store      {MonitoredContainer}   :Contains u238(kg)    represents the isope in process in the cascade
    cascade_feed_bulk         {MonitoredContainer}   :Contains bulk {in_material} to be fed into the cascade
    cascade_product_bulk      {MonitoredContainer}   :Contains bulk {product_material} to be moved into containers
    shippingstore  {MonitoredFilterStore} :Contains containers of {product_material} for shipping
    priority            {int}: Facilities priority when ordering {in_material} from {shipper}
    product_rate        {float}: Max kg product to produce each timestep
    feed_material       {mints.material}: Feed material for the cascade
    product_material    {mints.material}: Product material produced from cascade
    tail_material       {mints.material}: Tail material to remove from cascade

    
    '''
    def __init__(self,
                 name,
                 env,
                 indexer,
                 priority=1,
                 product_rate=36822,
                 feed_material: str | Material = UraniumHexaFlouride,
                 feed_enrichment: float = None,
                 product_material: str | Material = UraniumHexaFlouride,
                 product_enrichment: float = 0.05,
                 tail_material: str | Material = UraniumHexaFlouride,
                 tail_depletion: float = 0.003,
                 out_fill_weight_dist=np.random.normal,
                 **kwargs):
        super().__init__(name, env, indexer)

        # Instantiate feed material type
        if isinstance(feed_material, str):
            feed_material = STR_TO_MAT[feed_material]
        self.feed_material: Material = feed_material(enrich_pct = feed_enrichment)

        # Instantiate product material type
        if isinstance(product_material, str):
            product_material = STR_TO_MAT[product_material]
        self.product_material: Material = product_material(enrich_pct = product_enrichment)

        # Instantiate tail material type
        if isinstance(tail_material, str):
            tail_material = STR_TO_MAT[tail_material]
        self.tail_material: Material = tail_material(depletion_pct=tail_depletion)
        
        # Receiving MBA
        self.receiving_mba = MonitoredFilterStore(env)

        # Enrichment Cascade MBA
        self.cascade_mba = MonitoredFilterStore(env)
        self.oxygenstore = MonitoredContainer(env)
        self.u235store = MonitoredContainer(env)
        self.u238store = MonitoredContainer(env)
        self.cascade_product_bulk = MonitoredContainer(env)
        self.cascade_feed_bulk = MonitoredContainer(env)


        # Shipping MBA
        self.shipping_mba = MonitoredFilterStore(env)
        self.priority=priority

        # Cascade Parameters
        self.product_rate = product_rate            #amount of enriched product to make each timestep

        # Compute the Derived parameters
        self.cascade_cut=(self.feed_material.isotopes["U235"]-self.tail_material.isotopes["U235"])/(self.product_material.isotopes["U235"]-self.tail_material.isotopes["U235"])
        self.cascade_feed_rate=self.product_rate/self.cascade_cut
        self.cascade_waste_rate=self.product_rate/(1-self.cascade_cut)
        #initialize cascade distributions
        x=np.linspace(0,10,10)
        c=-self.cascade_feed_rate/np.log(self.product_rate/self.cascade_feed_rate)
        self.enrichment_steps=(self.cascade_feed_rate*np.exp(-x/c))/self.cascade_feed_rate
        self.cascade_up=np.zeros(10)
        #print(self.enrichment_steps)
        #plt.plot(self.enrichment_steps)

        # Ouput cylinder weights
        self._out_weight: callable = out_fill_weight_dist
        self._drum_weight: callable = out_fill_weight_dist

    def dict_of_stores(self):
        return {'receiving_mba':        self.receiving_mba,
                'cascade_mba':        self.cascade_mba,
                'oxygen_store':         self.oxygenstore,
                'u235_store':           self.u235store,
                'u238_store':           self.u238store,
                'cascade_product_bulk': self.cascade_product_bulk,
                'cascade_feed_bulk':   self.cascade_feed_bulk,
                'shipping_mba':         self.shipping_mba}

    def enrichment_receiving(self,
                             shipper: Conversion,
                             receiving_drum_throughput=7,
                             receiving_max_inventory=40,
                             **kwargs):
        '''
        Gets drums for shipper, put into receiving mba
        stores by isotope
        '''
        while True:
            #order drums from the shipper
            num_to_order=min(receiving_drum_throughput,receiving_max_inventory-self.receiving_mba.check_quantity())
            #print(f'shipper items {shipper.shipping_mba.inventory_count}, max_av_in ={max_inventory-self.receiving_mba.inventory_count}')
            #print(f'{num_to_order} ordered at {self.env.now}')

            drums_received = yield shipper.shipping_mba.submit_order(num_to_order, priority=self.priority)
            if drums_received is not None:
                logging.info(f'En recieved items {len(drums_received)} at t = {self.env.now}')

            #timeout so goods appear in the next timestep
            yield self.env.timeout(1)

            if drums_received is not None:
                self.place_items(self.receiving_mba, drums_received)
                logging.info(f'conversion ordered {num_to_order} at time = {self.env.now} and received {len(drums_received)}')

    def enrichment_cascade(self,
                           cascade_max_drum_throughput=10,
                           process_loss=0,
                           input_container_type='cylinder40y',
                           out_fill_weight_mean_kg=2277,
                           out_fill_weight_std_kg=0.1,
                           out_container='cylinder30b',
                           **kwargs):
        '''
        Gets isotopes from bulk stores and creates drums of
        output material by % weight of isotopes
        max_drum_througput {int} :Maximum number of drums that can be converted in one timestep
        process_loss {float} : Process loss, (1+process_loss) material is taken from stores for each 1 material converted 
        '''
        while True:
            #Open enough drums for  drum_throughput barrels (or as many as possible) and move into isotope stores
            #.962 kg u3o8/ kg uo2
            num_to_get=min(self.receiving_mba.check_quantity(), np.ceil(cascade_max_drum_throughput*.962).astype(int))

            drums_to_cascade_mba = yield self.receiving_mba.submit_order(num_to_get, priority=self.priority)
            if drums_to_cascade_mba is not None:
                logging.info(f'{len(drums_to_cascade_mba)} drums to move to enrichemnt cascade conversion chem time={self.env.now}')
                self.place_items(self.cascade_mba, drums_to_cascade_mba)

            #putting material into the cascade
            num_to_open=np.floor(min(self.cascade_mba.check_quantity(), self.cascade_feed_rate/400)).astype(int)
            logging.info(f"{self.env.now}: Cascade mba # to open = {num_to_open}")
            for _ in range(num_to_open):
                # Retrieve drum
                next_drum = yield self.cascade_mba.submit_order(1,  priority=self.priority) #can we order all of these drums at once?
                if next_drum is not None:
                    self.cascade_feed_bulk.put(next_drum[0].weight)
                    logging.info(f'drum {next_drum[0].id} opened at enrichment time={self.env.now}\n')
                else:
                    logging.info(f'Expected more drums to be available to open')

            #Compute output material to move to product
            product_in_cascade=self.cascade_up[-1]
            if(product_in_cascade>0):
                self.cascade_product_bulk.put(product_in_cascade)
                self.cascade_up[-1]=0
            elif(product_in_cascade<0):
                print("SOMETHING WENT WRONG IN CASCADE")

            #Update the quantities in the cascade
            self.cascade_up=np.roll(self.cascade_up,1)*self.enrichment_steps
            #Add feed material to cascade
            kg_to_feed=min(self.cascade_feed_rate,self.cascade_feed_bulk.level)
            if(kg_to_feed>0):
                yield self.cascade_feed_bulk.get(kg_to_feed)
                self.cascade_up[0]=kg_to_feed
                #print(f'{kg_to_feed} fed into cascade')
            elif(kg_to_feed<0):
                print("SOMETHING WENT WRONG IN CASCADE PARTII")

            #Fill up to drum throughput containers
            containers_filled=0
            while(containers_filled<cascade_max_drum_throughput):
                dweight=self._drum_weight(out_fill_weight_mean_kg, out_fill_weight_std_kg)
                if(dweight<=self.cascade_product_bulk.level):
                    yield self.cascade_product_bulk.get(dweight)
                    next_container=Cylinder(self.indexer.next_drum(), dweight, self.env.now, self.name, self.product_material, self.env.now, out_container)
                    yield self.shipping_mba.put(next_container)
                    containers_filled+=1
                    logging.info(f'A container filled at {self.name} with weight {dweight} at t={self.env.now}')
                else:
                    break
            logging.info(f'{containers_filled} containers filled at {self.name} at t={self.env.now}')

            yield self.env.timeout(1)

    def initialize_processes(self, env, config, facilities):
        receiving = env.process(self.enrichment_receiving(facilities[config['shipping_facility']], **config))
        cascade = env.process(self.enrichment_cascade(**config))
