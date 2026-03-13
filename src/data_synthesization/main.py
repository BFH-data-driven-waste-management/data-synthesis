import argparse

from data_synthesization.pipelines.generate_bin_activity import run_generate_bin_activity


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Data synthesization CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    arg_parser = sub.add_parser("generate-bin-activity", help="Generate synthetic bin_activity data")
    arg_parser.add_argument("--config", required=True, help="Path to YAML config")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate-bin-activity":
        run_generate_bin_activity(args.config)


if __name__ == "__main__":
    main()
