from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Tuple

import numpy as np
import tifffile
from scipy.ndimage import zoom
from tqdm import tqdm


CHANNEL_FILE_PATTERN = re.compile(r"^ImageData_(Ch\d+)_TP\d+\.npy$")


def parse_records(path: Path) -> list[dict]:
    records: list[dict] = []
    current: dict = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("ClassName:"):
            current["ClassName"] = line.split(":", 1)[1].strip()
        elif line.startswith("EndClass:"):
            if current:
                records.append(current)
                current = {}
        elif ":" in line and not line.startswith("StartClass") and not line.startswith("-"):
            key, value = line.split(":", 1)
            value = value.strip()
            try:
                current[key.strip()] = float(value)
            except ValueError:
                current[key.strip()] = value
    return records


def get_first_record(records: list[dict], class_name: str) -> dict:
    for record in records:
        if record.get("ClassName") == class_name:
            return record
    raise ValueError(f"Could not find {class_name} in metadata")


def _format_wavelength_from_record(record: dict[str, Any]) -> str | None:
    for key in ("mName", "mCameraName"):
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text.isdigit():
            return text

    for key in ("mExcitationLambda", "mLambda"):
        value = record.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric <= 0:
            continue
        if numeric < 10:
            numeric *= 1000.0
        return str(int(round(numeric)))

    return None


def discover_channels(imgdir: Path) -> list[dict[str, str]]:
    channel_files: list[dict[str, str]] = []
    for path in sorted(imgdir.glob("ImageData_Ch*_TP*.npy")):
        match = CHANNEL_FILE_PATTERN.match(path.name)
        if match is None:
            continue
        channel_files.append({"label": match.group(1), "filename": path.name})

    if not channel_files:
        raise ValueError(f"No channel volumes matching ImageData_Ch*_TP*.npy found in {imgdir}")

    return channel_files


def load_channel_metadata(imgdir: Path) -> dict[str, dict[str, Any]]:
    channel_record_path = imgdir / "ChannelRecord.yaml"
    if not channel_record_path.exists():
        return {}

    records = parse_records(channel_record_path)
    channel_blocks: list[dict[str, dict[str, Any]]] = []
    current: dict[str, dict[str, Any]] | None = None

    for record in records:
        class_name = str(record.get("ClassName", ""))
        if class_name == "CChannelRecord70":
            current = {"channel_record": record}
            channel_blocks.append(current)
            continue
        if current is None:
            continue
        if class_name == "CExposureRecord70" and "exposure_record" not in current:
            current["exposure_record"] = record
        elif class_name == "CChannelDef70" and "channel_def" not in current:
            current["channel_def"] = record
        elif class_name == "CFluorDef70" and "fluor_def" not in current:
            current["fluor_def"] = record

    channel_metadata: dict[str, dict[str, Any]] = {}
    for index, block in enumerate(channel_blocks):
        label = f"Ch{index}"
        fluor_def = block.get("fluor_def", {})
        channel_def = block.get("channel_def", {})
        wavelength = _format_wavelength_from_record(fluor_def) or _format_wavelength_from_record(channel_def)
        channel_metadata[label] = {
            "wavelength": wavelength,
            "channel_name": channel_def.get("mName"),
            "fluor_name": fluor_def.get("mName"),
        }

    return channel_metadata


def load_voxel_size(imgdir: Path) -> Tuple[float, float]:
    image_records = parse_records(imgdir / "ImageRecord.yaml")
    channel_records = parse_records(imgdir / "ChannelRecord.yaml")

    lens = get_first_record(image_records, "CLensDef70")
    optovar = get_first_record(image_records, "COptovarDef70")
    exposure = get_first_record(channel_records, "CExposureRecord70")

    micron_per_pixel = float(lens["mMicronPerPixel"])
    optovar_mag = float(optovar["mMagnification"])
    x_factor = float(exposure.get("mXFactor", 1.0))
    y_factor = float(exposure.get("mYFactor", 1.0))
    voxel_z_um = float(abs(exposure["mInterplaneSpacing"]))

    voxel_x_um = micron_per_pixel / optovar_mag * x_factor
    voxel_y_um = micron_per_pixel / optovar_mag * y_factor
    if not np.isclose(voxel_x_um, voxel_y_um):
        raise ValueError(
            "This script supports only isotropic XY voxel size, but metadata gave "
            f"X={voxel_x_um:.6f} um and Y={voxel_y_um:.6f} um."
        )

    voxel_xy_um = voxel_x_um
    print(
        "Metadata voxel size: "
        f"XY={voxel_xy_um:.6f} um, Z={voxel_z_um:.6f} um "
        f"(mMicronPerPixel={micron_per_pixel:.6f}, "
        f"optovar={optovar_mag:.6f}, "
        f"XFactor={x_factor:.6f}, "
        f"YFactor={y_factor:.6f})"
    )
    return voxel_xy_um, voxel_z_um


