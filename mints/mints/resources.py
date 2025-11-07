'''Contains the Data Structures used throughout the simulation,
Items: drums, pellet_batches,rods, and assemblies
materials : U02, U308, O2, U02r
Indexer : assigns each item a unique index in the simulation
Can be loaded alone to explore the database output'''
from __future__ import annotations
import numpy as np

class Item(object):
    '''
    Class attributes:
        id : global id from Global_Index
        weight : weight of material (kg) in the Item
        when : timestep when the Item was created
        where : facility name where the Item was created
        what : material the Item contains
        form: the physical form of the material (powder, rod, etc.)
    '''
    def __init__(self,
                 id: int,
                 weight: float,
                 when: int,
                 where: str,
                 what: str,
                 form: str,
                 arrival_time: int):
        self.id = id
        self.weight = weight
        self.when = when
        self.where = where
        self.what = what
        self.form = form
        self.arrival_time = arrival_time
        # Shipping history is a list of tuples containing (arrival_time, arrival_location)
        self.shipping_history = []

    def update_arrival_time(self, arrival_time: int, new_location: str):
        self.shipping_history.append((self.arrival_time, self.where))
        self.arrival_time = arrival_time
        self.where = new_location

    def __str__(self):
        return f'ID: {self.id} - WEIGHT: {self.weight} - WHEN: {self.when} - WHERE: {self.where} - WHAT: {self.what} - FORM: {self.form}'

class Drum(Item):
    def __init__(self, id, weight, when, where, what, arrival_time):
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form='drum', arrival_time=arrival_time)

class Pellet_Batch(Item):
    def __init__(self, id, weight, when, where, what, arrival_time):
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form='pellet', arrival_time=arrival_time)

class Rod(Item):
    def __init__(self, id, weight, when, where, what, arrival_time):
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form='rod', arrival_time=arrival_time)

class Assembly(Item):
    def __init__(self, id, weight, when, where, what, arrival_time):
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form='assembly', arrival_time=arrival_time)

class Cylinder(Item):
    def __init__(self, id: int, weight: float, when: int, where: str, what: Material, arrival_time: int, type: str ='30B'):
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form=f'cylinder_{type.lower()}', arrival_time=arrival_time)

class Material(object):
    def __init__(self, name: str, isotopes:dict[str,float], **kwargs):
        self.name: str = name
        self.isotopes: dict = isotopes
        self.irradiated: bool = False
        self.enrichment: float = None

    def transmute(self, isotopes:dict[str,float]):
        raise NotImplementedError("The 'transmute' method should be implemented by each chemical subclass")
    
    def __str__(self):
        out_str = f'{self.name} ({self.isotopes})'
        if self.irradiated:
            out_str += ' - irradiated'
        if self.enrichment is not None:
            out_str += f' - enrichment = {self.enrichment}'
        return out_str

class UraniumDioxide(Material):
    def __init__(self, name: str = 'UO2', isotopes: dict = {"U235":0.0061,"U238":0.87544,"O":0.11845}, enrich_pct=None, pu_pct=None, **kwargs):
        super().__init__(name, isotopes)
        if enrich_pct is not None:
            self.enrich(enrich_pct)
        if pu_pct is not None:
            self.irradiate(pu_pct)

    def irradiate(self, pu_pct: float):
        self.irradiated = True
        self.name += '_irradiated'
        if pu_pct == .0023:
            self.name = 'UO2r'
            self.isotopes = {"U235":0.001,"U238":0.84218,"O":0.1845,"Pu":.0023}
        elif pu_pct == .001:
            # LWR 1
            self.isotopes = {"U235":0.021,"U238":0.7915,"O":0.1845,"Pu":.003}
        elif pu_pct == .002:
            # LWR 2 0.         0  000000                                 
            self.isotopes = {"U235":0.011,"U238":0.8025,"O":0.1845,"Pu":.002}
        elif pu_pct == .003:
            # LWR 3
            self.isotopes = {"U235":0.001,"U238":0.8135,"O":0.1845,"Pu":.001}
        else:
            raise NotImplementedError("A better way to handle irradiation is coming soon")

    def enrich(self, pct: float):
        """Enrich UO2 to pct enrichment

        Args:
            pct (float): enrichment level

        Raises:
            NotImplementedError: _description_

        Returns:
            _type_: _description_
        """
        pct_str = 100*pct
        self.name += f'{pct_str}_enriched'
        if pct == .05:
            self.isotopes = {"U235":0.04260,"U238":0.81965,"O":0.11601}
        elif pct == .1:
            self.isotopes = {"U235":0.08713,"U238":0.79421,"O":0.11865}
        else:
            raise NotImplementedError("A better way to handle enrichment is coming soon!")

