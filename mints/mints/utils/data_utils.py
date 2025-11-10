"""
This file contains utility functions for creating plots of inventory counts at various portions of the fuel cycle.
"""
import numpy as np
import matplotlib.pyplot as plt
from mints.facilities.enrichment import *

def inv_counter(mba):
    try:
        final_week=np.max(mba['week'])
    except KeyError:
        print('Inventory was empty')
        return np.array([0]),np.array([0])
    
    inv_count=np.zeros((final_week,1))

    for ii in range(final_week):
        inv_count[ii]=len(mba.loc[(mba['week']==ii)])

    return inv_count

def inv_bulk(mba):
    inv_bulk=mba['quantity']

    return inv_bulk

def in_out_count(mba):
    final_week=np.max(mba['week'])
    in_count=np.zeros((final_week,1))
    out_count=np.zeros((final_week,1))

    for ii in range(final_week):
        in_count[ii]=len(mba['ins'][ii])
        out_count[ii]=len(mba['outs'][ii])

    return in_count,out_count

def mine_ship_plot(mine_store):
    inv_count = inv_counter(mine_store['receiving_mba'])
    plt.plot(inv_count,label='Receiving Inventory')

def PHWR_reactor_plot(react_store):
    inv_count = inv_counter(react_store['receiving_mba'])
    plt.plot(inv_count,label='Receiving Inventory')

    core_inv = inv_counter(react_store['core_mba'])
    plt.plot(core_inv,label='Core Inventory')


    spent_inv = inv_counter(react_store['spent_fuel_mba'])
    plt.plot(spent_inv,label='Spent Fuel Inventory')

    plt.xlabel('week')
    plt.ylabel('Inventory count(assemblies)')
    plt.title('PHWR Reactor Inventories')
    plt.legend()
    plt.show()

def LWR_reactor_plot(react_store):
    inv_count = inv_counter(react_store['receiving_mba'])
    plt.plot(inv_count,label='Receiving Inventory')

    core1_inv = inv_counter(react_store['core_mba1'])
    plt.plot(core1_inv,label='Core_1 Inventory')

    core2_inv = inv_counter(react_store['core_mba2'])
    plt.plot(core2_inv,label='Core_2 Inventory')

    core3_inv = inv_counter(react_store['core_mba3'])
    plt.plot(core3_inv,label='Core Inventory')

    spent_inv = inv_counter(react_store['spent_fuel_mba'])
    plt.plot(spent_inv,label='Spent Fuel Inventory')

    plt.xlabel('week')
    plt.ylabel('Inventory count(assemblies)')
    plt.title('PHWR Reactor Inventories')
    plt.legend()
    plt.show()

def conversion_plot(conv_store):
    inv_count = inv_counter(conv_store['receiving_mba'])
    plt.plot(inv_count,label='Receiving Inventory')

    u235_inv = inv_bulk(conv_store['u235_store'])
    plt.plot(u235_inv,label='u235 Inventory')

    ship_inv = inv_counter(conv_store['shipping_mba'])
    plt.plot(ship_inv,label='Shipping Inventory')

    plt.xlabel('week')
    plt.ylabel('Inventory count(drums)')
    plt.title('Conversion Inventories')
    plt.legend()
    plt.show()

def conversion_gen_plot(conv_store, show_loss=False):
    inv_count = inv_counter(conv_store['receiving_mba'])
    plt.plot(inv_count,label='Receiving Inventory')

    u235_inv = inv_bulk(conv_store['U235_in_process'])
    plt.plot(u235_inv/(400*0.0061),label='u235 in process')

    u235_inv = inv_bulk(conv_store['U235_to_product'])

    ship_inv = inv_counter(conv_store['shipping_mba'])
    plt.plot(ship_inv,label='Shipping Inventory')

    if(show_loss):
        U235_loss,_ = inv_bulk(conv_store['U235_lost_material'])
        plt.plot(U235_loss/(400*0.0061),label='u235 lost')

    plt.xlabel('week')
    plt.ylabel('Inventory count(drums)')
    plt.title('Conversion Inventories')
    plt.legend()
    plt.show()

def enrichment_plot(enr_store,  show_loss=False):
    inv_count = inv_counter(enr_store['receiving_mba'])
    plt.plot(inv_count,label='Receiving Inventory')

    u235_inv = inv_bulk(enr_store['cascade_feed_bulk'])
    plt.plot(u235_inv/(400*0.0061),label='cascade feed')

    u235_inv = inv_bulk(enr_store['cascade_product_bulk'])
    plt.plot(u235_inv/(400*0.87544),label='cascade product')

    ship_inv = inv_counter(enr_store['shipping_mba'])
    plt.plot(ship_inv,label='Shipping Inventory')

    if(show_loss):
        U235_loss,_ = inv_bulk(enr_store['U235_lost_material'])
        plt.plot(U235_loss/(400*0.0061),label='u235 lost')

    plt.xlabel('week')
    plt.ylabel('Inventory count(drums)')
    plt.title('Enrichment Inventories')
    plt.legend()
    plt.show()

def fuel_fab_plot(ff_store ,show_loss=False):
    inv_count = inv_counter(ff_store['receiving_mba'])
    plt.plot(inv_count*400,label='Receiving Inventory')

    pel_pow = inv_bulk(ff_store['pelleting_UO2_powder_store'])
    plt.plot(pel_pow,label='UO\u2082 powder Inventory')

    pel_inv = inv_counter(ff_store['pelleting_mba'])
    plt.plot(pel_inv*12,label='Pellet Inventory')

    ship_inv = inv_counter(ff_store['shipping_mba'])
    plt.plot(ship_inv*22.2,label='Shipping Inventory')

    if(show_loss):
            pel_pow_lost = inv_bulk(ff_store['pelleting_UO\u2082_powder_lost'])
            plt.plot(pel_pow_lost,label='UO2 powder lost')
    plt.xlabel('week')
    plt.ylabel('Inventory (kg UO\u2082)')
    plt.title('Fuel Fab Inventories')
    plt.legend()
    plt.show()
    
def conversion_in_out_plot(conv_store):
    rec_in,rec_out = in_out_count(conv_store['receiving_mba_ins_and_outs'])
    plt.plot(rec_in,label='Conv_rec In count')
    plt.plot(rec_out,linestyle='--',label='Conv_rec Out Count')

    ship_in,ship_out = in_out_count(conv_store['shipping_mba_ins_and_outs'])
    plt.plot(ship_in,label='Conv_ship In count')
    plt.plot(ship_out,linestyle='--',label='Conv_ship Out Count')

    inv_count = inv_counter(conv_store['receiving_mba'])
    plt.plot(inv_count,label='Receiving Inventory')


    plt.xlabel('week')
    plt.ylabel('In')
    plt.title('Conversion In/out')
    plt.legend()
    plt.show()


def load_all_inventory(file_path):
    """
    Load all inventory data from the HDF5 file into a nested dictionary.

    Parameters:
    - file_path: str, path to the HDF5 file

    Returns:
    - Dictionary where the first key is the facility name and the second key is the store name,
    containing the DataFrame for each store.
    """
    inventory_data = {}
    
    with pd.HDFStore(file_path, mode='r') as store:
        for key in store.keys():
            # Split the key to extract facility and store names
            path_parts = key.strip('/').split('/')
            facility_name = path_parts[0]
            store_name = path_parts[1]
            
            # Initialize nested dictionary if not already initialized
            if facility_name not in inventory_data:
                inventory_data[facility_name] = {}
                
            # Load the DataFrame
            inventory_data[facility_name][store_name] = store.get(key)
    
    return inventory_data
