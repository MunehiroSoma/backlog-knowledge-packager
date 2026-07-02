"""argparse entry point for the ``collect`` command (design §8).

TODO(#12): argument parsing (--space/--domain/--project/--targets/--output),
config merge, connection check, module wiring, exit codes 0/1/2/3.
"""

import sys


def main() -> int:
    print(
        "backlog-packager: not implemented yet (skeleton). "
        "See the v0.1 (MVP) milestone: "
        "https://github.com/MunehiroSoma/backlog-knowledge-packager/milestone/1",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
