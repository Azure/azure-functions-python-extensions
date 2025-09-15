#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import argparse
from typing import List, Optional


class ArgumentError(Exception):
    """Custom exception for missing or invalid arguments."""
    pass


def parse_grpc_args(argv: Optional[List[str]] = None):
    """
    Parses CLI arguments for gRPC connection.

    Args:
        argv: Optional list of CLI arguments (defaults to sys.argv[1:]).

    Returns:
        args: Namespace with host, port, and functions_grpc_max_message_length

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

    missing_args = []
    if not args.host:
        missing_args.append("'host'")
    if not args.port:
        missing_args.append("'port'")
    if not args.functions_grpc_max_message_length:
        missing_args.append("'functions-grpc-max-message-length'")

    if missing_args:
        raise ArgumentError(f"Missing required arguments: {', '.join(missing_args)}")
    return args


def get_grpc_uri(args) -> str:
    """
    Returns the gRPC URI from CLI args.
    """
    return f"{args.host}:{args.port}"


def get_grpc_max_message_length(args) -> int:
    """
    Returns the gRPC max message length from CLI args.
    """
    return args.functions_grpc_max_message_length
