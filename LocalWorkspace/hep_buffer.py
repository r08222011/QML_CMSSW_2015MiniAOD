''' To save data buffer after extracting with hep_events.py
- Buffer will be saved from awkward.Array to torch.Tensor
'''

import os, typing
import torch
import awkward as ak
from tqdm import tqdm
from hep_events import get_events

def load_data_buffer(channel:str, get_method:typing.Callable, *args) -> torch.Tensor:
    ''' Load data with hep_events.get_events()
    - channel: channel(process) name
    - get_method: extracting specific features with the given method
    - args: arguments for the get_method function
    '''

    # file name for the buffer
    suffix = " ".join(map(str, args))
    buffer_file = f"data_buffer/{channel}-{get_method.__name__}-{suffix}.pt"

    # check whether the buffer is already created, otherwise create a new buffer
    if not os.path.exists(buffer_file):
        print(f"DataLog(hep_buffer.py:load_data_buffer): {channel} buffer not found, create now ...")
        events = get_method(channel, *args)
        torch.save(events, buffer_file)
    else:
        events = torch.load(buffer_file)
        print(f"DataLog(hep_buffer.py:load_data_buffer): {channel} buffer found, loading complete!")
    return events

def get_parent_info(channel:str, num_events:int, jet_type:str, cut:str=None):
    ''' Get the parent information for a given channel
    - pt eta phi of the jet/fatjet
    - n-subjettiness of the fatjet
    '''

    # feature to be extracted
    expressions = [f"{jet_type}_{feature}" for feature in ["pt", "eta", "phi"]]
    if jet_type == "fatjet":
        expressions += ["fatjet_tau1", "fatjet_tau2", "fatjet_tau3", "fatjet_tau2/fatjet_tau1", "fatjet_tau3/fatjet_tau2"]
    events = get_events(channel, num_events, jet_type, cut, expressions)

    # pt eta phi of the jet/fatjet
    trimmed_events = torch.cat((
        torch.tensor(events[f"{jet_type}_pt"])[:, None], 
        torch.tensor(events[f"{jet_type}_eta"])[:, None],
        torch.tensor(events[f"{jet_type}_phi"])[:, None]), dim=1)
    
    # if fatjet, n-subjettiness will also be included
    if jet_type == "fatjet":
        trimmed_events = torch.cat((
            trimmed_events,
            torch.tensor(events["fatjet_tau1"])[:, None],
            torch.tensor(events["fatjet_tau2"])[:, None],
            torch.tensor(events["fatjet_tau3"])[:, None],
            torch.tensor(events["fatjet_tau2/fatjet_tau1"])[:, None],
            torch.tensor(events["fatjet_tau3/fatjet_tau2"])[:, None]), dim=1)
    return trimmed_events

def get_daughter_info(channel:str, num_events:int, num_particles:int, jet_type:str, cut=None):
    ''' Get additional the daughter information for a given channel (without parent info)
    - num_particles: how many daughter to be selected (highest pt) in each events
    - pt eta phi of the daughter of a jet/fatjet
    '''

    # feature to be extracted (only daughter)
    expressions = [f"{jet_type}_daughter_{feature}" for feature in ["pt", "eta", "phi"]]
    events = get_events(channel, num_events, jet_type, cut, expressions)

    # only choose daughters with highest pt
    trimmed_events = torch.zeros((len(events), num_particles*3))
    idx_argsort = ak.argsort(events[f"{jet_type}_daughter_pt"], axis=-1, ascending=False)
    for i in tqdm(range(len(events)), desc=f"get_daughter_info : Channel {channel} with {num_events} events"):
        # some events would not have as much particles as num_particles
        l = min(len(idx_argsort[i]), num_particles)
        pt, eta, phi = torch.zeros(num_particles), torch.zeros(num_particles), torch.zeros(num_particles)
        pt[:l]  = torch.tensor(events[f"{jet_type}_daughter_pt"][i][idx_argsort[i][:l]])
        eta[:l] = torch.tensor(events[f"{jet_type}_daughter_eta"][i][idx_argsort[i][:l]])
        phi[:l] = torch.tensor(events[f"{jet_type}_daughter_phi"][i][idx_argsort[i][:l]])
        trimmed_events[i] = torch.cat((pt, eta, phi), dim=0)
    return trimmed_events