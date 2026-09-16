"""GTK4 platform adapter for Deskling's Linux runtime."""

from .application import GtkPetApplication
from .backend import GtkBackend

__all__ = ["GtkBackend", "GtkPetApplication"]
