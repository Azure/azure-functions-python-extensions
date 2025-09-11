#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import argparse
from typing import Tuple, List


class ArgumentError(Exception):
    """Custom exception for missing or invalid arguments."""
    pass


def build_grpc_uri(argv: List[str] | None = None) -> Tuple[str, int]:
    """
    Builds a gRPC URI and retrieves the max message length from CLI args.

    Expected CLI arguments:
      --host HOST
      --port PORT
      --functions-grpc-max-message-length LENGTH

    Args:
        argv: Optional list of CLI arguments (defaults to sys.argv[1:]).

    Returns:
        (uri, grpc_max_message_length)

    Raises:
        ArgumentError if required arguments are missing or invalid.
    """
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("--host", help="gRPC server host")
    parser.add_argument("--port", help="gRPC server port")
    parser.add_argument(
        "--functions-grpc-max-message-length",
        type=int,
        help="Maximum gRPC message size in bytes",
    )

    args, _ = parser.parse_known_args(argv)

    missing = []
    if not args.host:
        missing.append("'host'")
    if not args.port:
        missing.append("'port'")
    if not args.functions_grpc_max_message_length:
        missing.append("'functions-grpc-max-message-length'")

    if missing:
        raise ArgumentError(f"Missing required arguments: {', '.join(missing)}")

    uri = f"{args.host}:{args.port}"
    return uri, args.functions_grpc_max_message_length
