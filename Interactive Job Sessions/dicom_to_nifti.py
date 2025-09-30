import SimpleITK as sitk
import json, os, argparse

def load_all_series(dicom_dir):
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(dicom_dir)
    if not series_ids:
        raise RuntimeError(f"No DICOM series in {dicom_dir}")
    out = []
    for sid in series_ids:
        files = reader.GetGDCMSeriesFileNames(dicom_dir, sid)
        reader.SetFileNames(files)
        img = reader.Execute()
        out.append((sid, img, files))
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dicom-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--series-index", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    series = load_all_series(args.dicom_dir)
    sid, img, files = series[args.series_index]

    nii_path  = os.path.join(args.out_dir, f"volume_{args.series_index}_{sid}.nii.gz")
    json_path = os.path.join(args.out_dir, f"volume_{args.series_index}_{sid}.json")

    sitk.WriteImage(img, nii_path, useCompression=True)
    meta = {
      "series_uid": sid,
      "size": list(img.GetSize()),
      "spacing": list(img.GetSpacing()),
      "origin": list(img.GetOrigin()),
      "direction": list(img.GetDirection()),
      "n_slices": len(files),
      "first_file": os.path.basename(files[0]),
    }
    with open(json_path, "w") as f:
        json.dump(meta, f, indent=2)

    print("WROTE", nii_path)
    print("META ", json_path)

