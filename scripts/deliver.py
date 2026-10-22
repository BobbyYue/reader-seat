#!/usr/bin/env python3
"""Run the existing final verifier and return its exact candidate, not a rewritten copy."""
import contextlib
import argparse
import io
import json
import sys
import tempfile
from pathlib import Path

import checked_delivery as delivery
import runtime_contract as runtime
import writing_execution
from lifecycle_guard import verify_lifecycle


def checked_document(arguments):
    arguments = list(arguments)
    if not arguments or arguments[0] not in {"verify", "present-draft", "lifecycle-draft"}:
        raise delivery.DeliveryBlocked("Only verified delivery and incomplete-draft operations are allowed")
    if any(arg == "--receipt" or arg.startswith("--receipt=") for arg in arguments):
        raise delivery.DeliveryBlocked("The wrapper owns the fresh verification receipt")
    with tempfile.TemporaryDirectory(prefix="reader-seat-delivery-") as temporary:
        receipt = Path(temporary) / "verification.json"
        args = runtime.build_parser().parse_args([*arguments, "--receipt", str(receipt)])
        lifecycle = verify_lifecycle(args.lifecycle_run, args.artifact,
                                     args.reader_review_aggregate,
                                     draft=args.command != "verify", contract_path=args.contract)
        paths = [value for key, value in vars(args).items()
                 if isinstance(value, Path) and key not in {"receipt", "lifecycle_run"}]
        paths.extend(map(Path, lifecycle["evidence_paths"]))
        scripts = Path(__file__).resolve().parent
        paths.extend(scripts.glob("*.py"))
        paths.extend((scripts.parent / "config").glob("*.json"))

        def verify():
            # Existing commands may print PASS for draft presentation. Read the
            # fresh typed receipt instead of trusting stdout or exit code alone.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    args.func(args)
                except SystemExit as exc:
                    raise delivery.DeliveryBlocked("Runtime verification failed") from exc
            result = json.loads(receipt.read_text(encoding="utf-8"))
            result["review_method"] = "independent" if result.get("reader_validation") else "not-attested"
            result["managed_execution"] = writing_execution.accept_native(
                args.lifecycle_run, args.artifact, [args.reader_review_aggregate], result)
            return result

        return delivery.pack(args.artifact, paths, verify)


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--output", type=Path)
    options, args = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    try:
        envelope = checked_document(args)
        delivery.emit(envelope, options.output)
        if options.output:
            print(json.dumps({"delivery_state": envelope["delivery_state"], "envelope": str(options.output.resolve()),
                              "artifact_sha256": envelope["artifact"]["sha256"]}))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        return delivery.blocked()


if __name__ == "__main__":
    raise SystemExit(main())
