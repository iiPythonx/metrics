# Copyright (c) 2025 iiPython

from .storm import StormPlugin

# This variable is what defines the plugin loading order.
# If you have two plugins both modifying the current notice, the one that is higher up will be used.
PLUGINS = [
    StormPlugin(),
]
