from .const import LZ4_COMPRESSION, LZO_COMPRESSION, NO_COMPRESSION, XZ_COMPRESSION, ZLIB_COMPRESSION, ZSTD_COMPRESSION


class Compressor:
    name = "none"

    def uncompress(self, src, size, outsize):
        return src


class ZlibCompressor(Compressor):
    name = "gzip"

    def __init__(self):
        import zlib
        self._lib = zlib

    def uncompress(self, src, size, outsize):
        return self._lib.decompress(src)


class LZOCompressor(Compressor):
    name = "lzo"

    def __init__(self):
        import lzo
        self._lib = lzo

    def uncompress(self, src, size, outsize):
        return self._lib.decompress(src, False, outsize)


class XZCompressor(Compressor):
    name = "xz"

    def __init__(self):
        try:
            import lzma
        except ImportError:
            from backports import lzma
        self._lib = lzma

    def uncompress(self, src, size, outsize):
        return self._lib.decompress(src)


class LZ4Compressor(Compressor):
    name = "lz4"

    def __init__(self):
        import lz4.frame
        self._lib = lz4.frame

    def uncompress(self, src, size, outsize):
        return self._lib.decompress(src)


class ZSTDCompressor:
    name = "zstd"

    def __init__(self):
        from ctypes import CDLL, c_void_p, c_size_t, create_string_buffer
        from ctypes.util import find_library

        self.create_string_buffer = create_string_buffer

        libzstd = CDLL(find_library("zstd"))
        self.zstddecomp = libzstd.ZSTD_decompress
        self.zstddecomp.restype = c_size_t
        self.zstddecomp.argtypes = (c_void_p, c_size_t, c_void_p, c_size_t)
        self.iserror = libzstd.ZSTD_isError

    def uncompress(self, src, size, outsize):

        dest = self.create_string_buffer(outsize)  # length of src seems to never be above 262144 (256K)

        sz = self.zstddecomp(dest, len(dest), src, len(src))
        if self.iserror(sz):
            raise IOError("Decompression failed!")
        return dest[:sz]  # outsize is always a multiple of 8K, but real size may be smaller


compressors = {
    NO_COMPRESSION: Compressor,
    ZLIB_COMPRESSION: ZlibCompressor,
    LZO_COMPRESSION: LZOCompressor,
    XZ_COMPRESSION: XZCompressor,
    LZ4_COMPRESSION: LZ4Compressor,
    ZSTD_COMPRESSION: ZSTDCompressor
}
