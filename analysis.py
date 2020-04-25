
import numpy as np

import utils

def house_fft_filter(size: int, low: int, high: int):
    """
        Function that returns the "gold standard" filter that was
        used for the legacy scans. This function returns a window
        function that resembles a sigmoid between `low` and `high`,
        and indices outside of these regions are set to zero or
        one respectively.
        
        This window is designed to produce low sidelobes
        for Fourier filters.
    """
    filt = np.zeros(size)
    
    def eval_filter(rf, c1, c2, c3, c4):
        r1 = 1. - rf**2.
        r2 = r1**2.
        r3 = r2 * r1
        filt = c1 + c2*r1 + c3*r2 + c4*r3
        return filt

    coefficients = {
        "c1": 0.074,
        "c2": 0.302,
        "c3": 0.233,
        "c4": 0.390
    }
    
    denom = (high - low + 1.0) / 2.
    if denom < 0.:
        raise ZeroDivisionError
    
    for i in range(int(low), int(high)):
        rf = (i + 1) / denom
        if rf > 1.5:
            filt[i] = 1.
        else:
            temp = eval_filter(rf, **coefficients)
            if temp < 0.:
                filt[i] = 1.
            else:
                filt[i] = 1. - temp
    filt[int(high):] = 1.
    return filt


def filter_signal(signal: np.ndarray, low=0, high=10000):
    """
    Function to run a signal through the FFT filter. First,
    the spectrum (frequency domain) goes through an FFT, and
    the processing is then done on the time-domain data. The
    `low` and `high` values implement a cut-off in the time
    domain corresponding to the array indices. Outside of these
    indices, the time-domain amplitude is set to zero.

    Parameters
    ----------
    signal : np.ndarray
        1D array containing the frequency spectrum
    low : int, optional
        Index cutoff in the time-domain, by default 0
    high : int, optional
        Index cutoff in the time-domain, by default 10000

    Returns
    -------
    np.ndarray
        The filtered signal, comprising only the real part of the
        FFT.
    """
    window_function = house_fft_filter(len(signal), low, high)
    print(len(window_function))
    time_domain = np.fft.fft(signal)
    # Remove contributions from outside the window
    time_domain[:low] = 0.
    time_domain[high:] = 0.
    time_domain *= window_function
    # Return the frequency domain spectrum
    return np.real(np.fft.ifft(time_domain))
    