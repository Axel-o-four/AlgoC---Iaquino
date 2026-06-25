# Code generator for AlgoC

from dataclasses import dataclass
from typing import List, Optional
from ast_nodes import *
from symbol_table import AlgoCError, Symbol, SymbolTable

@dataclass
class CExpr:
    code: str
    type: TypeNode


class CCodeGenerator:
    STRING_SIZE = 256

    def __init__(self) -> None:
        self.global_table = SymbolTable()
        self.current_table = SymbolTable()
        self.current_return_type: Optional[TypeNode] = None
        self.temp_counter = 0

    def generate(self, program: ProgramNode) -> str:
        self._semantic_analysis(program)
        return self._emit_program(program)

    # Semantic analysis

    def _semantic_analysis(self, program: ProgramNode) -> None:
        self.global_table = SymbolTable()

        for declaration in program.declarations:
            if isinstance(declaration, VarDeclNode):
                self._declare_var_decl(self.global_table, declaration)
            elif isinstance(declaration, FunctionDefNode):
                if declaration.return_type.name == "string" or declaration.return_type.is_array():
                    raise AlgoCError(
                        f"The function {declaration.name} has the return type {declaration.return_type} not supported by C."
                    )
                self.global_table.declare(
                    Symbol(
                        name=declaration.name,
                        kind="function",
                        params=declaration.params,
                        return_type=declaration.return_type,
                    )
                )
            elif isinstance(declaration, ProcedureDefNode):
                self.global_table.declare(
                    Symbol(
                        name=declaration.name,
                        kind="procedure",
                        params=declaration.params,
                    )
                )

        for declaration in program.declarations:
            if isinstance(declaration, FunctionDefNode):
                self._check_function(declaration)
            elif isinstance(declaration, ProcedureDefNode):
                self._check_procedure(declaration)

        # Corpo principale.
        self.current_table = self.global_table.copy()
        self.current_return_type = None
        self._check_body(program.body)

    def _declare_var_decl(self, table: SymbolTable, decl: VarDeclNode) -> None:
        for name in decl.names:
            table.declare(Symbol(name=name, kind="variable", type=decl.var_type))

    def _check_function(self, node: FunctionDefNode) -> None:
        self.current_table = self.global_table.copy()
        self.current_return_type = node.return_type
        self._declare_params(node.params)
        has_return = self._check_body(node.body)
        if not has_return:
            raise AlgoCError(f"The function {node.name} does not contain any return")
        self.current_return_type = None

    def _check_procedure(self, node: ProcedureDefNode) -> None:
        self.current_table = self.global_table.copy()
        self.current_return_type = None
        self._declare_params(node.params)
        self._check_body(node.body)

    def _declare_params(self, params: List[ParamNode]) -> None:
        for param in params:
            self.current_table.declare(
                Symbol(
                    name=param.name,
                    kind="parameter",
                    type=param.param_type,
                    direction=param.direction,
                )
            )

    def _check_body(self, body: BodyNode) -> bool:
        has_return = False
        for statement in body.statements:
            if isinstance(statement, VarDeclNode):
                self._declare_var_decl(self.current_table, statement)
            elif isinstance(statement, ReturnNode):
                self._check_return(statement)
                has_return = True
            else:
                if self._check_statement(statement):
                    has_return = True
        return has_return

    def _check_statement(self, node: ASTNode) -> bool:
        if isinstance(node, AssignNode):
            target_type = self._check_lvalue(node.target)
            value_type = self._check_expr(node.value)
            if not self._assignable(target_type, value_type):
                raise AlgoCError(f"Assignment not valid: {target_type} <- {value_type}.")
            return False

        if isinstance(node, CallStmtNode):
            self._check_call(node.call, as_statement=True)
            return False

        if isinstance(node, OutputNode):
            for arg in node.args:
                arg_type = self._check_expr(arg.expr)
                if arg_type.is_array():
                    raise AlgoCError("It's not possible to print an array.")
            return False

        if isinstance(node, InputNode):
            for arg in node.args:
                self._check_lvalue(arg.expr)
            return False

        if isinstance(node, IfNode):
            self._require_boolean(self._check_expr(node.condition), "if condition")
            has_return = self._check_body(node.then_body)
            for elif_node in node.elifs:
                self._require_boolean(self._check_expr(elif_node.condition), "elseif condition")
                if self._check_body(elif_node.body):
                    has_return = True
            if node.else_body and self._check_body(node.else_body):
                has_return = True
            return has_return

        if isinstance(node, WhileNode):
            self._require_boolean(self._check_expr(node.condition), "while condition")
            return self._check_body(node.body)

        if isinstance(node, DoWhileNode):
            has_return = self._check_body(node.body)
            self._require_boolean(self._check_expr(node.condition), "do-while condition")
            return has_return

        if isinstance(node, ForNode):
            symbol = self._require_variable(node.variable)
            if symbol.type.name != "int" or symbol.type.is_array():
                raise AlgoCError("The variable of the for loop must be an integer")
            self._require_int(self._check_expr(node.start), "start of the for loop")
            self._require_int(self._check_expr(node.final), "end of the for loop")
            return self._check_body(node.body)

        raise AlgoCError(f"Statement not handled semantically: {type(node).__name__}")

    def _check_return(self, node: ReturnNode) -> None:
        if self.current_return_type is None:
            raise AlgoCError("return used outside a function")
        value_type = self._check_expr(node.value)
        if not self._assignable(self.current_return_type, value_type):
            raise AlgoCError(f"Invalid return: expected {self.current_return_type}, got {value_type}")

    def _check_expr(self, node: ASTNode) -> TypeNode:
        if isinstance(node, IntConstNode):
            node.inferred_type = TypeNode("int")
            return node.inferred_type

        if isinstance(node, RealConstNode):
            node.inferred_type = TypeNode("real")
            return node.inferred_type

        if isinstance(node, CharConstNode):
            node.inferred_type = TypeNode("char")
            return node.inferred_type

        if isinstance(node, StringConstNode):
            node.inferred_type = TypeNode("string")
            return node.inferred_type

        if isinstance(node, BooleanConstNode):
            node.inferred_type = TypeNode("boolean")
            return node.inferred_type

        if isinstance(node, IdentifierNode):
            symbol = self._require_variable(node.name)
            node.inferred_type = symbol.type
            return symbol.type

        if isinstance(node, ArrayAccessNode):
            array_symbol = self._require_variable(node.name)
            if not array_symbol.type.is_array():
                raise AlgoCError(f"{node.name} is not an array")
            self._require_int(self._check_expr(node.index), "array index")
            node.inferred_type = array_symbol.type.copy_as_scalar()
            return node.inferred_type

        if isinstance(node, CallNode):
            call_type = self._check_call(node, as_statement=False)
            node.inferred_type = call_type
            return call_type

        if isinstance(node, UnaryOpNode):
            operand_type = self._check_expr(node.operand)
            if node.op == "!":
                self._require_boolean(operand_type, "operator !")
                node.inferred_type = TypeNode("boolean")
            elif node.op == "-":
                if not operand_type.is_numeric():
                    raise AlgoCError("The unary operator requires an int or real")
                node.inferred_type = operand_type
            return node.inferred_type

        if isinstance(node, BinaryOpNode):
            return self._check_binary(node)

        raise AlgoCError(f"Expression not handled semantically: {type(node).__name__}")

    def _check_binary(self, node: BinaryOpNode) -> TypeNode:
        left_type = self._check_expr(node.left)
        right_type = self._check_expr(node.right)

        if node.op in ("+", "-", "*", "/"):
            if not left_type.is_numeric() or not right_type.is_numeric():
                raise AlgoCError(f"The operator {node.op} requires numeric operands")
            if node.op == "/" or left_type.name == "real" or right_type.name == "real":
                node.inferred_type = TypeNode("real")
            else:
                node.inferred_type = TypeNode("int")
            return node.inferred_type

        if node.op == "%":
            self._require_int(left_type, "operator %")
            self._require_int(right_type, "operator %")
            node.inferred_type = TypeNode("int")
            return node.inferred_type

        if node.op in ("<", "<=", ">", ">="):
            if not left_type.is_numeric() or not right_type.is_numeric():
                raise AlgoCError(f"The operator {node.op} requires numeric operands")
            node.inferred_type = TypeNode("boolean")
            return node.inferred_type

        if node.op in ("=", "<>"):
            if not self._comparable(left_type, right_type):
                raise AlgoCError(f"Invalid comparison: {left_type} {node.op} {right_type}")
            node.inferred_type = TypeNode("boolean")
            return node.inferred_type

        if node.op in ("&", "|"):
            self._require_boolean(left_type, f"operator {node.op}")
            self._require_boolean(right_type, f"operator {node.op}")
            node.inferred_type = TypeNode("boolean")
            return node.inferred_type

        raise AlgoCError(f"Unrecognized operator: {node.op}")

    def _check_call(self, node: CallNode, as_statement: bool) -> TypeNode:
        symbol = self.global_table.lookup(node.name)
        if symbol is None or symbol.kind not in ("function", "procedure"):
            raise AlgoCError(f"Function/procedure not declared: {node.name}")

        params = symbol.params or []
        if len(params) != len(node.args):
            raise AlgoCError(
                f"Call to {node.name} with incorrect number of arguments: expected {len(params)}, got {len(node.args)}"
            )

        for param, arg in zip(params, node.args):
            if param.is_out():
                arg_type = self._check_lvalue(arg)
            else:
                arg_type = self._check_expr(arg)
            if not self._assignable(param.param_type, arg_type):
                raise AlgoCError(
                    f"Parameter {param.name} of {node.name}: expected {param.param_type}, got {arg_type}"
                )

        if symbol.kind == "procedure":
            if not as_statement:
                raise AlgoCError(f"Procedure {node.name} does not return a value")
            return TypeNode("void")

        return symbol.return_type

    def _check_lvalue(self, node: ASTNode) -> TypeNode:
        if isinstance(node, IdentifierNode):
            symbol = self._require_variable(node.name)
            return symbol.type
        if isinstance(node, ArrayAccessNode):
            return self._check_expr(node)
        raise AlgoCError("An lvalue was expected")

    def _require_variable(self, name: str) -> Symbol:
        symbol = self.current_table.require(name)
        if symbol.kind not in ("variable", "parameter"):
            raise AlgoCError(f"{name} is not a variable")
        return symbol

    def _require_boolean(self, type_node: TypeNode, context: str) -> None:
        if type_node.name != "boolean" or type_node.is_array():
            raise AlgoCError(f"{context}: expected boolean, got {type_node}")

    def _require_int(self, type_node: TypeNode, context: str) -> None:
        if type_node.name != "int" or type_node.is_array():
            raise AlgoCError(f"{context}: expected int, got {type_node}")

    def _assignable(self, target: TypeNode, source: TypeNode) -> bool:
        if target.is_array() or source.is_array():
            return self._same_type(target, source)
        if target.name == source.name:
            return True
        if target.name == "real" and source.name == "int":
            return True
        return False

    def _comparable(self, a: TypeNode, b: TypeNode) -> bool:
        if a.is_array() or b.is_array():
            return False
        if a.is_numeric() and b.is_numeric():
            return True
        return a.name == b.name

    def _same_type(self, a: TypeNode, b: TypeNode) -> bool:
        return a.name == b.name and a.size == b.size

    # Code generation

    def _emit_program(self, program: ProgramNode) -> str:
        lines: List[str] = []
        lines.extend(self._runtime())

        global_vars = [d for d in program.declarations if isinstance(d, VarDeclNode)]
        if global_vars:
            lines.append("/* Global variables */")
            for decl in global_vars:
                lines.extend(self._emit_decl(decl, indent=0))
            lines.append("")

        routines = [d for d in program.declarations if isinstance(d, (FunctionDefNode, ProcedureDefNode))]
        if routines:
            lines.append("/* Prototypes */")
            for routine in routines:
                lines.append(self._prototype(routine) + ";")
            lines.append("")

        for routine in routines:
            if isinstance(routine, FunctionDefNode):
                lines.extend(self._emit_function(routine))
            else:
                lines.extend(self._emit_procedure(routine))
            lines.append("")

        lines.extend(self._emit_main(program.body))
        return "\n".join(lines).rstrip() + "\n"

    def _runtime(self) -> List[str]:
        return [
            "#include <stdio.h>",
            "#include <stdbool.h>",
            "#include <string.h>",
            "",
            f"#define ALGOC_STRING_SIZE {self.STRING_SIZE}",
            "",
            "static void algoc_assign_string(char *dest, const char *src) {",
            "    strncpy(dest, src, ALGOC_STRING_SIZE - 1);",
            "    dest[ALGOC_STRING_SIZE - 1] = '\\0';",
            "}",
            "",
        ]

    def _prototype(self, routine: ASTNode) -> str:
        if isinstance(routine, FunctionDefNode):
            return f"{self._c_type(routine.return_type)} {routine.name}({self._c_params(routine.params)})"
        if isinstance(routine, ProcedureDefNode):
            return f"void {routine.name}({self._c_params(routine.params)})"
        raise AlgoCError("Unrecognized routine")

    def _emit_function(self, node: FunctionDefNode) -> List[str]:
        self.current_table = self.global_table.copy()
        self._add_params_to_current_table(node.params)
        self._add_local_decls_to_current_table(node.body)
        lines = [self._prototype(node) + " {"]
        lines.extend(self._emit_local_declarations(node.body, indent=1))
        lines.extend(self._emit_body(node.body, indent=1))
        lines.append("}")
        return lines

    def _emit_procedure(self, node: ProcedureDefNode) -> List[str]:
        self.current_table = self.global_table.copy()
        self._add_params_to_current_table(node.params)
        self._add_local_decls_to_current_table(node.body)
        lines = [self._prototype(node) + " {"]
        lines.extend(self._emit_local_declarations(node.body, indent=1))
        lines.extend(self._emit_body(node.body, indent=1))
        lines.append("}")
        return lines

    def _emit_main(self, body: BodyNode) -> List[str]:
        self.current_table = self.global_table.copy()
        self._add_local_decls_to_current_table(body)
        lines = ["int main(void) {"]
        lines.extend(self._emit_local_declarations(body, indent=1))
        lines.extend(self._emit_body(body, indent=1))
        lines.append("    return 0;")
        lines.append("}")
        return lines

    def _add_params_to_current_table(self, params: List[ParamNode]) -> None:
        for param in params:
            if not self.current_table.contains(param.name):
                self.current_table.declare(
                    Symbol(param.name, "parameter", param.param_type, direction=param.direction)
                )


    def _add_local_decls_to_current_table(self, body: BodyNode) -> None:
        for decl in self._collect_var_decls(body):
            for name in decl.names:
                if not self.current_table.contains(name):
                    self.current_table.declare(Symbol(name=name, kind="variable", type=decl.var_type))

    def _emit_local_declarations(self, body: BodyNode, indent: int) -> List[str]:
        lines: List[str] = []
        for decl in self._collect_var_decls(body):
            lines.extend(self._emit_decl(decl, indent))
        if lines:
            lines.append("")
        return lines

    def _collect_var_decls(self, body: BodyNode) -> List[VarDeclNode]:
        result: List[VarDeclNode] = []
        for statement in body.statements:
            if isinstance(statement, VarDeclNode):
                result.append(statement)
            elif isinstance(statement, IfNode):
                result.extend(self._collect_var_decls(statement.then_body))
                for elif_node in statement.elifs:
                    result.extend(self._collect_var_decls(elif_node.body))
                if statement.else_body:
                    result.extend(self._collect_var_decls(statement.else_body))
            elif isinstance(statement, WhileNode):
                result.extend(self._collect_var_decls(statement.body))
            elif isinstance(statement, DoWhileNode):
                result.extend(self._collect_var_decls(statement.body))
            elif isinstance(statement, ForNode):
                result.extend(self._collect_var_decls(statement.body))
        return result

    def _emit_decl(self, decl: VarDeclNode, indent: int) -> List[str]:
        return [self._i(indent) + self._c_decl(name, decl.var_type) + ";" for name in decl.names]

    def _emit_body(self, body: BodyNode, indent: int) -> List[str]:
        lines: List[str] = []
        for statement in body.statements:
            if isinstance(statement, VarDeclNode):
                continue
            lines.extend(self._emit_statement(statement, indent))
        return lines

    def _emit_statement(self, node: ASTNode, indent: int) -> List[str]:
        if isinstance(node, AssignNode):
            target = self._emit_lvalue(node.target)
            value = self._emit_expr(node.value)
            if target.type.name == "string" and not target.type.is_array():
                return [self._i(indent) + f"algoc_assign_string({target.code}, {value.code});"]
            return [self._i(indent) + f"{target.code} = {value.code};"]

        if isinstance(node, CallStmtNode):
            return [self._i(indent) + self._emit_call(node.call).code + ";"]

        if isinstance(node, OutputNode):
            lines: List[str] = []
            for arg in node.args:
                lines.append(self._i(indent) + self._printf_line(arg.expr))
            lines.append(self._i(indent) + 'printf("\\n");')
            return lines

        if isinstance(node, InputNode):
            lines: List[str] = []
            for arg in node.args:
                lines.extend(self._scanf_lines(arg.expr, indent))
            return lines

        if isinstance(node, IfNode):
            cond = self._emit_expr(node.condition).code
            lines = [self._i(indent) + f"if ({cond}) {{"]
            lines.extend(self._emit_body(node.then_body, indent + 1))
            for elif_node in node.elifs:
                elif_cond = self._emit_expr(elif_node.condition).code
                lines.append(self._i(indent) + f"}} else if ({elif_cond}) {{")
                lines.extend(self._emit_body(elif_node.body, indent + 1))
            if node.else_body:
                lines.append(self._i(indent) + "} else {")
                lines.extend(self._emit_body(node.else_body, indent + 1))
            lines.append(self._i(indent) + "}")
            return lines

        if isinstance(node, WhileNode):
            cond = self._emit_expr(node.condition).code
            lines = [self._i(indent) + f"while ({cond}) {{"]
            lines.extend(self._emit_body(node.body, indent + 1))
            lines.append(self._i(indent) + "}")
            return lines

        if isinstance(node, DoWhileNode):
            lines = [self._i(indent) + "do {"]
            lines.extend(self._emit_body(node.body, indent + 1))
            cond = self._emit_expr(node.condition).code
            lines.append(self._i(indent) + f"}} while ({cond});")
            return lines

        if isinstance(node, ForNode):
            start = self._emit_expr(node.start).code
            final = self._emit_expr(node.final).code
            lines = [
                self._i(indent)
                + f"for ({node.variable} = {start}; {node.variable} <= {final}; {node.variable}++) {{"
            ]
            lines.extend(self._emit_body(node.body, indent + 1))
            lines.append(self._i(indent) + "}")
            return lines

        if isinstance(node, ReturnNode):
            value = self._emit_expr(node.value).code
            return [self._i(indent) + f"return {value};"]

        raise AlgoCError(f"Statement non generabile: {type(node).__name__}")

    def _emit_expr(self, node: ASTNode) -> CExpr:
        if isinstance(node, IntConstNode):
            return CExpr(str(node.value), TypeNode("int"))
        if isinstance(node, RealConstNode):
            return CExpr(repr(node.value), TypeNode("real"))
        if isinstance(node, CharConstNode):
            return CExpr(node.value, TypeNode("char"))
        if isinstance(node, StringConstNode):
            return CExpr(node.value, TypeNode("string"))
        if isinstance(node, BooleanConstNode):
            return CExpr("true" if node.value else "false", TypeNode("boolean"))
        if isinstance(node, IdentifierNode):
            symbol = self.current_table.require(node.name)
            code = self._identifier_code(symbol)
            return CExpr(code, symbol.type)
        if isinstance(node, ArrayAccessNode):
            symbol = self.current_table.require(node.name)
            index = self._emit_expr(node.index).code
            return CExpr(f"{node.name}[{index}]", symbol.type.copy_as_scalar())
        if isinstance(node, CallNode):
            return self._emit_call(node)
        if isinstance(node, UnaryOpNode):
            operand = self._emit_expr(node.operand)
            return CExpr(f"({node.op}{operand.code})", node.inferred_type or operand.type)
        if isinstance(node, BinaryOpNode):
            left = self._emit_expr(node.left)
            right = self._emit_expr(node.right)
            return self._emit_binary(node, left, right)
        raise AlgoCError(f"Espressione non generabile: {type(node).__name__}")

    def _emit_binary(self, node: BinaryOpNode, left: CExpr, right: CExpr) -> CExpr:
        if node.op in ("&", "|"):
            c_op = "&&" if node.op == "&" else "||"
            return CExpr(f"({left.code} {c_op} {right.code})", TypeNode("boolean"))

        if node.op in ("=", "<>"):
            if left.type.name == "string" and right.type.name == "string":
                comparison = f"(strcmp({left.code}, {right.code}) == 0)"
                if node.op == "<>":
                    comparison = f"(!{comparison})"
                return CExpr(comparison, TypeNode("boolean"))
            c_op = "==" if node.op == "=" else "!="
            return CExpr(f"({left.code} {c_op} {right.code})", TypeNode("boolean"))

        return CExpr(f"({left.code} {node.op} {right.code})", node.inferred_type or TypeNode("int"))

    def _emit_call(self, node: CallNode) -> CExpr:
        symbol = self.global_table.require(node.name)
        params = symbol.params or []
        args = []
        for param, arg in zip(params, node.args):
            if param.is_out():
                arg_code = self._emit_lvalue(arg).code
                if self._needs_address_for_out(param.param_type):
                    arg_code = f"&{arg_code}"
                args.append(arg_code)
            else:
                args.append(self._emit_expr(arg).code)
        return_type = symbol.return_type if symbol.kind == "function" else TypeNode("void")
        return CExpr(f"{node.name}({', '.join(args)})", return_type)

    def _emit_lvalue(self, node: ASTNode) -> CExpr:
        if isinstance(node, IdentifierNode):
            symbol = self.current_table.require(node.name)
            return CExpr(self._identifier_code(symbol), symbol.type)
        if isinstance(node, ArrayAccessNode):
            return self._emit_expr(node)
        raise AlgoCError("Lvalue non generabile")

    def _identifier_code(self, symbol: Symbol) -> str:
        if symbol.kind == "parameter" and symbol.direction == "out" and self._needs_address_for_out(symbol.type):
            return f"(*{symbol.name})"
        return symbol.name

    def _needs_address_for_out(self, type_node: TypeNode) -> bool:
        return not type_node.is_array() and type_node.name != "string"

    def _printf_line(self, expr_node: ASTNode) -> str:
        expr = self._emit_expr(expr_node)
        if expr.type.name == "int":
            return f'printf("%d", {expr.code});'
        if expr.type.name == "real":
            return f'printf("%g", {expr.code});'
        if expr.type.name == "char":
            return f'printf("%c", {expr.code});'
        if expr.type.name == "string":
            return f'printf("%s", {expr.code});'
        if expr.type.name == "boolean":
            return f'printf("%s", ({expr.code}) ? "true" : "false");'
        raise AlgoCError(f"Tipo non stampabile: {expr.type}")

    def _scanf_lines(self, expr_node: ASTNode, indent: int) -> List[str]:
        target = self._emit_lvalue(expr_node)
        if target.type.name == "int":
            return [self._i(indent) + f'scanf("%d", &{target.code});']
        if target.type.name == "real":
            return [self._i(indent) + f'scanf("%lf", &{target.code});']
        if target.type.name == "char":
            return [self._i(indent) + f'scanf(" %c", &{target.code});']
        if target.type.name == "string":
            return [self._i(indent) + f'scanf("%255s", {target.code});']
        if target.type.name == "boolean":
            tmp = self._new_temp("bool_input")
            return [
                self._i(indent) + f"int {tmp};",
                self._i(indent) + f'scanf("%d", &{tmp});',
                self._i(indent) + f"{target.code} = ({tmp} != 0);",
            ]
        raise AlgoCError(f"Tipo non leggibile da input: {target.type}")

    # Code generation utilities

    def _c_type(self, type_node: TypeNode) -> str:
        if type_node.name == "int":
            return "int"
        if type_node.name == "real":
            return "double"
        if type_node.name == "char":
            return "char"
        if type_node.name == "boolean":
            return "bool"
        if type_node.name == "string":
            return "char"
        if type_node.name == "void":
            return "void"
        raise AlgoCError(f"Tipo C non riconosciuto: {type_node}")

    def _c_decl(self, name: str, type_node: TypeNode) -> str:
        base = self._c_type(type_node)
        if type_node.name == "string" and not type_node.is_array():
            return f"char {name}[ALGOC_STRING_SIZE] = \"\""
        if type_node.is_array():
            return f"{base} {name}[{type_node.size}]"
        return f"{base} {name}"

    def _c_params(self, params: List[ParamNode]) -> str:
        if not params:
            return "void"
        return ", ".join(self._c_param(param) for param in params)

    def _c_param(self, param: ParamNode) -> str:
        base = self._c_type(param.param_type)
        if param.param_type.name == "string":
            return f"char {param.name}[]"
        if param.param_type.is_array():
            return f"{base} {param.name}[]"
        if param.is_out():
            return f"{base} *{param.name}"
        return f"{base} {param.name}"

    def _new_temp(self, prefix: str) -> str:
        self.temp_counter += 1
        return f"__algoc_{prefix}_{self.temp_counter}"

    def _i(self, indent: int) -> str:
        return "    " * indent
