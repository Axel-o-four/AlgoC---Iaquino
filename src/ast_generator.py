# AST generator for AlgoC

from pathlib import Path
from typing import List, Optional, Union
from lark import Lark, Tree, Token, UnexpectedInput
from ast_nodes import *
from symbol_table import AlgoCError

EXPR_TOKEN_TYPES = {
    "ID",
    "INT_CONST",
    "REAL_CONST",
    "CHAR_CONST",
    "STRING_CONST",
    "TRUE",
    "FALSE",
}

EXPR_RULES = {
    "primary_expr",
    "array_access",
    "func_call",
    "or_op",
    "and_op",
    "eq_op",
    "neq_op",
    "lt_op",
    "le_op",
    "gt_op",
    "ge_op",
    "add_op",
    "sub_op",
    "mul_op",
    "div_op",
    "mod_op",
    "not_op",
    "neg_op",
}

BINARY_OPS = {
    "or_op": "|",
    "and_op": "&",
    "eq_op": "=",
    "neq_op": "<>",
    "lt_op": "<",
    "le_op": "<=",
    "gt_op": ">",
    "ge_op": ">=",
    "add_op": "+",
    "sub_op": "-",
    "mul_op": "*",
    "div_op": "/",
    "mod_op": "%",
}

UNARY_OPS = {
    "not_op": "!",
    "neg_op": "-",
}

