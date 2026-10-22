"""Inspect a review JSON's shape and anchors; never produce an acceptance receipt."""
import argparse
import json
from pathlib import Path
import reader_review

def inspect(packet_path, result_path):
    packet = json.loads(Path(packet_path).read_text())
    result = json.loads(Path(result_path).read_text())
    manifest = {key: packet[key] for key in ("contract_id", "batch_id", "round")}
    errors = reader_review.validate_result(result, manifest, packet)
    return {"errors": list(dict.fromkeys(errors)),
            "scope": "Local format/anchor diagnostics only. Preserve negative judgments. This is not captured review or final acceptance."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.packet, args.result), ensure_ascii=False))