def load_volume(imgdir: Path, filename: str) -> np.ndarray:
    volume = np.load(imgdir / filename, mmap_mode="r")
    if volume.ndim != 3:
        raise ValueError(f"Expected ZYX volume, got shape {volume.shape} for {filename}")
    return volume


def resample_xy_parallel(volume: np.ndarray, scale_xy: float, workers: int) -> np.ndarray:
    if np.isclose(scale_xy, 1.0):
        return np.asarray(volume)

    first = zoom(volume[0].astype(np.float32), (scale_xy, scale_xy), order=1)
    out = np.empty((volume.shape[0], first.shape[0], first.shape[1]), dtype=volume.dtype)
    out[0] = np.clip(first, 0, np.iinfo(volume.dtype).max).astype(volume.dtype)

    def process_slice(z: int) -> Tuple[int, np.ndarray]:
        resized = zoom(volume[z].astype(np.float32), (scale_xy, scale_xy), order=1)
        resized = np.clip(resized, 0, np.iinfo(volume.dtype).max).astype(volume.dtype)
        return z, resized

    with ThreadPoolExecutor(max_workers=workers) as executor:
        iterator = executor.map(process_slice, range(1, volume.shape[0]))
        for z, resized in tqdm(
            iterator,
            total=volume.shape[0] - 1,
            desc="Resampling XY",
            unit="slice",
        ):
            out[z] = resized

    return out


def resample_volume(volume: np.ndarray, scale_z: float, scale_xy: float, workers: int) -> np.ndarray:
    if np.isclose(scale_z, 1.0) and np.isclose(scale_xy, 1.0):
        return np.asarray(volume)
    if np.isclose(scale_z, 1.0):
        return resample_xy_parallel(volume, scale_xy=scale_xy, workers=workers)

    resized = zoom(volume.astype(np.float32), (scale_z, scale_xy, scale_xy), order=1)
    return np.clip(resized, 0, np.iinfo(volume.dtype).max).astype(volume.dtype)


def maybe_flip(volume: np.ndarray, flip_x: bool, flip_y: bool) -> np.ndarray:
    out = volume
    if flip_y:
        out = out[:, ::-1, :]
    if flip_x:
        out = out[:, :, ::-1]
    return out


def save_tiff(volume: np.ndarray, path: Path, voxel_z_um: float, voxel_xy_um: float) -> None:
    resolution_xy = (10000.0 / voxel_xy_um, 10000.0 / voxel_xy_um)
    tifffile.imwrite(
        path,
        volume,
        imagej=True,
        resolution=resolution_xy,
        resolutionunit="CENTIMETER",
        metadata={"axes": "ZYX", "unit": "um", "spacing": voxel_z_um},
    )


