#!/usr/bin/env python3
"""Read-only hot-seed placement policy. Never copies, removes or starts Mover.

Adapters must supply verified physical location, canonical user-share paths,
complete torrent ownership, fresh maintenance guards and upload observations.
"""
import math
from selection_policy import REQUIRED_GUARDS, within
from torrent_preflight import absolute_path


def number(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value < 0:
        raise ValueError('Unknown numeric state')
    return value


def demand(previous, current, now, minimum_bytes):
    for sample in (previous,current):
        if not isinstance(sample,dict):raise ValueError('Missing demand sample')
        for key in ('at','uploaded','generation'):number(sample.get(key))
    elapsed=current['at']-previous['at']
    if not 300 <= elapsed <= 3600 or not 0 <= now-current['at'] <= 60:
        raise ValueError('Stale or insufficient demand observations')
    if current['generation']!=previous['generation'] or current['uploaded']<previous['uploaded']:
        raise ValueError('Counter reset or changed ownership')
    return current['uploaded']-previous['uploaded'] >= minimum_bytes


def plan(files, guards, *, now, observed_at, free_bytes, reserve_bytes=300*1024**3,
         batch_bytes=32*1024**3, max_files=2, cooldown=86400,
         minimum_uploaded=64*1024**2, root='/mnt/user/Filmek'):
    """Suggest array -> cache candidates, with reserve and anti-ping-pong guards.

    Ratio is deliberately irrelevant: cumulative ratio does not show current
    demand. Two monotonic upload observations identify recently wanted content.
    Hot content may be copied only after it becomes quiet and closed; this policy
    never interrupts a seed or grants execution permission.
    """
    result={'version':1,'read_only':True,'execution_allowed':False,
            'direction':'array_to_cache','candidates':[],'skipped':[],
            'planned_bytes':0,'blockers':[]}
    try:
        for value in (now,observed_at,free_bytes,reserve_bytes,batch_bytes,cooldown,minimum_uploaded):number(value)
        if (type(free_bytes) is not int or type(reserve_bytes) is not int or
            type(batch_bytes) is not int or type(max_files) is not int or
            not 1 <= max_files <= 8 or batch_bytes==0 or cooldown<86400 or
            minimum_uploaded==0 or not 0 <= now-observed_at <= 30):
            raise ValueError('Unverifiable policy settings')
        root=absolute_path(root)
        if root=='/' or not isinstance(files,list) or not isinstance(guards,dict):
            raise ValueError('Unverifiable inventory')
        result['blockers']=[key for key in REQUIRED_GUARDS if guards.get(key)!='pass']
        if result['blockers']:
            result['decision']='blocked';return result
        budget=max(0,min(batch_bytes,free_bytes-reserve_bytes))
        seen=set();eligible=[]
        for item in files:
            key=absolute_path(item['path'])
            if key in seen or key==root or not within(key,root):raise ValueError('Ambiguous inventory')
            seen.add(key)
            size=item.get('bytes')
            if type(size) is not int or size<=0:raise ValueError('Unknown file size')
            reason=None
            if item.get('location')!='array' or type(item.get('copies')) is not int or item.get('copies')!=1:
                reason='not_unique_array_copy'
            elif not all(item.get(k) is True for k in ('regular','stable','all_owners_complete','user_share_binding')) or type(item.get('nlink')) is not int or item.get('nlink')!=1 or item.get('symlink') is not False:
                reason='unsafe_or_unknown_content'
            elif item.get('open') is not False or item.get('quiet') is not True:
                reason='busy_or_unknown'
            else:
                try:
                    moved=number(item.get('last_move_at'))
                    if moved==0 or not 0 <= now-moved or now-moved<cooldown:reason='movement_cooldown'
                    elif not demand(item.get('previous'),item.get('current'),now,minimum_uploaded):reason='low_recent_demand'
                except (ValueError,TypeError,KeyError):reason='unknown_demand_or_history'
            if reason:result['skipped'].append({'path':key,'reason':reason})
            else:eligible.append(dict(item,path=key))
        # Highest observed demand first; stable tie-break makes plans reproducible.
        eligible.sort(key=lambda x:(-(x['current']['uploaded']-x['previous']['uploaded']),x['path']))
        for item in eligible:
            key=item['path'];size=item['bytes']
            if len(result['candidates'])>=max_files:reason='batch_file_limit'
            elif size>budget-result['planned_bytes']:reason='cache_reserve_or_batch_limit'
            else:
                result['candidates'].append(key);result['planned_bytes']+=size;continue
            result['skipped'].append({'path':key,'reason':reason})
        result.update(decision='preview_only',remaining_free_bytes=free_bytes-result['planned_bytes'])
    except (ValueError,TypeError,KeyError,AttributeError):
        result.update(decision='unknown',candidates=[],skipped=[],planned_bytes=0,blockers=['unverifiable_snapshot'])
    return result
