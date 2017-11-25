import numpy

import cupy
from cupy import cuda
from cupy.cuda import device
from cupy.linalg import util
from cupy import sparse


if cuda.cusolver_enabled:
    from cupy.cuda import cusolver


def lsqr(A, b):
    """Solves linear system with QR decomposition.

    Find the solution to a large, sparse, linear system of equations.
    The function solves ``Ax = b``. Given two-dimensional matrix ``A`` is
    decomposed into ``Q * R``.

    Args:
        A (cupy.ndarray or cupy.sparse.csr_matrix): The input matrix with
            dimension ``(N, N)``
        b (cupy.ndarray): Right-hand side vector.

    Returns:
        ret (tuple): Tuple of the same type as scipy. The solution vector
            ``x`` is the first element of the tuple. There are some unknown
            elements, which are expressed as None, due to the differences
            in the implementation of cusolver and scipy.

    .. seealso:: :func:`scipy.sparse.linalg.lsqr`
    """

    if not cuda.cusolver_enabled:
        raise RuntimeError('Current cupy only supports cusolver in CUDA 8.0')

    if not sparse.isspmatrix_csr(A):
        A = sparse.csr_matrix(A)
    util._assert_nd_squareness(A)
    util._assert_cupy_array(b)
    m = A.shape[0]
    if b.ndim != 1 or len(b) != m:
        raise ValueError('b must be 1-d array whose size is same as A')

    # Cast to float32 or float64
    if A.dtype.char == 'f' or A.dtype.char == 'd':
        dtype = A.dtype.char
    else:
        dtype = numpy.find_common_type((A.dtype.char, 'f'), ()).char

    handle = device.get_cusolver_sp_handle()
    nnz = A.nnz
    tol = 1.0
    reorder = 1
    x = cupy.empty(m, dtype=dtype)
    singularity = numpy.empty(1, numpy.int64)

    if dtype == 'f':
        csrlsvqr = cusolver.scsrlsvqr
    else:
        csrlsvqr = cusolver.dcsrlsvqr
    csrlsvqr(
        handle, m, nnz, A._descr.descriptor, A.data.data.ptr,
        A.indptr.data.ptr, A.indices.data.ptr, b.data.ptr, tol, reorder,
        x.data.ptr, singularity.ctypes.data)
    x = x.astype(numpy.float64)

    r1norm = cupy.linalg.norm(b - A.dot(x))
    xnorm = cupy.linalg.norm(x)
    ret = (x, None, None, r1norm, None, None, None, None, xnorm, None)
    return ret
