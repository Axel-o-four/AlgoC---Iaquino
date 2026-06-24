# Symbol tables for AlgoC

from dataclasses import dataclass
from typing import Dict, List, Optional
from ast_nodes import TypeNode, ParamNode

class AlgoCError(Exception):
    """Generic exception for errors"""
    
@dataclass
class Symbol:
    name: str
    kind: str # variable, function, procedure, parameter
    type: Optional[TypeNode] = None
    params: Optional[List[ParamNode]] = None
    return_type: Optional[TypeNode] = None
    direction: str = "in"

    def is_out(self) -> bool:
        return self.direction == "out"

class SymbolTable:
    def __init__(self) -> None:
        self._symbols: Dict[str, Symbol] = {}

    def declare(self, symbol: Symbol) -> None:
        if symbol.name in self._symbols:
            raise AlgoCError(f"The symbol {symbol.name} is already declared.")
        self._symbols[symbol.name] = symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        return self._symbols.get(name)

    def require(self, name: str) -> Symbol:
        symbol = self.lookup(name)
        if symbol is None:
            raise AlgoCError(f"The symbol {name} is not declared.")
        return symbol

    def contains(self, name: str) -> bool:
        return name in self._symbols

    def copy(self) -> "SymbolTable":
        new_table = SymbolTable()
        new_table._symbols = dict(self._symbols)
        return new_table

    def items(self):
        return self._symbols.items()