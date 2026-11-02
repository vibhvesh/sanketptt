"""Plug-in style inputs. Every input type is a class registered with @register in its own module.
Adding a new input type = drop a module here that subclasses InputBase and import it below."""
from .registry import InputBase, register, types, create, InputManager   # noqa
from . import local_audio, fake, relay, rtlsdr                         # noqa  (registers types)
