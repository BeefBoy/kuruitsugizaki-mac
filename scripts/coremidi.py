"""CoreMIDI through ctypes, for the live link on macOS: a virtual MIDI source and destination that FL sees as an input
and an output port. ctypes rather than python-rtmidi, which has no wheel for every Python and needs a compiler.

Messages are SysEx frames (`frames`, `Frames`), the same framing the controller script uses: JSON is ASCII, so it is
valid SysEx data as is, cut into chunks."""
import ctypes
import platform
import threading
import zlib
from ctypes import POINTER, byref, c_char_p, c_int32, c_uint32, c_uint64, c_void_p

HEAD = bytes((0xF0, 0x7D, 0x6B, 0x7A))  # 7D: the MIDI manufacturer ID for non-commercial use, then 'kz'
TO_FL, FROM_FL = 1, 2
CHUNK = 240

_cm = _cf = None
ReadProc = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, c_void_p)


def frames(mid: int, data: bytes, way: int) -> list[bytes]:
    n = max(1, -(-len(data) // CHUNK))
    return [HEAD + bytes((way, mid >> 7 & 127, mid & 127, i >> 7, i & 127, n >> 7, n & 127)) + data[i * CHUNK:(i + 1) * CHUNK] + b"\xf7"
            for i in range(n)]


class Frames:
    """Collects frames going one way into whole messages: add() returns (id, data) when the last chunk arrives."""

    def __init__(self, way: int):
        self.way, self.mid, self.parts = way, None, {}

    def add(self, s: bytes):
        if len(s) < 12 or s[:4] != HEAD or s[4] != self.way:
            return None
        mid, i, n = s[5] << 7 | s[6], s[7] << 7 | s[8], s[9] << 7 | s[10]
        if mid != self.mid or i == 0:
            self.mid, self.parts = mid, {}
        self.parts[i] = s[11:-1]
        if len(self.parts) < n:
            return None
        data = b"".join(self.parts.get(k, b"") for k in range(n))
        self.mid, self.parts = None, {}
        return mid, data


class SysEx:
    """Whole SysEx messages out of a byte stream; CoreMIDI may split one across packets."""

    def __init__(self):
        self.buf = None

    def feed(self, data: bytes) -> list[bytes]:
        out = []
        for b in data:
            if b == 0xF0:
                self.buf = bytearray(b"\xf0")
            elif self.buf is None or b >= 0xF8:  # outside SysEx, or a realtime byte inside one
                continue
            elif b == 0xF7:
                out.append(bytes(self.buf + b"\xf7"))
                self.buf = None
            elif b >= 0x80:
                self.buf = None
            else:
                self.buf.append(b)
        return out


def _libs():
    global _cm, _cf
    if _cm is None:
        cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        cm = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI")
        cf.CFStringCreateWithCString.restype = c_void_p
        cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]
        cf.CFRelease.argtypes = [c_void_p]
        cm.MIDIClientCreate.argtypes = [c_void_p, c_void_p, c_void_p, POINTER(c_uint32)]
        cm.MIDISourceCreate.argtypes = [c_uint32, c_void_p, POINTER(c_uint32)]
        cm.MIDIDestinationCreate.argtypes = [c_uint32, c_void_p, ReadProc, c_void_p, POINTER(c_uint32)]
        cm.MIDIObjectSetIntegerProperty.argtypes = [c_uint32, c_void_p, c_int32]
        cm.MIDIPacketListInit.argtypes = [c_void_p]
        cm.MIDIPacketListInit.restype = c_void_p
        cm.MIDIPacketListAdd.argtypes = [c_void_p, c_uint64, c_void_p, c_uint64, c_uint64, c_char_p]
        cm.MIDIPacketListAdd.restype = c_void_p
        cm.MIDIReceived.argtypes = [c_uint32, c_void_p]
        cm.MIDIEndpointDispose.argtypes = [c_uint32]
        cm.MIDIClientDispose.argtypes = [c_uint32]
        _cm, _cf = cm, cf
    return _cm, _cf


def _check(status: int, what: str):
    if status:
        raise OSError(f"CoreMIDI {what} failed: OSStatus {status}")


def _packets(ptr: int):
    """The data of each MIDIPacket in a MIDIPacketList (4-byte aligned packets on arm64)."""
    n = c_uint32.from_address(ptr).value
    p = ptr + 4
    for _ in range(n):
        length = ctypes.c_uint16.from_address(p + 8).value
        yield ctypes.string_at(p + 10, length)
        p += 10 + length
        if platform.machine() == "arm64":
            p = (p + 3) & ~3


class VirtualPort:
    """A virtual source (we send, FL's MIDI input reads) and destination (FL's MIDI output writes, on_sysex gets each
    whole SysEx message, on a CoreMIDI thread). Both exist while this object does. Fixed unique IDs let FL keep its
    settings for them across restarts of the server."""

    def __init__(self, name: str, on_sysex):
        cm, cf = _libs()
        self.on_sysex, self.sysex, self.lock = on_sysex, SysEx(), threading.Lock()
        cname = cf.CFStringCreateWithCString(None, name.encode(), 0x08000100)
        prop = c_void_p.in_dll(cm, "kMIDIPropertyUniqueID")
        client, src, dst = c_uint32(), c_uint32(), c_uint32()
        try:
            _check(cm.MIDIClientCreate(cname, None, None, byref(client)), "MIDIClientCreate")
            self.client = client.value
            _check(cm.MIDISourceCreate(self.client, cname, byref(src)), "MIDISourceCreate")
            self._proc = ReadProc(self._read)  # kept: CoreMIDI calls it for as long as the destination exists
            _check(cm.MIDIDestinationCreate(self.client, cname, self._proc, None, byref(dst)), "MIDIDestinationCreate")
        finally:
            cf.CFRelease(cname)
        self.src, self.dst = src.value, dst.value
        base = zlib.crc32(name.encode()) & 0x3FFFFFFF
        cm.MIDIObjectSetIntegerProperty(self.src, prop, base)
        cm.MIDIObjectSetIntegerProperty(self.dst, prop, base + 1)

    def _read(self, pktlist, _ref, _src):
        for data in _packets(pktlist):
            for msg in self.sysex.feed(data):
                self.on_sysex(msg)

    def send(self, msg: bytes):
        cm, _ = _libs()
        size = len(msg) + 64
        with self.lock:
            buf = ctypes.create_string_buffer(size)
            pkt = cm.MIDIPacketListInit(buf)
            if not cm.MIDIPacketListAdd(buf, size, pkt, 0, len(msg), msg):
                raise OSError("MIDIPacketListAdd: message does not fit")
            _check(cm.MIDIReceived(self.src, buf), "MIDIReceived")

    def close(self):
        cm, _ = _libs()
        for e in (self.src, self.dst):
            cm.MIDIEndpointDispose(e)
        cm.MIDIClientDispose(self.client)
