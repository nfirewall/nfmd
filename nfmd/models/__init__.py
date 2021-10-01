import os
from importlib import import_module

submodules = []

for module in os.listdir(os.path.dirname(__file__)):
    if module == '__init__.py' or module[-3:] != '.py':
        continue
    modulename = module[:-3]
    mod = import_module("{}.{}".format(__name__, modulename))
    globals()[modulename] = getattr(mod, modulename)
    submodules.append(modulename)
del module, mod

__all__ = submodules