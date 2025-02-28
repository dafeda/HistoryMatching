"""Common tools."""

import numpy as np
import scipy.linalg as sla
from tqdm.auto import tqdm as progbar


def norm(xx):
    # return numpy.linalg.norm(xx/sqrt(len(xx)), ord=2)
    return np.sqrt(np.mean(xx * xx))


def RMSMs(series, ref):
    """Print RMS err. and dev., from the Mean (along axis 0), for each item in `series`.

    The `ref` must point to a data series that is *not* an ensemble.
    All series (including `ref`) can have both singleton and `squeeze`d axis 0.
    """
    x = series[ref]

    # Ensure reference's axis 0 is singleton.
    if x.shape[0] != 1:
        x = x[None, :]

    # Print table heading
    header = "Series    rms err  rms dev"
    print(header, "-"*len(header), sep="\n")

    for k, y in series.items():

        # Ensure non-ensemble series also has singleton axis 0
        if y.ndim < x.ndim:
            y = y[None, :]
            assert y.shape == x.shape

        err = x - y.mean(0)
        dev = y - y.mean(0)
        print(f"{k:8}: {norm(err):6.4f}   {norm(dev):6.4f}")


def svd0(A):
    """Similar to Matlab's svd(A,0).

    Compute the

     - full    svd if nrows > ncols
     - reduced svd otherwise.

    As in Matlab: svd(A,0),
    except that the input and output are transposed, in keeping with DAPPER convention.
    It contrasts with scipy.linalg's svd(full_matrice=False) and Matlab's svd(A,'econ'),
    both of which always compute the reduced svd.

    .. seealso:: tsvd() for rank (and threshold) truncation.
    """
    M, N = A.shape
    if M > N:
        return sla.svd(A, full_matrices=True)
    return sla.svd(A, full_matrices=False)


def pad0(ss, N):
    """Pad ss with zeros so that len(ss)==N."""
    out = np.zeros(N)
    out[:len(ss)] = ss
    return out


def pows(U, sig):
    """Prepare the computation of the matrix power of a symmetric matrix.

    The input matrix is specified by its eigen-vectors (U) and -values (sig).
    """
    def compute(expo):
        return (U * sig**expo) @ U.T
    return compute


def center(E, axis=0, rescale=False):
    """Center ensemble, `E`.

    Makes use of np features: keepdims and broadcasting.

    If it is known that the true/theoretical mean of (the members of) `E`
    is actually zero, it might be beneficial make it so for `E`, but at the same
    time compensate for the reduction in the (expected) variance this implies.
    This is done if `rescale` is `True`.
    """
    x = np.mean(E, axis=axis, keepdims=True)
    X = E - x

    if rescale:
        N = E.shape[axis]
        X *= np.sqrt(N/(N-1))

    x = x.squeeze()

    return X, x


def mean0(E, axis=0, rescale=True):
    """Like `center`, but only return the anomalies (not the mean).

    Uses `rescale=True` by default, which is beneficial
    when used to center observation perturbations.
    """
    return center(E, axis=axis, rescale=rescale)[0]


def inflate_ens(E, factor):
    """Inflate the ensemble (center, inflate, re-combine)."""
    if factor == 1:
        return E
    X, x = center(E)
    return x + X*factor


def cov(a, b):
    """Compute covariance between a sample of two multivariate variables.

    Unlike `np.cov`, `a` and `b` need not have the same shape,
    but must must of course have equal ensemble size, i.e. `shape[0]`.
    """
    A, _ = center(a)
    B, _ = center(b)
    return A.T @ B / (len(B) - 1)


def corr(a, b):
    """Compute correlation using `cov`."""
    C = cov(a, b)

    sa = np.std(a.T, axis=-1, ddof=1)
    sb = np.std(b  , axis=+0, ddof=1, keepdims=True)
    # with np.errstate(divide="ignore", invalid="ignore"):
    Corr = C / sa / sb

    # Convert inf to 999. Either way it means that the correlation is ill-defined,
    # but contourf colors inf as nan's (given by set_bad(color), not set_over())
    Corr = Corr.clip(-999, 999)

    return Corr


def get_map(multiprocessing=False):
    """Unify multiprocessing/single-processing interface via `map`."""
    nCores = None if multiprocessing in ["auto", True] else multiprocessing

    def mp(fun, args, desc="", total=None, leave=True):
        if nCores == None or nCores > 1:
            # Make sure np uses only 1 core. Our problem is embarrasingly parallelzable,
            # so we are more efficient manually instigating multiprocessing.
            import threadpoolctl
            threadpoolctl.threadpool_limits(1)

            from p_tqdm import p_map
            return p_map(fun, list(args), desc=desc, num_cpus=nCores, leave=leave)
        else:
            return progbar(map(fun, args), desc=desc, total=total, leave=leave)

    return mp
