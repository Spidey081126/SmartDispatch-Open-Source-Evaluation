from copy import deepcopy
import math


def is_valid_time(val):
    """
    A valid time is a finite, non-negative real number.
    - bool is rejected (True == 1 in Python, which would be a silent bug).
    - Very large ints are handled safely (math.isnan(10**400) would raise OverflowError).
    """
    if isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    try:
        as_float = float(val)
    except OverflowError:
        return False
    return math.isfinite(as_float) and as_float >= 0


def is_valid_id(val):
    """A valid id is a non-empty, non-whitespace string."""
    return isinstance(val, str) and len(val.strip()) > 0


def _ineligible(partner_id):
    return {'partner_id': partner_id, 'eta_minutes': None, 'eligible': False}


def estimate_eta(order, partner, travel, now=0):
    """
    Pickup = now + leg1 + workload
    ETA    = pickup + prep_minutes + leg2
    A missing or invalid route is NEVER treated as zero: the partner is ineligible.
    """
    partner_id = partner.get('partner_id') if isinstance(partner, dict) else None
    if not (isinstance(order, dict) and isinstance(partner, dict) and isinstance(travel, dict)):
        return _ineligible(partner_id)

    if not is_valid_time(now):
        return _ineligible(partner_id)

    prep = order.get('prep_minutes', 0)
    workload = partner.get('workload_minutes', 0)
    if not is_valid_time(prep) or not is_valid_time(workload):
        return _ineligible(partner_id)

    partner_zone = partner.get('zone')
    restaurant_id = order.get('restaurant_id')
    destination_zone = order.get('destination_zone')
    if not (is_valid_id(partner_zone) and is_valid_id(restaurant_id) and is_valid_id(destination_zone)):
        return _ineligible(partner_id)

    try:
        leg1 = travel.get((partner_zone, restaurant_id))
        leg2 = travel.get((restaurant_id, destination_zone))
    except TypeError:  # unhashable key part
        return _ineligible(partner_id)

    if not is_valid_time(leg1) or not is_valid_time(leg2):
        return _ineligible(partner_id)

    pickup = now + leg1 + workload
    eta = pickup + prep + leg2

    # Guard against overflow to inf / absurdly large sums.
    if not (is_valid_time(pickup) and is_valid_time(eta)):
        return _ineligible(partner_id)

    return {
        'partner_id': partner_id,
        'pickup_minutes': pickup,
        'eta_minutes': eta,
        'eligible': True,
    }


def assign_order(order, partners, travel, now=0):
    """
    Filters partners (active, capacity, valid ids), computes ETA, and picks the lowest ETA.
    Ties are broken deterministically by partner_id ascending.
    """
    if not isinstance(order, dict):
        return {'order_id': None, 'partner_id': None, 'eta_minutes': None, 'reason': 'invalid order'}

    order_id = order.get('order_id')
    restaurant_id = order.get('restaurant_id')
    destination_zone = order.get('destination_zone')
    prep = order.get('prep_minutes', 0)

    if not (is_valid_id(order_id) and is_valid_id(restaurant_id) and is_valid_id(destination_zone)):
        return {'order_id': order_id, 'partner_id': None, 'eta_minutes': None, 'reason': 'invalid order fields'}

    if not is_valid_time(prep):
        return {'order_id': order_id, 'partner_id': None, 'eta_minutes': None, 'reason': 'invalid prep time'}

    if not isinstance(travel, dict) or not is_valid_time(now):
        return {'order_id': order_id, 'partner_id': None, 'eta_minutes': None, 'reason': 'invalid travel or time'}

    if not isinstance(partners, (list, tuple)):
        return {'order_id': order_id, 'partner_id': None, 'eta_minutes': None,
                'reason': 'no eligible partner or missing time data'}

    options = []
    for partner in partners:
        if not isinstance(partner, dict):
            continue

        # 1. Must be active
        if partner.get('active') is not True:
            continue

        # 2. Capacity must be an int >= 1 (bool excluded)
        cap = partner.get('capacity')
        if not (isinstance(cap, int) and not isinstance(cap, bool) and cap >= 1):
            continue

        # 3. Must have room for one more order.
        #    Only list/tuple/set are accepted; a string would be split into characters.
        active_orders = partner.get('active_order_ids', [])
        if not isinstance(active_orders, (list, tuple, set, frozenset)):
            continue
        if len(active_orders) >= cap:
            continue

        # 4. Valid identifiers
        if not (is_valid_id(partner.get('partner_id')) and is_valid_id(partner.get('zone'))):
            continue

        estimate = estimate_eta(order, partner, travel, now)
        if estimate.get('eligible'):
            options.append(estimate)

    if not options:
        return {'order_id': order_id, 'partner_id': None, 'eta_minutes': None,
                'reason': 'no eligible partner or missing time data'}

    chosen = min(options, key=lambda item: (item['eta_minutes'], item['partner_id']))
    return {
        'order_id': order_id,
        'partner_id': chosen['partner_id'],
        'pickup_minutes': chosen['pickup_minutes'],
        'eta_minutes': chosen['eta_minutes'],
        'reason': 'assigned',
    }


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set, frozenset)):
        return list(value)
    return []


def process_cancellation(partner, order_id, event_id):
    """
    Idempotent cancellation:
    - Duplicate event_id -> state unchanged.
    - Active order -> removed (all copies), workload reduced once, clamped at 0.
    - event_id recorded so a replay never releases workload twice.
    """
    if not isinstance(partner, dict):
        return partner

    out = deepcopy(partner)  # never mutate the caller's object
    out['active_order_ids'] = _as_list(out.get('active_order_ids', []))
    out['processed_cancellation_ids'] = _as_list(out.get('processed_cancellation_ids', []))

    # Without an event id we cannot guarantee idempotency, so ignore the event.
    if event_id is None:
        return out

    # Idempotency guard
    if event_id in out['processed_cancellation_ids']:
        return out

    if order_id in out['active_order_ids']:
        while order_id in out['active_order_ids']:
            out['active_order_ids'].remove(order_id)

        minutes_by_order = out.get('minutes_by_order')
        minutes = 0
        if isinstance(minutes_by_order, dict):
            minutes = minutes_by_order.pop(order_id, 0)  # also clears the stale entry
        if not is_valid_time(minutes):
            minutes = 0

        workload = out.get('workload_minutes', 0)
        if not is_valid_time(workload):
            workload = 0
        out['workload_minutes'] = max(0, workload - minutes)

    out['processed_cancellation_ids'].append(event_id)
    return out