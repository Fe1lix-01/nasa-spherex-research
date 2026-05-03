import os
import subprocess
import sys

import astropy.units as u
from astropy.coordinates import SkyCoord


def open_file(filename):
    """
    Open a file using the default system application based on the platform.

    Parameters
    ----------
    filename : str
        The path to the file to be opened.

    Notes
    -----
    - On Windows, this uses `os.startfile`.
    - On macOS, it uses the `open` command.
    - On Linux, it uses `evince` (assumes it's installed).
    """

    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "evince"
        subprocess.call([opener, filename])


def create_object_name(ra, dec, precision=0, sep="", prefix=None, shortform=False, decimal=True):
    """
    Generate a string-based object name from celestial coordinates.

    Parameters
    ----------
    ra : float
        Right Ascension in degrees.
    dec : float
        Declination in degrees.
    precision : int, optional
        Number of decimal places for coordinates (default is 0).
    sep : str, optional
        Separator to use in formatted output (default is "").
    prefix : str, optional
        String to prepend to the object name.
    shortform : bool, optional
        If True, returns a short HMS/DMS form like '1234+5678'.
    decimal : bool, optional
        If True, returns decimal-formatted coordinates.

    Returns
    -------
    str
        A formatted object name string.
    """

    coords = SkyCoord(ra=ra * u.degree, dec=dec * u.degree)

    if shortform:
        coords_str = coords.to_string("hmsdms", decimal=False, sep=sep, precision=0)
        object_name = coords_str[0:4] + coords_str[7:12]
    else:
        if decimal:
            object_name = coords.to_string(decimal=True, precision=precision)
        else:
            object_name = coords.to_string("hmsdms", decimal=False, sep=sep, precision=precision).replace(" ", "")

    if prefix:
        object_name = prefix + object_name

    return str(object_name)
