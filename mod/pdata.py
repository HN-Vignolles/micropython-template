# Based on https://gitlab.com/superfly/dawndoor by Raoul Snyman
#
# Licensed under the MIT license, see LICENSE.txt for details

import json


def _load_db():
    """
    Context manager to return an instance of a database
    """
    try:
        with open('config.json', 'r') as f:
            db = json.load(f)
    except OSError:
        db = {}
    return db


def _save_db(db):
    with open('config.json', 'w') as f:
        json.dump(db, f)


def has_config():
    """
    Determine if there is existing configuration
    """
    return bool(_load_db())


def get_network():
    """
    Get the WiFi config. If there is none, return None.
    """
    return _load_db().get('network')


def save_network(**kwargs):
    """
    Write the network config to file
    """
    db = _load_db()
    config = db.get('network')
    if not config:
        config = {}
    config.update(kwargs)
    db['network'] = config
    _save_db(db)
