"""
The MINTs containers module contains implementations of the classes which
implement the Material Balance Areas in the simulation. These include both
Monitored Containers, which are representative of bulk item stores, and Monitored
Filter Stores, which are representative of item stratas in the fuel cycle.
"""

import simpy
import heapq
import itertools
import pandas as pd
from simpy.resources.store import StoreGet, StorePut
from simpy.events import Event, Timeout
from typing import Generator, Callable, NamedTuple
from copy import deepcopy

INVENTORY_COLUMNS = ['id', 'weight', 'when', 'where', 'what', 'form']
INVENTORY_TYPES = [int, float, int, str, str, str]

BULK_INV_COLUMNS = ['week', 'actual_quantity']
BULK_INV_TYPES = [int, float, float]

def record_to_row(item):
    return item.id, dict(zip(INVENTORY_COLUMNS, [item.id, item.weight, item.when, item.where, item.what, item.form]))

class MonitoredContainer(simpy.Container):
    '''
    The MonitoredContainer class is an implementation of a bulk store MBA for the
    fuel cycle simulation. The Monitored Container is expected to contain one material
    type which is added and removed based on weight.

    Inherits Container class from simpy. Appends (time,level) 
    of the container to self.data everytime the level changes (put,get are called))
    '''
    def __init__(self, env, *args, **kwargs):
        super().__init__(env, *args, **kwargs)
        self.env: simpy.Environment = env
        self.inventory: pd.DataFrame = pd.DataFrame({name: pd.Series(dtype=type_) for name, type_ in zip(BULK_INV_COLUMNS, BULK_INV_TYPES)}).set_index('week')
        self.weekly_ins: list[float] = []
        self.weekly_outs: list[float] = []
        self.ins = 0
        self.outs = 0
        self.order_queue: list = []
        self.orders_received: int = 0
        heapq.heapify(self.order_queue)
        self.counter = itertools.count()
        self.processing_event = self.env.event()
        self._trigger_processing()

    def put(self, *args, **kwargs) -> StorePut:
        """Put a quantity of material into a bulk container
        """
        init_level = self.level
        if isinstance(args[0],float): #if input is weight (float) add it to the store
            ret = super().put(*args, **kwargs)
            amount_added = self.level - init_level
            self.ins += amount_added
            return ret

    def get(self, *args, **kwargs) -> StoreGet:
        """Get a quantity of material from the bulk container
        """
        init_level = self.level
        ret = super().get(*args, **kwargs)
        amount_removed = init_level - self.level
        self.outs += amount_removed
        return ret
    
    def _save_inventory_record(self):
        """Save a copy of the current state of the inventory
        """
        data = {'week': self.env.now, 'quantity': self.level}
        df = pd.DataFrame([data]).set_index('week')
        self.inventory = pd.concat([self.inventory, df])
        self.weekly_ins.append(self.ins)
        self.weekly_outs.append(self.outs)
        self.ins = 0
        self.outs = 0

    def generate_ins_and_outs_table(self):
        weeks = range(len(self.weekly_ins))
        return pd.DataFrame({'week':weeks, 'ins':self.weekly_ins, 'outs':self.weekly_outs})
    
    def generate_inventory_table(self) -> pd.DataFrame:
        """Return a dataframe representation of the inventory

        Returns:
            DataFrame: Inventory of container represented as a Pandas DataFrame
        """
        return self.inventory
    
    def submit_order(self, quantity: float | int, priority: int) -> Event:
        """Request a quantity of material from the container with the given priority

        Args:
            quantity (float | int): Quantity of bulk material requested
            priority (int): Priority of requesting facility (lower value = higher priority)

        Returns:
            Event: Simpy Event for request; yielding on return value will suspend the parent
                   process until the order is fufilled
        """
        request = self.env.event()
        count = next(self.counter)
        heapq.heappush(self.order_queue, (priority, count, request, quantity))
        self.orders_received += 1
        self.env.process(self._wait_until_end_of_timestep())
        return request
    
    def _wait_until_end_of_timestep(self):
        '''Ensure all orders for the current timestep are placed before processing'''
        yield self.env.timeout(0)
        self.orders_received -= 1
        if self.orders_received == 0:
            self.processing_event.succeed()
            self.processing_event = self.env.event()
            self._trigger_processing()

    def _trigger_processing(self) -> None:
        """Begin iterating through orders if process is not already running
        """
        if not any(req[2].triggered for req in self.order_queue):  # Run only if not currently triggered
            self.env.process(self._fufill_orders())

    def _fufill_orders(self) -> Generator[StoreGet, Timeout, None]:
        """Iterate through the order queue, fufilling orders or closing requests
        """
        yield self.processing_event
        while self.order_queue:
            priority, count, request, quantity = heapq.heappop(self.order_queue)
            n_available = min(quantity, self.level)
            if n_available > 0:
                yield self.get(n_available)
                request.succeed(n_available)
            else:
                request.succeed(0)
            yield self.env.timeout(0)

