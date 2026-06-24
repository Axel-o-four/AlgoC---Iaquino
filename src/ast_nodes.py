# AST nodes for AlgoC.

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ASTNode: # base node
    inferred_type: Optional["TypeNode"] = field(default=None, init=False, repr=False)

@dataclass
class TypeNode(ASTNode):
    name: str
    size: Optional[int] = None

    def is_array(self) -> bool:
        return self.size is not None

    def is_numeric(self) -> bool:
        return self.name in ("int", "real") and not self.is_array()

    def copy_as_scalar(self) -> "TypeNode":
        return TypeNode(self.name)

    def __str__(self) -> str:
        if self.is_array():
            return f"{self.name}[{self.size}]"
        return self.name

@dataclass
class ProgramNode(ASTNode):
    declarations: List[ASTNode]
    body: "BodyNode"

@dataclass
class BodyNode(ASTNode):
    statements: List[ASTNode]

@dataclass
class VarDeclNode(ASTNode):
    names: List[str]
    var_type: TypeNode

@dataclass
class ParamNode(ASTNode):
    name: str
    param_type: TypeNode
    direction: str = "in"

    def is_out(self) -> bool:
        return self.direction == "out"

@dataclass
class FunctionDefNode(ASTNode):
    name: str
    params: List[ParamNode]
    return_type: TypeNode
    body: BodyNode

@dataclass
class ProcedureDefNode(ASTNode):
    name: str
    params: List[ParamNode]
    body: BodyNode

@dataclass
class AssignNode(ASTNode):
    target: ASTNode
    value: ASTNode

@dataclass
class CallStmtNode(ASTNode):
    call: "CallNode"

@dataclass
class OutputNode(ASTNode):
    args: List["IOArgNode"]

@dataclass
class InputNode(ASTNode):
    args: List["IOArgNode"]

@dataclass
class IOArgNode(ASTNode):
    expr: ASTNode
    dollar: bool = False

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then_body: BodyNode
    elifs: List["ElifNode"]
    else_body: Optional[BodyNode] = None

@dataclass
class ElifNode(ASTNode):
    condition: ASTNode
    body: BodyNode

@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: BodyNode

@dataclass
class DoWhileNode(ASTNode):
    body: BodyNode
    condition: ASTNode

@dataclass
class ForNode(ASTNode):
    variable: str
    start: ASTNode
    final: ASTNode
    body: BodyNode

@dataclass
class ReturnNode(ASTNode):
    value: ASTNode

@dataclass
class IdentifierNode(ASTNode):
    name: str

@dataclass
class ArrayAccessNode(ASTNode):
    name: str
    index: ASTNode

@dataclass
class CallNode(ASTNode):
    name: str
    args: List[ASTNode]

@dataclass
class BinaryOpNode(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode

@dataclass
class UnaryOpNode(ASTNode):
    op: str
    operand: ASTNode

@dataclass
class IntConstNode(ASTNode):
    value: int

@dataclass
class RealConstNode(ASTNode):
    value: float

@dataclass
class CharConstNode(ASTNode):
    value: str

@dataclass
class StringConstNode(ASTNode):
    value: str

@dataclass
class BooleanConstNode(ASTNode):
    value: bool