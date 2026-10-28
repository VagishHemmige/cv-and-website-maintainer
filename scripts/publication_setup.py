"""Private publication-setup observations; no network calls or library/export writes."""
import argparse
import importlib.util
import json
from pathlib import Path

spec=importlib.util.spec_from_file_location('publication_bootstrap',Path(__file__).with_name('initialize.py'))
init=importlib.util.module_from_spec(spec);spec.loader.exec_module(init)

def assess(value):
    allowed={'reference','desktop','integration','inventory','destination_verified','export_side_effects_reviewed','account','sync_requested','export'}
    if not isinstance(value,dict) or set(value)-allowed:
        raise ValueError('Unexpected publication observations; never store credentials')
    if not isinstance(value.get('reference'),str) or not value['reference'].strip():
        raise ValueError('Actual observation reference required')
    desktop=value.get('desktop','unknown')
    if desktop not in ('missing','stopped','running','unknown'):raise ValueError('Invalid Desktop observation')
    account=value.get('account','unknown')
    if account not in ('none','present','unknown'):raise ValueError('Invalid account observation')
    def boolean(v):
        if v is not None and type(v) is not bool:raise ValueError('Readiness observations must be true, false or null')
        return v is True
    integration=value.get('integration',{})
    if not isinstance(integration,dict) or set(integration)-{'available','read','import','export'}:raise ValueError('Invalid integration capabilities')
    capabilities={key:boolean(integration.get(key)) for key in ('available','read','import','export')}
    inventory=value.get('inventory',{})
    if not isinstance(inventory,dict) or set(inventory)-{'complete','item_count'}:raise ValueError('Invalid inventory observation')
    complete=boolean(inventory.get('complete'));count=inventory.get('item_count')
    if count is not None and (type(count) is not int or count<0):raise ValueError('Invalid item count')
    connection=desktop=='running' and capabilities['available'] and capabilities['read']
    library=('empty' if count==0 else 'existing') if connection and complete and count is not None else 'unknown'
    destination=boolean(value.get('destination_verified'))
    side_effects=boolean(value.get('export_side_effects_reviewed'))
    proposal=connection and library!='unknown' and capabilities['import'] and destination and side_effects
    export=value.get('export',{})
    keys={'scope_verified','citation_keys_verified','consumer_path_verified','format_verified','outputs_verified'}
    if not isinstance(export,dict) or set(export)-keys:raise ValueError('Invalid export observations')
    export_checks={key:boolean(export.get(key)) for key in keys}
    export_ready=connection and library!='unknown' and all(export_checks.values())
    sync=boolean(value.get('sync_requested'))
    actions=[]
    if desktop!='running':actions.append('Offer authorized Desktop installation/launch or continue private candidate reconciliation')
    if not connection:actions.append('Resolve current integration/read access; no account is required for the local route')
    if library=='unknown':actions.append('Complete relevant library inventory before duplicate absence claims')
    else:actions.append('Reconcile CV/PubMed candidates with '+library+' library through existing reviewed workflows')
    if not proposal:actions.append('Keep imports pending until capabilities, destination and export effects are verified')
    if not export_ready:actions.append('Verify intended export subset, citation keys, consumer path/format and actual requested outputs')
    if sync:actions.append('Resolve optional account/sync setup separately; local setup remains independent')
    return dict(desktop=desktop,connection='ready' if connection else 'pending',library=library,
                import_proposal='ready_for_review' if proposal else 'pending',
                publication_outputs='verified_observations' if export_ready else 'pending',
                account=account,sync='requested_separate_setup' if sync else 'not_requested',
                next_actions=actions,reference=value['reference'],
                basis='operator_observations_not_live_verification',writes_authorized=False)

def stage(state,value):
    report=assess(value)
    with init.lock(state):
        init.load(state)
        def write(folder):
            init.exclusive(folder/'observations.json',init.encode(value))
            init.exclusive(folder/'readiness.json',init.encode(report))
            return dict(folder=str(folder),readiness_path=str(folder/'readiness.json'),writes_authorized=False)
        return init.transaction(state,'publication-setup',write)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('assess');p.add_argument('observations',type=Path)
    p=sub.add_parser('stage');p.add_argument('state',type=Path);p.add_argument('observations',type=Path)
    a=parser.parse_args()
    value=init.decode(a.observations.read_bytes())
    result=stage(a.state,value) if a.command=='stage' else assess(value)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