class MonitoredFilterStore(simpy.FilterStore):
    '''Inherits from simpy.FilterStore. Updates inventory/data after each get() and push() opperation
    if the inventory has changed
    '''
    def __init__(self, env, *args, **kwargs):
        super().__init__(env, *args, **kwargs)
        self.env: simpy.Environment = env
        self.inventory: dict = dict()
        self.ins: list = []
        self.outs: list = []
        self.weekly_ins: list[list] = []
        self.weekly_outs: list[list] = []
        self.weekly_inventories: list[dict] = []
        self.order_queue: list = []
        self.orders_received: int = 0
        self.pending_additions = 0
        self.pending_subtractions = 0
        heapq.heapify(self.order_queue)
        self.counter = itertools.count() # In the case of multiple requests with same priority, FIFO
        self.processing_event = self.env.event()
        self._trigger_processing()

    def put(self, *args) -> StorePut:
        """Put an item into the store and record into the inventory table

        Returns:
            StorePut: _description_
        """
        ret = super().put(*args)
        id, item_row = record_to_row(args[0])
        self.inventory[id] = item_row
        self.ins.append(id)        
        return ret
        
    
    def get(self, condition, *args) -> StoreGet:
        ret = super().get(condition, *args)           
        return ret

    def remove_from_inventory(self, items):
        ids = [item.id for item in items]
        for id in ids:
            self.outs.append(id)
            del self.inventory[id]
    
    def _save_inventory_record(self):
        """Save a copy of the current state of the inventory for the week plus the in and
            out records for the MBA. Reset ins and outs tracking.
        """
        self.weekly_inventories.append(deepcopy(self.inventory))
        self.weekly_ins.append(self.ins)
        self.weekly_outs.append(self.outs)
        self.ins = []
        self.outs = []

    def generate_ins_and_outs_table(self):
        weeks = range(len(self.weekly_ins))
        return pd.DataFrame({'week':weeks, 'ins':self.weekly_ins, 'outs':self.weekly_outs})

    def generate_inventory_table(self):
        combined_df = pd.DataFrame()  # Initialize with an empty DataFrame
        for i, weekly_dict in enumerate(self.weekly_inventories):
            if len(weekly_dict) == 0:
                continue
            week_df = pd.DataFrame(weekly_dict.values())
            week_df['week'] = [i] * len(week_df)
            combined_df = pd.concat([combined_df, week_df], ignore_index=True)
        return combined_df

    @staticmethod
    def _item_filter_lambda(material: str, form: str) -> Callable[[NamedTuple], bool]:
        return lambda item: ((material is None or item.what == material) and (form is None or item.form == form))
    
    def check_quantity(self, material=None, form=None) -> int:
        """Check quantity, taking into account arrival time

        TODO: Add filtering based on item isotopics (material) and form
        to implement container which store multiple item types.

        Args:
            material (_type_, optional): Material type to search for. Defaults to None.
            form (_type_, optional): Item form to search for, e.g. 'drum'. Defaults to None.

        Returns:
            int: Number of items in the store matching the search parameters
        """
        temp = [x for x in self.items if x.arrival_time!=self.env.now]
        return len(temp)

    def check_quantity_present(self, material=None, form=None) -> int:
        """Check quantity method which ignores arrival time"""
        return len(self.items)
        
    def submit_order(self, quantity: int, material: str = None, form: str = None, priority: int = 1) -> Event:
        """Submit a retrieval order based on material type, form, and priority."""
        request = self.env.event()
        count = next(self.counter)
        condition = self._item_filter_lambda(material, form)
        heapq.heappush(self.order_queue, (priority, count, request, quantity, condition))
        self.orders_received += 1
        self.env.process(self._wait_until_end_of_timestep())
        return request
    
    def _wait_until_end_of_timestep(self):
        '''Ensure all orders for the current timestep are placed before processing'''
        yield self.env.timeout(0)
        self.orders_received -= 1
        if self.orders_received == 0:
            self.processing_event.succeed()
            self.processing_event = self.env.event()
            self._trigger_processing()

    def _trigger_processing(self) -> None:
        """If there is not already a process running for serving orders, start one
        """
        if not any(req[2].triggered for req in self.order_queue):
            self.env.process(self._fulfill_orders())

    def _fulfill_orders(self) -> Generator[StoreGet, Timeout, None]:
        """Fufill all orders in the order queue

        Should run once per timestep, at the end of the timestep.

        Yields:
            Generator[StoreGet, Timeout, None]: _description_
        """
        yield self.processing_event
        while self.order_queue:
            priority, count, request, quantity, condition = heapq.heappop(self.order_queue) # pops lowest priority, breaking ties by timestep order was submitted
            
            fulfilled_items = []
            for _ in range(quantity):
                # Attempt to get each required item, if available
                if not any(condition(i) for i in self.items):
                    break
                try:
                    item = yield self.get(condition)
                    if item.arrival_time == self.env.now: #items come out in FIFO order so once we reach the first all others have same or later arrival time
                        yield self.put(item) #put the item back
                        break
                    fulfilled_items.append(item)
                except simpy.Interrupt:
                    break

            if len(fulfilled_items) == 0:
                # If nothing available, return None
                request.succeed(None)
            
            else:
                # Succeed the request with the collected items
                self.remove_from_inventory(fulfilled_items)
                request.succeed(fulfilled_items)

            yield self.env.timeout(0)
