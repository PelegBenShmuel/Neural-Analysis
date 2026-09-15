"""
Generate a buzcode/Neuroscope-style .xml from a SpikeGLX Neuropixels LF-band
.meta file, so SleepScoreMaster can run directly against the raw .lf.bin
(symlinked as basename.lfp -- no resampling/conversion needed).

Schema confirmed by cross-checking the existing scored sessions (MS08, MS09,
MS11) against their own .meta files:
    nChannels       = nSavedChans          (probe channels + 1 sync)
    samplingRate    = lfpSamplingRate = round(imSampRate)
    amplification   = imChan0lfGain         (real per-session LF gain)
    voltageRange    = round((imAiRangeMax - imAiRangeMin) * 1000)   [mV]
    nBits           = 16 (fixed)
    offset          = 0  (fixed)
    anatomicalDescription: single channel group listing channels
        0 .. nSavedChans-2 (excludes the last channel, which is the sync line)

Usage:
    python generate_buzcode_xml.py <path/to/*.imec0.lf.meta> <path/to/basename.xml>
"""
import sys
from pathlib import Path

XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<parameters version="1.0">
  <acquisitionSystem>
    <nBits>16</nBits>
    <nChannels>{n_channels}</nChannels>
    <samplingRate>{sampling_rate}</samplingRate>
    <voltageRange>{voltage_range}</voltageRange>
    <amplification>{amplification}</amplification>
    <offset>0</offset>
  </acquisitionSystem>
  <fieldPotentials>
    <lfpSamplingRate>{lfp_sampling_rate}</lfpSamplingRate>
  </fieldPotentials>
  <anatomicalDescription>
    <channelGroups>
      <group>
        {channels}
      </group>
    </channelGroups>
  </anatomicalDescription>
  <spikeDetection>
    <channelGroups>
    </channelGroups>
  </spikeDetection>
</parameters>
"""


def parse_meta(meta_path):
    meta = {}
    for line in Path(meta_path).read_text().splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        meta[key.lstrip("~")] = value
    return meta


def build_xml(meta_path):
    meta = parse_meta(meta_path)

    n_saved_chans = int(meta["nSavedChans"])
    samp_rate = round(float(meta["imSampRate"]))
    gain = meta["imChan0lfGain"]
    ai_max = float(meta["imAiRangeMax"])
    ai_min = float(meta["imAiRangeMin"])
    voltage_range = round((ai_max - ai_min) * 1000)

    # Sync channel is always last; the channel group covers the probe
    # channels only (0 .. n_saved_chans-2), matching MS08/09/11's convention.
    n_probe_chans = n_saved_chans - 1
    channel_lines = []
    for row_start in range(0, n_probe_chans, 4):
        row = "".join(
            f"<channel>{ch}</channel>"
            for ch in range(row_start, min(row_start + 4, n_probe_chans))
        )
        channel_lines.append(row)
    channels_block = "\n        ".join(channel_lines)

    return XML_TEMPLATE.format(
        n_channels=n_saved_chans,
        sampling_rate=samp_rate,
        lfp_sampling_rate=samp_rate,
        voltage_range=voltage_range,
        amplification=gain,
        channels=channels_block,
    )


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    meta_path, out_xml_path = sys.argv[1], sys.argv[2]
    xml_text = build_xml(meta_path)
    Path(out_xml_path).write_text(xml_text)
    print(f"Wrote {out_xml_path}")


if __name__ == "__main__":
    main()
