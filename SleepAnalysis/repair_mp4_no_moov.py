"""
Rebuild a playable .mp4 from a session video whose recording was cut off
before the MP4 index (the `moov` box) was written -- ffmpeg/OpenCV then
refuse it with "moov atom not found", even though every frame is still in
the file's `mdat` box.

How: the frames are stored as length-prefixed H.264 NAL units, but the
decoder setup headers (SPS/PPS, which hold resolution/profile) only ever
lived in the missing moov. This script takes SPS/PPS from a *working* video
recorded by the same camera setup (check the x264 settings SEI string
matches -- it's printed below), rewrites the NAL stream as Annex-B with
SPS/PPS before every keyframe, and pipes it into ffmpeg, which muxes a
fresh .mp4 at a constant frame rate. No re-encoding, so no quality loss.

Optionally keeps only the first `max_frames` frames (rounded up to the next
keyframe so the file ends cleanly) -- e.g. when the camera kept recording
long after the ephys recording ended.

Written for MS14 (camera ran 12 days vs a 73h recording), 2026-09-24.
Usage:
    python repair_mp4_no_moov.py <broken.mp4> <reference_ok.mp4> <out.mp4> [max_frames] [fps]
"""
import subprocess
import sys

FFMPEG = "/media/anan/diskh1/miniconda3n/envs/peleg_env/bin/ffmpeg"
SC = b"\x00\x00\x00\x01"
CHUNK = 64 * 1024 * 1024


def x264_settings(path):
    with open(path, "rb") as f:
        b = f.read(4 * 1024 * 1024)
    i = b.find(b"x264 - core")
    return b[i:i + 2000].split(b"\x00")[0].decode(errors="replace") if i >= 0 else None


def reference_sps_pps(ref_path):
    out = subprocess.run(
        [FFMPEG, "-v", "error", "-i", ref_path, "-map", "0:v:0", "-c", "copy",
         "-bsf:v", "h264_mp4toannexb", "-frames:v", "1", "-f", "h264", "-"],
        check=True, capture_output=True).stdout
    nals = [n[:-1] if n.endswith(b"\x00") else n  # strip 4-byte-startcode zero
            for n in out.split(b"\x00\x00\x01")]
    nals = [n for n in nals if n]
    sps = next(n for n in nals if n[0] & 0x1F == 7)
    pps = next(n for n in nals if n[0] & 0x1F == 8)
    return sps, pps


def mdat_payload_offset(path):
    with open(path, "rb") as f:
        head = f.read(4096)
    i = head.find(b"mdat")
    if i < 4:
        raise ValueError("no mdat box near the start of the file")
    size = int.from_bytes(head[i - 4:i], "big")
    return i + 4 + (8 if size == 1 else 0)  # size==1 -> 64-bit largesize follows


def repair(broken, reference, out_path, max_frames=None, fps=25):
    a, b = x264_settings(broken), x264_settings(reference)
    print("x264 settings match reference:", a == b)
    if a != b:
        raise SystemExit("Encoder settings differ -- pick a reference from the same setup.")
    sps, pps = reference_sps_pps(reference)

    # -framerate (not -r) makes the raw-h264 demuxer assign timestamps;
    # -use_editlist 0 stops the mp4 muxer from hiding the first GOP's
    # B-frames behind an edit list -- without it, frames 1 and 3 silently
    # vanish and every later frame index shifts by 2 relative to the sync
    # pulses (checked frame-by-frame with ffmpeg -f framemd5 on MS14).
    ff = subprocess.Popen(
        [FFMPEG, "-v", "warning", "-y", "-framerate", str(fps),
         "-f", "h264", "-i", "-", "-c", "copy", "-use_editlist", "0", out_path],
        stdin=subprocess.PIPE)

    frames = 0
    stop_at_next_idr = False
    with open(broken, "rb") as f:
        f.seek(mdat_payload_offset(broken))
        buf, pos = b"", 0  # index into buf instead of re-slicing it per NAL
        eof = False
        while True:
            if len(buf) - pos < 4 + 20_000_000 and not eof:
                more = f.read(CHUNK)
                eof = not more
                buf, pos = buf[pos:] + more, 0
            if len(buf) - pos < 4:
                break
            n = int.from_bytes(buf[pos:pos + 4], "big")
            if n == 0 or n > 20_000_000:
                print(f"  stopping at implausible NAL length {n} (end of valid data)")
                break
            if len(buf) - pos < 4 + n:
                if eof:
                    break  # truncated last NAL (recording cut mid-write)
                continue
            nal = buf[pos + 4:pos + 4 + n]
            pos += 4 + n
            t = nal[0] & 0x1F
            if t == 5:  # IDR keyframe
                if stop_at_next_idr:
                    break
                ff.stdin.write(SC + sps + SC + pps)
            ff.stdin.write(SC + nal)
            if t in (1, 5):
                frames += 1
                if frames % 250_000 == 0:
                    print(f"  {frames} frames ({frames / fps / 3600:.2f} h)", flush=True)
                if max_frames and frames >= max_frames:
                    stop_at_next_idr = True
    ff.stdin.close()
    ff.wait()
    print(f"Wrote {frames} frames ({frames / fps / 3600:.2f} h) -> {out_path}, ffmpeg exit {ff.returncode}")
    return frames


if __name__ == "__main__":
    args = sys.argv[1:]
    repair(args[0], args[1], args[2],
           int(args[3]) if len(args) > 3 else None,
           int(args[4]) if len(args) > 4 else 25)
