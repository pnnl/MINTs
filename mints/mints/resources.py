'''
The Resources module contains implementations for classes representing Items and Materials
in the fuel cycle simulation.

Items are simulation entities such as drums of material, fuel assemblies, batches of pellets, etc.

Materials are representative of specific chemical resources (e.g. UO2, U3O8), and maintain the name
of the material as well as the material isotopics, enrichment, etc.
'''
from __future__ import annotations
import numpy as np

class Item(object):
    '''
    The Item class is used to represent items within the fuel cycle.
    Each item has a unique id, and maintains information on its weight, where it is from,
    when during the simulation is was created, and what it is made out of.

    Attributes:
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

    def update_arrival_time(self, arrival_time: int, new_location: str) -> None:
        """Update the location history of the item when it is shipped to a new location

        For reporting at the end of the fuel cycle simulation, each item maintains a list of
        every facility it has been to and during what timesteps it was located there.

        Args:
            arrival_time (int): Time item arrived at the new facility
            new_location (str): Name of the facility the item has arrived at
        """
        self.shipping_history.append((self.arrival_time, self.where))
        self.arrival_time = arrival_time
        self.where = new_location

    def __str__(self) -> str:
        """Generate string representation of the item

        Returns:
            str: String representation of item
        """
        return f'ID: {self.id} - WEIGHT: {self.weight} - WHEN: {self.when} - WHERE: {self.where} - WHAT: {self.what} - FORM: {self.form}'

class Drum(Item):
    """Item class wrapper for drums.
    """
    def __init__(self, id: int, weight: float, when: int, where: str, what: Material, arrival_time: int):
        """Instantiate new drum item

        Args:
            id (int): Id of new drum
            weight (float): weight of new drum
            when (int): timestep of item creation
            where (str): current location (facility) of item
            what (Material): Material type stored in drum
            arrival_time (int): Time arrived at current facility
        """
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form='drum', arrival_time=arrival_time)

class Pellet_Batch(Item):
    """Item class wrapper for batches of pellets
    """
    def __init__(self, id: int, weight: float, when: int, where: str, what: Material, arrival_time: int):
        """Create new Pellet Batch item

        Args:
            id (int): ID of pellet batch
            weight (float): Total weight of pellet batch
            when (int): Timestep of creation
            where (str): Facility where the pellet batch was created
            what (Material): Material type of pellets
            arrival_time (int): Time item arrived at current facility
        """
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form='pellet', arrival_time=arrival_time)

class Rod(Item):
    """Item class wrapper for fuel rods
    """
    def __init__(self, id: int, weight: float, when: int, where: str, what: Material, arrival_time: int):
        """Create a new fuel rod item

        Args:
            id (int): ID of fuel rod
            weight (float): Total weight of fuel rod
            when (int): Time of item creation
            where (str): Location of item creation
            what (Material): Material type of fuel rod
            arrival_time (int): Timestep fuel rod arrived at current facility
        """
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form='rod', arrival_time=arrival_time)

class Assembly(Item):
    """Item class wrapper for fuel assemblies
    """
    def __init__(self, id: int, weight: float, when: int, where: str, what: Material, arrival_time: int):
        """Create a new fuel assembly item

        Args:
            id (int): ID of fuel assembly
            weight (float): Total weight of material in the fuel assembly
            when (int): Timestep of fuel assembly creation
            where (str): Location (facility) of fuel assembly creation
            what (Material): Material type of fuel assembly
            arrival_time (int): Time assembly arrived at current facility
        """
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form='assembly', arrival_time=arrival_time)

class Cylinder(Item):
    """Item class wrapper for cylinders
    """
    def __init__(self, id: int, weight: float, when: int, where: str, what: Material, arrival_time: int, type: str ='30B'):
        """Create new cylinder item

        Args:
            id (int): ID of new cylinder
            weight (float): Total weight of material in cylinder
            when (int): Timestep of cylinder creation
            where (str): Location of cylinder creation
            what (Material): Material type of cylinder
            arrival_time (int): Time cylinder arrived at current facility
            type (str, optional): Specific type of cylinder. Defaults to '30B'.
        """
        super().__init__(id=id, weight=weight, when=when, where=where, what=what, form=f'cylinder_{type.lower()}', arrival_time=arrival_time)

class Material(object):
    """Class for representing materials in the fuel cycle simulation

    Materials are specific chemical compositions of resources within the fuel cycle.
    The material class tracks the name of material type which is typically the chemical
    formula of the material (e.g., U3O8), a dictionary of the isotopic breakdown of the
    material, a boolean indicating if the material has been irradiated, and a boolean
    indicating if the material has been enriched beyond natural enrichment levels.
    """
    def __init__(self, name: str, isotopes:dict[str,float], **kwargs):
        """Initialize material

        Args:
            name (str): Chemical formula for material
            isotopes (dict[str,float]): Dictionary of isotopes/elements and their relative proportions
        """
        self.name: str = name
        self.isotopes: dict = isotopes
        self.irradiated: bool = False
        self.enrichment: float = None
    
    def __str__(self) -> str:
        """Return a string representation of the material

        Returns:
            str: String representation of the material
        """
        out_str = f'{self.name} ({self.isotopes})'
        if self.irradiated:
            out_str += ' - irradiated'
        if self.enrichment is not None:
            out_str += f' - enrichment = {self.enrichment}'
        return out_str

class UraniumDioxide(Material):
    """Material wrapper for Uranium Dioxide
    """
    def __init__(self,
                 name: str = 'UO2',
                 isotopes: dict = {"U235":0.0061,"U238":0.87544,"O":0.11845},
                 enrich_pct: float | None = None,
                 pu_pct: float | None = None,
                 **kwargs):
        """Initialize UO2 material

        Args:
            name (str, optional): Name of material. Defaults to 'UO2'.
            isotopes (dict, optional): Isotopes and relative proportions. Defaults to {"U235":0.0061,"U238":0.87544,"O":0.11845}.
            enrich_pct (float, optional): Percent u23 enrichment. Defaults to None.
            pu_pct (float, optional): Proportion of Pu content from irradiation. Defaults to None.
        """
        super().__init__(name, isotopes)
        if enrich_pct is not None:
            self.enrich(enrich_pct)
        if pu_pct is not None:
            self.irradiate(pu_pct)

    def irradiate(self, pu_pct: float):
        """Modify isotopes to simulate irradiation

        Currently this method only supports a variety of hard-coded percentages
        as part of the fuel cycles for PHWR and LWR reactors. In the future we
        plan to make this modification continous.

        Args:
            pu_pct (float): Percent plutonium

        Raises:
            NotImplementedError: Selected plutonium percentage is not implemented.
        """
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

    def enrich(self, pct: float) -> None:
        """Enrich UO2 to pct enrichment

        Args:
            pct (float): enrichment level

        Raises:
            NotImplementedError: If enrichment level is not yet implemented
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
    """Material wrapper for Uranium Hexaflouride
    """
    def __init__(self,
                 name: str='UF6',
                 isotopes: dict = {"U235":0.00467,"U238":0.67145,"F":0.32388},
                 enrich_pct: float = None,
                 depletion_pct: float = None,
                 **kwargs):
        """Initialize material class for UF6

        Args:
            name (str, optional): Chemical formula. Defaults to 'UF6'.
            isotopes (dict, optional): Isotopes in material and their relative proportions. Defaults to {"U235":0.00467,"U238":0.67145,"F":0.32388}.
            enrich_pct (float, optional): Percent U235 enrichment. Defaults to None.
            depletion_pct (float, optional): Percentage depletion. Defaults to None.
        """
        super().__init__(name, isotopes)
        if enrich_pct is not None:
            self.enrich(enrich_pct)
        if depletion_pct is not None:
            self.deplete(depletion_pct)

    def enrich(self, pct: float):
        """Enrich UF6 to pct percent U235 enrichment

        Args:
            pct (float): percentage of U235 enrichment
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
        """Deplete the level of U235 in isotopes down to pct

        This method exists in order to simulate depleted UF6 as a tail product from
        UF6 enrichment. Currently only one hardcoded percentage is supported.

        Args:
            pct (float, optional): Percentage of u235 in isotopes. Defaults to .003.
        """
        if pct == .003:
            self.isotopes = {"U235":0.00033,"U238":0.67580,"F":0.32387}

class TriuraniumOctoxide(Material):
    """Material class wrapper for U3O8
    """
    def __init__(self,
                 name: str = 'U3O8',
                 isotopics: dict = {"U235":0.00586,"U238":0.84218,"O":0.152},
                 **kwargs):
        """Initialize U3O8 material

        Args:
            name (str, optional): Chemical formula of material. Defaults to 'U3O8'.
            isotopics (_type_, optional): Isotopics of material. Defaults to {"U235":0.00586,"U238":0.84218,"O":0.152}.
        """
        super().__init__(name, isotopics)

class Flouride(Material):
    """Material class wrapper for flouride
    """
    def __init__(self,
                 name: str ="F",
                 isotopics: dict = {'F':1},
                 **kwargs):
        """Initialize Flouride material

        Args:
            name (str, optional): Chemical formula of material. Defaults to "F".
            isotopics (_type_, optional): Isotopics of material. Defaults to {'F':1}.
        """
        super().__init__(name, isotopics)

class Oxygen(Material):
    """Material class wraper for Oxygen.
    """
    def __init__(self,
                 name: str ='O',
                 isotopics: dict = {'O':1},
                 **kwargs):
        """Initialize oxygen material 

        Args:
            name (str, optional): Chemical formula of material. Defaults to 'O'.
            isotopics (_type_, optional): Isotopics of material. Defaults to {'O':1}.
        """
        super().__init__(name, isotopics)

# This dictionary serves as a reference between chemical formula names
# and their associated Material classes
STR_TO_MAT = {'UO2': UraniumDioxide,
              'UF6': UraniumHexaFlouride,
              'U3O8': TriuraniumOctoxide,
              'F': Flouride,
              'O': Oxygen}

def aggregate_isotopics(materials_list: list[dict]):
    """Aggregate the isotopics across a list of materials

    #TODO: Implement this aggregation process. Currently, this just returns
    the isotopics of the first element.

    Args:
        materials_list (list[dict]): List of isotopics dictionaries

    Returns:
        dict: Aggregated isotopics
    """
    return materials_list[0]

class BatchedResource(Item):
    """Class for combining multiple items into a single unit

    The BatchedResource class is a base class for combining multiple Items into a single Item unit.
    This process of batching items allows for easier computation and more convience when moving groups
    of material through the fuel cycle (e.g., combining multiple fuel rods into a single assembly)
    """
    def __init__(self,
                 id: int,
                 when: int,
                 where: str,
                 what: Material,
                 arrival_time: int,
                 batch_size: int =0,
                 weights: list = None,
                 weight_distribution: callable = np.random.normal,
                 weight_distribution_parameters: tuple = [.02,.005],
                 resource_type: str = ''):
        """Initialize a batch of items

        A batch of items can either be instantiated by passing a list of pre-generated weights
        as the 'weights' argument to this function, or if no weights are specified the class will
        use the specified weight distribution and parameters to generate a list of weights with length
        batch_size.

        Args:
            id (int): Unique ID for the batch
            when (int): Time of batch creation 
            where (str): Facility where the batch was created
            what (Material): Material type of the batch items
            arrival_time (int): The timestep when the item arrived at the current facility
            batch_size (int, optional): Number of items in the batch. Defaults to 0.
            weights (list, optional): List of weights of the items in the batch. Defaults to None.
            weight_distribution (callable, optional): Distribution of item weights for batch creation. Defaults to np.random.normal.
            weight_distribution_parameters (tuple, optional): parameters for item weight distribution. Defaults to [.02,.005].
            resource_type (str, optional): Physical form of resource. Defaults to ''.
        """
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
    """BatchedResource class for batches where all items have same isotopics
    """
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
        """Initialize a batch of items

        A batch of items can either be instantiated by passing a list of pre-generated weights
        as the 'weights' argument to this function, or if no weights are specified the class will
        use the specified weight distribution and parameters to generate a list of weights with length
        batch_size.

        The homogenous batched resource assumes that all items within the batch have the same isotopics, and therefore
        aggregation can be streamlined and sampling can be simplified.

        Args:
            id (int): Unique ID for the batch
            when (int): Time of batch creation 
            where (str): Facility where the batch was created
            what (Material): Material type of the batch items
            arrival_time (int): The timestep when the item arrived at the current facility
            batch_size (int, optional): Number of items in the batch. Defaults to 0.
            weights (list, optional): List of weights of the items in the batch. Defaults to None.
            weight_distribution (callable, optional): Distribution of item weights for batch creation. Defaults to np.random.normal.
            weight_distribution_parameters (tuple, optional): parameters for item weight distribution. Defaults to [.02,.005].
            resource_type (str, optional): Physical form of resource. Defaults to ''.
        """
        super().__init__(id, when, where, what, arrival_time, batch_size=batch_size, weights=weights,
                         weight_distribution=weight_distribution,
                         weight_distribution_parameters=weight_distribution_parameters,
                         resource_type=resource_type)

    def extend_batch(self, in_batch: BatchedResource) -> None:
        """Combine this batch of items with a new batch.

        Args:
            in_batch (BatchedResource): Batched resource to combine with this batch of items.

        Raises:
            ValueError: To combine multiple homogenous batched resources, the batches must be of the same material type.
        """
        if in_batch.what != self.what:
            raise ValueError("Cannot combine different material types which homogenous batch")
        
        self.batch_size += in_batch.batch_size
        self.weights_list = np.concatenate([self.weights_list, in_batch.weights_list])
        self.weight = self.aggregate_weights()
        
    #function to get pellets of specific material returned as a new stuff_batch
    def sample(self, num_to_sample: int) -> tuple[list, dict]:
        """Sample num_to_sample items from the batch

        sample_counter is used to track the number of items already sampled from this batch.
        After sampling is completed and the items are retrieved, the total batch weight is 
        re-aggregated.

        Args:
            num_to_sample (int): Number of items to sample

        Returns:
            tuple[list, dict]: The sampled weights and the material type of the items
        """
        weights = self.weights_list[self.sample_counter:self.sample_counter+num_to_sample]
        self.sample_counter += num_to_sample
        self.batch_size -= num_to_sample
        self.weight = self.aggregate_weights()
        return weights, self.what

    def aggregate_weights(self):
        """Get the total weight of the items in the batch

        Returns:
            float: Total weight of the items in the batch
        """
        return np.sum(self.weights_list[self.sample_counter:])
    
    def aggregate_isotopics(self) -> Material:
        """Aggregate the isotopics of the batch

        As this is assumed to be a homogenous batch, we know all items have the same isotopic
        breakdown and do not need to perform aggregation of the isotopics.

        Returns:
            Material: The Material type of the batch
        """
        return self.what

class Global_Index:
    ''' Global indexer maintains current index for each type of Item.
    When a new item is created at any facility it gets a unique index
    '''
    def __init__(self):
        """Initialize the global indexer
        """
        self.drum_index=0
        self.pellet_index=0
        self.rod_index=0
        self.assembly_index=0

    #functions store and retrieve the next index for each item type
    def next_drum(self) -> int:
        """Get the index of the next drum created in the simulation

        Returns:
            int: The index of the new drum
        """
        self.drum_index = self.drum_index+1
        return self.drum_index
    
    def next_pellet(self) -> int:
        """Get the index of the next pellet batch in the simulation

        Returns:
            int: The index of the next pellet batch
        """
        self.pellet_index=self.pellet_index+1
        return self.pellet_index
    
    def next_rod(self) -> int:
        """Get the index of the next fuel rod in the simulation

        Returns:
            int: The index of the next fuel rod in the simulation
        """
        self.rod_index = self.rod_index+1
        return self.rod_index
    
    def next_assembly(self) -> int:
        """Get the index of the next fuel assembly in the simulation

        Returns:
            int: The index of the next fuel assembly in the simulation
        """
        self.assembly_index=self.assembly_index+1
        return self.assembly_index