def save_info(
    path: Path,
    imgdir: Path,
    channels: list[dict[str, Any]],
    source_xy_um: float,
    source_z_um: float,
    target_xy_um: float,
    target_z_um: float,
    scale_xy: float,
    scale_z: float,
    flip_x: bool,
    flip_y: bool,
) -> None:
    info = {
        "input_imgdir": str(imgdir),
        "channels": channels,
        "source_voxel_um": {
            "xy": float(source_xy_um),
            "z": float(source_z_um),
        },
        "target_voxel_um": {
            "xy": float(target_xy_um),
            "z": float(target_z_um),
        },
        "scale_factors": {
            "xy": float(scale_xy),
            "z": float(scale_z),
        },
        "flip": {
            "x": bool(flip_x),
            "y": bool(flip_y),
        },
    }
    path.write_text(json.dumps(info, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Light Sheet microscope volumes to TIFF.")
    parser.add_argument("--imgdir", type=Path, required=True, help="Input *.imgdir directory.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for TIFF outputs.")
    parser.add_argument("--prefix", type=str, default=None, help="Optional prefix for the conversion info JSON only.")
    parser.add_argument("--source-xy-um", type=float, default=None, help="Override source XY voxel size in um.")
    parser.add_argument("--source-z-um", type=float, default=None, help="Override source Z voxel size in um.")
    parser.add_argument("--target-xy-um", type=float, default=None, help="Target XY voxel size in um. Omit to skip resampling.")
    parser.add_argument("--target-z-um", type=float, default=None, help="Target Z voxel size in um. Omit to skip resampling.")
    parser.add_argument("--workers", type=int, default=16, help="Workers for XY-only resampling.")
    parser.add_argument("--flip-x", dest="flip_x", action="store_true", help="Flip X before saving.")
    parser.add_argument("--no-flip-x", dest="flip_x", action="store_false", help="Do not flip X.")
    parser.add_argument("--flip-y", dest="flip_y", action="store_true", help="Flip Y before saving.")
    parser.add_argument("--no-flip-y", dest="flip_y", action="store_false", help="Do not flip Y.")
    parser.set_defaults(flip_x=False, flip_y=False)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source_xy_um, source_z_um = load_voxel_size(args.imgdir)
    if args.source_xy_um is not None:
        source_xy_um = float(args.source_xy_um)
    if args.source_z_um is not None:
        source_z_um = float(args.source_z_um)

    target_xy_um = float(args.target_xy_um) if args.target_xy_um is not None else source_xy_um
    target_z_um = float(args.target_z_um) if args.target_z_um is not None else source_z_um

    scale_xy = source_xy_um / target_xy_um
    scale_z = source_z_um / target_z_um

    print(f"Source voxel size: XY={source_xy_um:.6f} um, Z={source_z_um:.6f} um")
    print(f"Target voxel size: XY={target_xy_um:.6f} um, Z={target_z_um:.6f} um")
    print(f"Scale factors: scale_xy={scale_xy:.6f}, scale_z={scale_z:.6f}")
    print(f"Flip: flip_x={args.flip_x}, flip_y={args.flip_y}")

    channel_files = discover_channels(args.imgdir)
    channel_metadata = load_channel_metadata(args.imgdir)
    saved_channels: list[dict[str, Any]] = []

    for channel in channel_files:
        channel_label = channel["label"]
        input_name = channel["filename"]
        metadata = channel_metadata.get(channel_label, {})
        wavelength = str(metadata.get("wavelength") or "unknown")
        print(f"Loading {channel_label}: {input_name}")
        volume = load_volume(args.imgdir, input_name)
        print(f"Input shape ZYX: {tuple(int(v) for v in volume.shape)}")

        volume = resample_volume(volume, scale_z=scale_z, scale_xy=scale_xy, workers=args.workers)
        volume = maybe_flip(volume, flip_x=args.flip_x, flip_y=args.flip_y)

        output_name = f"{channel_label}_{wavelength}.tif"
        output_path = args.output_dir / output_name
        print(f"Saving TIFF -> {output_path}")
        save_tiff(volume, output_path, voxel_z_um=target_z_um, voxel_xy_um=target_xy_um)
        print(f"Saved shape ZYX: {tuple(int(v) for v in volume.shape)}")
        saved_channels.append(
            {
                "label": channel_label,
                "input_file": input_name,
                "wavelength": wavelength,
                "channel_name": metadata.get("channel_name"),
                "fluor_name": metadata.get("fluor_name"),
                "output_file": output_name,
            }
        )

    info_stem = f"{args.prefix}_conversion_info.json" if args.prefix else "conversion_info.json"
    info_path = args.output_dir / info_stem
    save_info(
        info_path,
        imgdir=args.imgdir,
        channels=saved_channels,
        source_xy_um=source_xy_um,
        source_z_um=source_z_um,
        target_xy_um=target_xy_um,
        target_z_um=target_z_um,
        scale_xy=scale_xy,
        scale_z=scale_z,
        flip_x=args.flip_x,
        flip_y=args.flip_y,
    )
    print(f"Saved info -> {info_path}")


if __name__ == "__main__":
    main()
