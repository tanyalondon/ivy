# global
import struct
from typing import Optional, Tuple
import math
import paddle
from ivy.utils.exceptions import IvyNotImplementedException
from paddle.fluid.libpaddle import Place
from ivy.functional.backends.paddle.device import to_device

# local
import ivy
from ivy.func_wrapper import with_unsupported_dtypes
from . import backend_version

# noinspection PyProtectedMember
# Helpers for calculating Window Functions
# ----------------------------------------
# Code from cephes for i0


def _kaiser_window(window_length, beta):
    with ivy.ArrayMode(False):
        if window_length == 1:
            return ivy.ones(1)
        n = paddle.arange(0, window_length)
        alpha = (window_length - 1) / 2.0
        return ivy.i0(beta * paddle.sqrt(1 - ((n - alpha) / alpha) ** 2.0)) / ivy.i0(
            float(beta)
        )


# Array API Standard #
# -------------------#


def triu_indices(
    n_rows: int,
    n_cols: Optional[int] = None,
    k: Optional[int] = 0,
    /,
    *,
    device: Place,
) -> Tuple[paddle.Tensor]:
    return to_device(
        paddle.triu_indices(n_rows, col=n_cols, offset=k, dtype="int64"), device
    )


def kaiser_window(
    window_length: int,
    periodic: bool = True,
    beta: float = 12.0,
    *,
    dtype: Optional[paddle.dtype] = None,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    if periodic is False:
        return _kaiser_window(window_length, beta).cast(dtype)
    else:
        return _kaiser_window(window_length + 1, beta)[:-1].cast(dtype)


def hamming_window(
    window_length: int,
    /,
    *,
    periodic: Optional[bool] = True,
    alpha: Optional[float] = 0.54,
    beta: Optional[float] = 0.46,
    dtype: Optional[paddle.dtype] = None,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    # Implemented as a composite function in ivy.functional.experimental.creation
    raise IvyNotImplementedException()


def vorbis_window(
    window_length: paddle.Tensor,
    *,
    dtype: Optional[paddle.dtype] = paddle.float32,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    i = paddle.arange(1, window_length * 2, 2)
    pi = paddle.to_tensor(math.pi)
    return paddle.sin((pi / 2) * (paddle.sin(pi * i / (window_length * 2)) ** 2)).cast(
        dtype
    )


def hann_window(
    size: int,
    /,
    *,
    periodic: Optional[bool] = True,
    dtype: Optional[paddle.dtype] = None,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    size = size + 1 if periodic else size
    pi = paddle.to_tensor(math.pi)
    result_dtype = ivy.promote_types_of_inputs(size, 0.0)[0].dtype
    if size < 1:
        return paddle.to_tensor([], dtype=result_dtype)
    if size == 1:
        return paddle.ones(1, dtype=result_dtype)
    n = paddle.arange(1 - size, size, 2)
    res = (0.5 + 0.5 * paddle.cos(pi * n / (size - 1))).cast(dtype)
    return res[:-1] if periodic else res


def tril_indices(
    n_rows: int,
    n_cols: Optional[int] = None,
    k: Optional[int] = 0,
    /,
    *,
    device: Place,
) -> Tuple[paddle.Tensor, ...]:
    return tuple(
        to_device(
            paddle.tril_indices(n_rows, col=n_cols, offset=k, dtype="int64"), device
        )
    )


@with_unsupported_dtypes(
    {
        "2.4.2 and below": (
            "bfloat16",
            "complex64",
            "complex128",
            "uint16",
            "uint32",
            "uint64",
        )
    },
    backend_version,
)
def frombuffer(
    buffer: bytes,
    dtype: Optional[paddle.dtype] = float,
    count: Optional[int] = -1,
    offset: Optional[int] = 0,
) -> paddle.Tensor:
    dtype_bytes = int(ivy.Dtype(dtype).dtype_bits / 8)
    if str(dtype) == "bool":
        dtype_bytes = 1
    dtype_str = str(dtype)
    struct_format = {
        "bool": "?",
        "int8": "b",
        "int16": "h",
        "int32": "i",
        "int64": "q",
        "uint8": "B",
        "float16": "e",
        "float32": "f",
        "float64": "d",
    }
    ret = []
    for i in range(0, len(buffer), dtype_bytes):
        x = struct.unpack(struct_format[dtype_str], buffer[i : i + dtype_bytes])
        ret = ret + list(x)
    if offset > 0:
        offset = int(offset / dtype_bytes)
    if count > -1:
        ret = ret[offset : offset + count]
    else:
        ret = ret[offset:]
    ret = paddle.to_tensor(ret, dtype=dtype)

    return ret
