# AlgoC compiler
# To make an executable python algoc.py source
# To make a C traduction python algoc.py source --no-gcc
# REQUIREMENTS: Lark 1.1.0 or higher

import argparse
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from ast_generator import ASTGenerator
from code_generator import CCodeGenerator
from symbol_table import AlgoCError

GRAMMAR_PATH = Path(__file__).resolve().with_name("grammar.lark")

def compile_algoc(source_path: str, no_gcc: bool = False) -> Tuple[Path, Optional[Path]]:
    source = Path(source_path)

    if not source.is_file():
        raise AlgoCError(f"Source file {source} not found. Please, specify a valid file.")

    if not GRAMMAR_PATH.is_file():
        raise AlgoCError(f"Grammar file not found, please put the grammar file in {GRAMMAR_PATH} as grammar.lark.")

    c_path = source.with_suffix(".c")
    executable_path = source.with_suffix("")

    ast = ASTGenerator(str(GRAMMAR_PATH)).generate_from_file(str(source))
    c_code = CCodeGenerator().generate(ast)
    c_path.write_text(c_code, encoding="utf-8")

    if no_gcc:
        return c_path, None

    command = ["gcc", "-std=c99", str(c_path), "-o", str(executable_path)]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise AlgoCError(
            "gcc not found. Install gcc or use --no-gcc to generate only the C file."
        ) from exc
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() or exc.stdout.strip()
        raise AlgoCError("Error during C compilation:\n" + details) from exc

    if not executable_path.exists() and executable_path.with_suffix(".exe").exists():
        executable_path = executable_path.with_suffix(".exe")

    return c_path, executable_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AlgoC compiler: AlgoC -> C -> executable",
        usage="python algoc.py source.algoc [--no-gcc]",
    )
    parser.add_argument("source", help="Source file for AlgoC")
    parser.add_argument(
        "--no-gcc",
        action="store_true",
        help="Generate only the C file, without compiling the executable with gcc.",
    )
    args = parser.parse_args()

    try:
        c_path, executable_path = compile_algoc(args.source, no_gcc=args.no_gcc)

        print(f"C code generated as {c_path}.")
        if executable_path is not None:
            print(f"Executable generated as {executable_path}.")

    except AlgoCError as exc:
        print(f"AlgoC error: {exc}")
        raise SystemExit(1)
