"""Pure start/stop policy for completed-seed cache draining; no I/O."""


def limits(settings):
    enabled = settings.get('completed_seed_mode', False)
    if type(enabled) is not bool:
        raise ValueError('Invalid completed seed mode')
    if not enabled:
        return None
    start = settings.get('cache_start_percent', 75)
    stop = settings.get('cache_stop_percent', 65)
    if type(start) is not int or type(stop) is not int or not 1 <= stop < start <= 99:
        raise ValueError('Cache percentages must satisfy 1 <= stop < start <= 99')
    return start, stop


def evaluate(settings, previous, total, free, scope):
    bounds = limits(settings)
    if bounds is None:
        return None
    if type(total) is not int or type(free) is not int or total <= 0 or not 0 <= free <= total:
        raise ValueError('Cache capacity unavailable')
    if not isinstance(previous, dict):
        raise ValueError('Invalid cache cycle state')
    if previous and (type(previous.get('version')) is not int or previous.get('version') != 1 or type(previous.get('active')) is not bool
                     or not isinstance(previous.get('scope'), dict)):
        raise ValueError('Unknown cache cycle state')
    start, stop = bounds
    same = (previous.get('scope') == scope and previous.get('start_percent') == start
            and previous.get('stop_percent') == stop)
    active = same and previous.get('active') is True
    used = 100 * (total - free) / total
    active = used >= start or (active and used > stop)
    return {'version': 1, 'scope': scope, 'start_percent': start,
            'stop_percent': stop, 'active': active, 'used_percent': used,
            'stop_reached': used <= stop}