class UraniumHexaFlouride(Material):
    def __init__(self, name='UF6', isotopes={"U235":0.00467,"U238":0.67145,"F":0.32388}, enrich_pct=None, depletion_pct=None, **kwargs):
        super().__init__(name, isotopes)
        if enrich_pct is not None:
            self.enrich(enrich_pct)
        if depletion_pct is not None:
            self.deplete(depletion_pct)

    def enrich(self, pct: float):
        """Enrich UF6 to pct percent U235 enrichment

        Args:
            pct (float): _description_
        """
        pct_str = 100*pct
        self.name += f'_{pct_str}_enriched'
        if pct == .05:
            self.isotopes = {"U235":0.03339,"U238":0.64260,"F":0.32400}
        elif pct == .1:
            self.isotopes = {"U235":0.06681,"U238":0.60904,"F":0.32414}
        else:
            raise NotImplementedError("A better way to handle this is coming soon")

    def deplete(self, pct: float = .003):
        if pct == .003:
            self.isotopes = {"U235":0.00033,"U238":0.67580,"F":0.32387}

class TriuraniumOctoxide(Material):
    def __init__(self, name='U3O8', isotopics={"U235":0.00586,"U238":0.84218,"O":0.152}, **kwargs):
        super().__init__(name, isotopics)

class Flouride(Material):
    def __init__(self, name="F", isotopics={'F':1}, **kwargs):
        super().__init__(name, isotopics)

class Oxygen(Material):
    def __init__(self, name='O', isotopics={'O':1}, **kwargs):
        super().__init__(name, isotopics)

STR_TO_MAT = {'UO2': UraniumDioxide,
              'UF6': UraniumHexaFlouride,
              'U3O8': TriuraniumOctoxide,
              'F': Flouride,
              'O': Oxygen}

def aggregate_isotopics(materials_list: list[dict]):
    return materials_list[0]

class BatchedResource(Item):
    def __init__(self,
                 id,
                 when,
                 where,
                 what,
                 arrival_time,
                 batch_size=0,
                 weights=None,
                 weight_distribution=np.random.normal,
                 weight_distribution_parameters=[.02,.005],
                 resource_type: str = ''):
        super().__init__(id, 0, when, where, what, resource_type, arrival_time)
        #if weights are provided use them, else draw weights from distribution
        self.form = resource_type
        self.weights_list: np.ndarray = None
        if(weights is None):
            self.weights_list=np.asarray(weight_distribution(*weight_distribution_parameters, batch_size))
        else:
            self.weights_list=np.asarray(weights)
        
        self.sample_counter: int = 0
        self.batch_size: int = batch_size
        self.weight: float = self.aggregate_weights()
        self.arrival_time=arrival_time

    def sample_batch(self, num_to_sample: int) -> BatchedResource:
        raise NotImplementedError("Batched resource must implement self.sample_batch")
    
    def sample(self, num_to_sample: int) -> tuple[list, dict]:
        raise NotImplementedError("Batched resource must implement self.sample")

    def extend_batch(self, num_to_append: int) -> None:
        raise NotImplementedError("Batched resource must implement self.extend_batch")

    def aggregate_weights(self) -> float:
        raise NotImplementedError("Batched resource must implement self.aggregate_weights")

    def aggregate_isotopics(self) -> dict:
        raise NotImplementedError("Batched resource must implement self.aggregate_isotopics")

class HomogenousBatchedResource(BatchedResource):
    def __init__(self,
                 id: int,
                 when: int,
                 where: str,
                 what: dict,
                 arrival_time: int,
                 batch_size: int = 0,
                 weights: list[float] | None = None,
                 weight_distribution: callable = np.random.normal,
                 weight_distribution_parameters: tuple =[.02, .005],
                 resource_type: str = ''):
        super().__init__(id, when, where, what, arrival_time, batch_size=batch_size, weights=weights,
                         weight_distribution=weight_distribution,
                         weight_distribution_parameters=weight_distribution_parameters,
                         resource_type=resource_type)

    def extend_batch(self, in_batch: BatchedResource) -> None:
        if in_batch.what != self.what:
            raise ValueError("Cannot combine different material types which homogenous batch")
        
        self.batch_size += in_batch.batch_size
        self.weights_list = np.concatenate([self.weights_list, in_batch.weights_list])
        self.weight = self.aggregate_weights()
        
    #function to get pellets of specific material returned as a new stuff_batch
    def sample(self, num_to_sample: int) -> tuple[list, dict]:
        weights = self.weights_list[self.sample_counter:self.sample_counter+num_to_sample]
        self.sample_counter += num_to_sample
        self.batch_size -= num_to_sample
        self.weight = self.aggregate_weights()
        return weights, self.what

    def aggregate_weights(self):
        return np.sum(self.weights_list[self.sample_counter:])
    
    def aggregate_isotopics(self):
        return self.what


''' Global indexer maintains current index for each type of Item.
When a new item is created at any facility it gets a unique index
'''
class Global_Index:
    def __init__(self):
        self.drum_index=0
        self.pellet_index=0
        self.rod_index=0
        self.assembly_index=0
    #functions store and retrieve the next index for each item type
    def next_drum(self):
        self.drum_index = self.drum_index+1
        return self.drum_index
    def next_pellet(self):
        self.pellet_index=self.pellet_index+1
        return self.pellet_index
    def next_rod(self):
        self.rod_index = self.rod_index+1
        return self.rod_index
    def next_assembly(self):
        self.assembly_index=self.assembly_index+1
        return self.assembly_index