class ASTGenerator:
    def __init__(self, grammar_path: str = "grammar.lark") -> None:
        self.grammar_path = Path(grammar_path)
        self.parser = Lark(
            self._load_grammar(),
            parser="lalr",
            keep_all_tokens=True,
            start="program",
        )

    def _load_grammar(self) -> str:
        grammar = self.grammar_path.read_text(encoding="utf-8")
        return grammar

    def parse(self, source_code: str) -> Tree:
        try:
            return self.parser.parse(source_code)
        except UnexpectedInput as exc:
            raise AlgoCError(f"Syntax error at line {exc.line}, column {exc.column}.") from exc

    def generate(self, source_code: str) -> ProgramNode:
        parse_tree = self.parse(source_code)
        return self._program(parse_tree)

    def generate_from_file(self, source_path: str) -> ProgramNode:
        source = Path(source_path).read_text(encoding="utf-8")
        return self.generate(source)

    # AST construction methods
    # Program structure

    def _program(self, tree: Tree) -> ProgramNode:
        declarations = []
        main_body: Optional[BodyNode] = None

        for child in tree.children:
            if self._is_tree(child, "global_decls"):
                declarations.extend(self._global_decl(child))
            elif self._is_tree(child, "body"):
                main_body = self._body(child)

        if main_body is None:
            raise AlgoCError("Program's main body is missing.")

        return ProgramNode(declarations=declarations, body=main_body)

    def _global_decl(self, tree: Tree) -> List[object]:
        inner = self._first_tree(tree)
        if inner is None:
            return []

        name = self._data(inner)
        if name == "var_decl":
            return self._var_decl(inner)
        if name == "function_def":
            return [self._function_def(inner)]
        if name == "procedure_def":
            return [self._procedure_def(inner)]

        raise AlgoCError(f"Global declaration {name} not recognized.")

    def _body(self, tree: Tree) -> BodyNode:
        statements = []
        for child in tree.children:
            if not isinstance(child, Tree):
                continue

            name = self._data(child)
            if name == "var_decl":
                statements.extend(self._var_decl(child))
            else:
                statements.append(self._statement(child))

        return BodyNode(statements=statements)

    # Variable declarations

    def _var_decl(self, tree: Tree) -> List[VarDeclNode]:
        result: List[VarDeclNode] = []
        for decl_tree in self._find_trees(tree, "var_declaration"):
            ids_tree = self._first_tree(decl_tree, "ids")
            type_tree = self._first_tree(decl_tree, "type")
            if ids_tree is None or type_tree is None:
                raise AlgoCError("Variable declaration is malformed.")
            result.append(VarDeclNode(names=self._ids(ids_tree), var_type=self._type(type_tree)))
        return result

    def _ids(self, tree: Tree) -> List[str]:
        return [token.value for token in tree.children if isinstance(token, Token) and token.type == "ID"]

    def _type(self, tree: Tree) -> TypeNode:
        inner = self._first_tree(tree)
        if inner is None:
            raise AlgoCError("Type not recognized.")

        name = self._data(inner)
        if name == "primitive_type":
            token = self._first_token(inner)
            return TypeNode(token.value)

        if name == "array_type":
            primitive = self._first_tree(inner, "primitive_type")
            size_token = self._first_token(inner, "INT_CONST")
            if primitive is None or size_token is None:
                raise AlgoCError("Array malformed.")
            return TypeNode(self._first_token(primitive).value, int(size_token.value))

        raise AlgoCError(f"Type not recognized: {name}")

    # Funciton and procedure definition

    def _function_def(self, tree: Tree) -> FunctionDefNode:
        name = self._first_token(tree, "ID").value
        params_tree = self._first_tree(tree, "func_params")
        return_type_tree = self._first_tree(tree, "return_type")
        body_tree = self._first_tree(tree, "body")

        if return_type_tree is None or body_tree is None:
            raise AlgoCError(f"Function {name} is malformed")

        return FunctionDefNode(
            name=name,
            params=self._func_params(params_tree) if params_tree else [],
            return_type=self._return_type(return_type_tree),
            body=self._body(body_tree),
        )
    
    def _func_params(self, tree: Tree) -> List[ParamNode]:
        return [self._func_param(t) for t in self._find_direct_trees(tree, "func_param")]

    def _func_param(self, tree: Tree) -> ParamNode:
        name = self._first_token(tree, "ID").value
        type_tree = self._first_tree(tree, "type")
        if type_tree is None:
            raise AlgoCError(f"Parameter {name} specified without type.")
        return ParamNode(name=name, param_type=self._type(type_tree), direction="in")

    def _procedure_def(self, tree: Tree) -> ProcedureDefNode:
        name = self._first_token(tree, "ID").value
        params_tree = self._first_tree(tree, "proc_params")
        body_tree = self._first_tree(tree, "body")

        if body_tree is None:
            raise AlgoCError(f"Procedure {name} is malformed.")

        return ProcedureDefNode(
            name=name,
            params=self._proc_params(params_tree) if params_tree else [],
            body=self._body(body_tree),
        )

    def _proc_params(self, tree: Tree) -> List[ParamNode]:
        return [self._proc_param(t) for t in self._find_direct_trees(tree, "proc_param")]

    def _proc_param(self, tree: Tree) -> ParamNode:
        out = any(isinstance(c, Token) and c.type == "OUT" for c in tree.children)
        name = self._first_token(tree, "ID").value
        type_tree = self._first_tree(tree, "type")
        if type_tree is None:
            raise AlgoCError(f"Parameter {name} specified without a type.")
        return ParamNode(name=name, param_type=self._type(type_tree), direction="out" if out else "in")

    def _return_type(self, tree: Tree) -> TypeNode:
        type_tree = self._first_tree(tree, "type")
        if type_tree is None:
            raise AlgoCError("Return type missing.")
        return self._type(type_tree)

    # Statements

    def _statement(self, tree: Tree):
        name = self._data(tree)

        if name == "assignment_stmt":
            target_tree = self._first_tree(tree, "lvalue")
            value = self._first_expr_after(tree.children, target_tree)
            return AssignNode(target=self._lvalue(target_tree), value=value)

        if name == "function_call_stmt":
            call_tree = self._first_tree(tree, "func_call")
            return CallStmtNode(call=self._func_call(call_tree))

        if name == "output_stmt":
            args_tree = self._first_tree(tree, "io_args")
            return OutputNode(args=self._io_args(args_tree))

        if name == "input_stmt":
            args_tree = self._first_tree(tree, "io_args")
            return InputNode(args=self._io_args(args_tree))

        if name == "return_stmt":
            value = self._first_expr_in(tree.children)
            return ReturnNode(value=value)

        if name == "if_stmt":
            return self._if_stmt(tree)

        if name == "while_stmt":
            condition = self._first_expr_in(tree.children)
            body_tree = self._first_tree(tree, "body")
            return WhileNode(condition=condition, body=self._body(body_tree))

        if name == "do_while_stmt":
            body_tree = self._first_tree(tree, "body")
            condition = self._first_expr_after(tree.children, body_tree)
            return DoWhileNode(body=self._body(body_tree), condition=condition)

        if name == "for_stmt":
            init_tree = self._first_tree(tree, "for_init")
            final_tree = self._first_tree(tree, "for_final")
            body_tree = self._first_tree(tree, "body")
            variable, start = self._for_init(init_tree)
            final = self._for_final(final_tree)
            return ForNode(variable=variable, start=start, final=final, body=self._body(body_tree))

        raise AlgoCError(f"Statement {name} not recognized.")

    def _lvalue(self, tree: Tree):
        for child in tree.children:
            if isinstance(child, Token) and child.type == "ID":
                return IdentifierNode(child.value)
            if self._is_tree(child, "array_access"):
                return self._array_access(child)
        raise AlgoCError("Lvalue not recognized.")
    
    def _array_access(self, tree: Tree) -> ArrayAccessNode:
        name = self._first_token(tree, "ID").value
        exprs = [c for c in tree.children if self._is_expr_item(c)]
        for child in tree.children:
            if self._is_expr_item(child) and not (isinstance(child, Token) and child.type == "ID" and child.value == name):
                return ArrayAccessNode(name=name, index=self._expr(child))
        raise AlgoCError(f"Access to array {name} without an index.")

    def _if_stmt(self, tree: Tree) -> IfNode:
        condition = self._first_expr_in(tree.children)
        bodies = self._find_direct_trees(tree, "body")
        if not bodies:
            raise AlgoCError("if statement without a body")

        then_body = self._body(bodies[0])
        elifs = [self._elif_clause(t) for t in self._find_direct_trees(tree, "elif_clause")]
        else_tree = self._first_tree(tree, "else_clause")
        else_body = self._else_clause(else_tree) if else_tree else None
        return IfNode(condition=condition, then_body=then_body, elifs=elifs, else_body=else_body)

    def _elif_clause(self, tree: Tree) -> ElifNode:
        condition = self._first_expr_in(tree.children)
        body_tree = self._first_tree(tree, "body")
        return ElifNode(condition=condition, body=self._body(body_tree))

    def _else_clause(self, tree: Tree) -> BodyNode:
        body_tree = self._first_tree(tree, "body")
        return self._body(body_tree)

    def _for_init(self, tree: Tree):
        variable = self._first_token(tree, "ID").value
        start = self._first_expr_after_first_id(tree.children)
        return variable, start

    def _for_final(self, tree: Tree):
        return self._first_expr_in(tree.children)

    def _io_args(self, tree: Optional[Tree]) -> List[IOArgNode]:
        if tree is None:
            return []

        args: List[IOArgNode] = []
        for child in tree.children:
            if self._is_tree(child, "io_arg"):
                dollar = any(isinstance(c, Token) and c.value == "$" for c in child.children)
                expr = self._first_expr_in(child.children)
                args.append(IOArgNode(expr=expr, dollar=dollar))
            elif self._is_expr_item(child):
                args.append(IOArgNode(expr=self._expr(child), dollar=False))
        return args

    # Expressions

    def _expr(self, item: Union[Tree, Token]):
        if isinstance(item, Token):
            return self._token_expr(item)

        name = self._data(item)

        if name == "primary_expr":
            return self._first_expr_in(item.children)

        if name == "array_access":
            return self._array_access(item)

        if name == "func_call":
            return self._func_call(item)

        if name in BINARY_OPS:
            expr_children = [c for c in item.children if self._is_expr_item(c)]
            if len(expr_children) != 2:
                raise AlgoCError(f"Binary operation malformed.")
            return BinaryOpNode(
                op=BINARY_OPS[name],
                left=self._expr(expr_children[0]),
                right=self._expr(expr_children[1]),
            )

        if name in UNARY_OPS:
            expr_children = [c for c in item.children if self._is_expr_item(c)]
            if len(expr_children) != 1:
                raise AlgoCError(f"Unary operation malformed.")
            return UnaryOpNode(op=UNARY_OPS[name], operand=self._expr(expr_children[0]))

        raise AlgoCError(f"Expression {name} not recognized.")

    def _token_expr(self, token: Token):
        if token.type == "ID":
            return IdentifierNode(token.value)
        if token.type == "INT_CONST":
            return IntConstNode(int(token.value))
        if token.type == "REAL_CONST":
            return RealConstNode(float(token.value))
        if token.type == "CHAR_CONST":
            return CharConstNode(token.value)
        if token.type == "STRING_CONST":
            return StringConstNode(token.value)
        if token.type == "TRUE":
            return BooleanConstNode(True)
        if token.type == "FALSE":
            return BooleanConstNode(False)
        raise AlgoCError(f"Token {token} not recognized as an expression.")

    def _func_call(self, tree: Tree) -> CallNode:
        name = self._first_token(tree, "ID").value
        exprs_tree = self._first_tree(tree, "exprs")
        args = []
        if exprs_tree is not None:
            args = [self._expr(c) for c in exprs_tree.children if self._is_expr_item(c)]
        return CallNode(name=name, args=args)

    # Utilities

    def _data(self, tree: Tree) -> str:
        return str(tree.data)
    
    def _is_tree(self, item, name: Optional[str] = None) -> bool:
        if not isinstance(item, Tree):
            return False
        return name is None or self._data(item) == name

    def _is_expr_item(self, item) -> bool:
        if isinstance(item, Token):
            return item.type in EXPR_TOKEN_TYPES
        if isinstance(item, Tree):
            return self._data(item) in EXPR_RULES
        return False

    def _first_tree(self, tree: Tree, name: Optional[str] = None) -> Optional[Tree]:
        for child in tree.children:
            if self._is_tree(child, name):
                return child
        return None

    def _first_token(self, tree: Tree, token_type: Optional[str] = None) -> Optional[Token]:
        for child in tree.children:
            if isinstance(child, Token) and (token_type is None or child.type == token_type):
                return child
        return None

    def _find_direct_trees(self, tree: Tree, name: str) -> List[Tree]:
        return [child for child in tree.children if self._is_tree(child, name)]

    def _find_trees(self, tree: Tree, name: str) -> List[Tree]:
        result = []
        for child in tree.children:
            if self._is_tree(child, name):
                result.append(child)
            if isinstance(child, Tree):
                result.extend(self._find_trees(child, name))
        return result

    def _first_expr_in(self, items) -> object:
        for child in items:
            if self._is_expr_item(child):
                return self._expr(child)
        raise AlgoCError("Expression is missing.")

    def _first_expr_after(self, items, previous_item) -> object:
        found = previous_item is None
        for child in items:
            if child is previous_item:
                found = True
                continue
            if found and self._is_expr_item(child):
                return self._expr(child)
        raise AlgoCError("Expression is missing.")

    def _first_expr_after_first_id(self, items) -> object:
        found_first_id = False
        for child in items:
            if isinstance(child, Token) and child.type == "ID" and not found_first_id:
                found_first_id = True
                continue
            if found_first_id and self._is_expr_item(child):
                return self._expr(child)
        raise AlgoCError("Expression is missing.")
