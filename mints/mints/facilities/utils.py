from simpy.core import Environment
from mints.facilities import SimulationFacility

#Compute the enrichment of a material given the isotope and weights 
def get_enrichment(isotope1, isotope1_weight, isotope2, isotope2_weight):
    atom_iso1 = isotope1_weight/isotope1
    atom_iso2 = isotope2_weight/isotope2
    enrichment = atom_iso1/(atom_iso1+atom_iso2)
    return enrichment


def get_UO2_concentration(material):
    u_concentration=(material.isotopes['U235']+material.isotopes['U238'])/(material.isotopes['O']+material.isotopes['U235']+material.isotopes['U238'])
    return u_concentration

def get_pu_concentration(material):
    return material.isotopes['Pu'] / sum(material.isotopes.values())

def monitor_facility_inventory(env: Environment, facility: SimulationFacility):
    facility_stores = facility.dict_of_stores().values()
    while True:
        yield env.timeout(1)
        for store in facility_stores:
            store._save_inventory_record()