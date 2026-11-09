"""Information-boundary utilities for the synthetic institutional protocol.

Public API and evidence exports are untrusted audiences, not Coordinator views.
The internal report store remains role-scoped and must not be serialized directly.
"""


def public_report(report):
    """Expose an event's existence without its message, route or capacity."""
    return {
        'step': report['step'],
        'visibility': ('FORMALLY_SHARED' if 'Coordinator' in report.get('visible_to', ())
                       else 'RESTRICTED'),
        'details_withheld': True,
    }


def pending_private_supplier_reports(reports):
    """Return supplier-only route updates lacking a *later matching* disclosure.

    A prior or unrelated disclosure never acknowledges a new private event.
    Values are returned only to trusted in-process callers; public handoffs
    contain a boolean, not route identifiers or numerical quantities.
    """
    pending = {}
    for report in reports:
        viewers = report.get('visible_to', ())
        change = report.get('change') or {}
        route_id = change.get('route_id')
        if route_id and 'Supplier' in viewers and 'Coordinator' not in viewers:
            pending[route_id] = report
        if 'Coordinator' in viewers:
            for revealed in report.get('revealed_routes', ()):
                pending.pop(revealed, None)
            if route_id:  # coordinator directly received the same route update
                pending.pop(route_id, None)
    return list(pending.values())
