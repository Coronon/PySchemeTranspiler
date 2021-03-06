# PySchemeTranspiler, Transpile simple Python to Scheme(Racket)
# Copyright (C) 2020  Rubin Raithel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations
from typing import Dict, List, Tuple, Union, Callable, Any

from ast import (
    AST,
    FunctionDef,
    Constant,
    Return,
    BinOp,
    Add,
    Sub,
    Mult,
    Div,
    Name,
    Assign,
    UnaryOp,
    UAdd,
    USub,
    Not,
    Expr,
    Call,
    keyword,
    If,
    Compare,
    BoolOp,
    Or,
    And,
    Eq,
    NotEq,
    Lt,
    LtE,
    Gt,
    GtE,
    Subscript,
    List,
    AnnAssign,
    Index,
    Slice,
    Attribute,
    For,
    ImportFrom,
    arg
    )

from .exceptions import throw, warn

IGNORED_IMPORTS = ["typing"]
NUMBER_TYPES = [int, float]
SEPERATOR = '\n'

class TempState():
    def __init__(self, key: str, tempVal: str) -> None:
        """Create a temporary change in the current state within the current scope

        Arguments:
            key     {str} -- Key of temporary change
            tempVal {str} -- Value of temporary change
        """
        self.key = key
        self.oldExists = Builder.inStateLocal(key)
        if self.oldExists:
            self.oldVal = Builder.getStateKeyLocal(key)
        
        Builder.setStateKey(key, tempVal)
    
    def __enter__(self) -> None:
        return
    
    def __exit__(self, type: type, value: Any, traceback: Any) -> bool:
        if self.oldExists:
            Builder.setStateKey(self.key, self.oldVal)
        else:
            Builder.removeStateKeyLocal(self.key)
        
        return False

class _Builder():
       
    @staticmethod
    def error(node: AST) -> str:
        raise ValueError(f"Node of type '{type(node)}' is not fully supported")
    
    @staticmethod
    def FunctionDef(node: FunctionDef) -> str:
        Builder.widenState()
        #* Name
        name = node.name
        #* Arguments
        args = ""
        argTypesDef = []
        argTypesKey = {}
        
        setStateQueue: List[Tuple[str, type]] = []
        
        argsLen     = len(node.args.args)
        defaultsLen = len(node.args.defaults)
        for i in range(argsLen):
            if args != "": args += " "
            
            if (default := -(argsLen-defaultsLen-i)) >= 0:
                #? Argument with default
                argV, argT = Builder.buildFromNodeType(node.args.defaults[default])
                args += f"#:{node.args.args[i].arg} [{node.args.args[i].arg} {argV}]"
                
                aType = Typer.deduceTypeFromNode(node.args.args[i])
                if not Typer.isTypeCompatible(aType, argT):
                    raise TypeError(
                        f"annotaion type {aType} and default type {argT} are incompatible for argument '{node.args.args[i].arg}' of {name}"
                        )
                
                argTypesKey[node.args.args[i].arg] = aType
                setStateQueue.append((node.args.args[i].arg, aType))
            else:
                #? Normal argument
                args += node.args.args[i].arg
                
                aType = Typer.deduceTypeFromNode(node.args.args[i])
                argTypesDef.append(aType)
                setStateQueue.append((node.args.args[i].arg, aType))
        
        #? Check for vararg
        varArgFlag = False
        if node.args.vararg is not None:
            varArgFlag = True
            args += f" . {node.args.vararg.arg}"
        
        #* Add self to state
        retType = Typer.deduceTypeFromNode(node.returns)
        Builder.setStateKeyPropagate(name, Typer.TFunction(argTypesDef, argTypesKey, varArgFlag, retType))
        
        for t in setStateQueue:
            Builder.setStateKey(*t)
        
        #* Body
        with TempState('__returnType__', retType):
            with TempState('__didReturn__', False):
                body = ""
                for i in node.body:
                    body += Builder.buildFromNode(i)
                
                if not Builder.getStateKeyLocal('__didReturn__'):
                    raise ValueError("Please ensure your function returns at least 'None' on every path")
            
        Builder.popState()
        return f'(define ({name} {args}) {body})'

    @staticmethod
    def Constant(node: Constant) -> Tuple[str]:
        value = node.value
        ret = None
        
        if isinstance(value, str):
            ret = f'"{value}"', str
        #? This has to be before int as bool is a subclass of int
        elif isinstance(value, bool):
            boolSwitcher: Dict[bool, str] = {
                True  : "#t",
                False : "#f"
            }
            ret = boolSwitcher[value], bool
        elif isinstance(value, int):
            ret = str(value), int
        elif isinstance(value, float):
            ret = str(value), float
        elif value is None:
            #? We use a symbol as it is compiled into a staic pointer in the binary
            ret = "'NoneType", None
        else:
            _Builder.error(node)
        
        #? Check if we should resolve as a literal if
        if Builder.getStateKeyLocal('__resolveAsIf__'):
            return IfLiteralResolver.resolve(*ret)
        
        return ret
    
    @staticmethod
    def Return(node: Return) -> str:
        value, vType = Builder.buildFromNodeType(node.value)
        if not Typer.isTypeCompatible(vType, (sType := Builder.getStateKeyLocal('__returnType__'))):
            raise TypeError(f"Type {sType} and {vType} are incompatible for return value")
        
        Builder.setStateKey('__didReturn__', True)
        return value
    
    @staticmethod
    def BinOp(node: BinOp) -> Tuple[str, Any]:
        def flattenNumberBinOp(operation: str) -> str:
            ops = ['+', '-', '*', '/']
            for op in ops:
                i = 0
                while True:
                    i = operation.find(op, i)
                    if i != -1 and operation[i+3] == op:
                        closer = operation.find(')', i)
                        operation = operation[:i-1]+operation[i+2:closer]+operation[closer+1:]
                        i = 0
                    else:
                        break
            
            return operation
        def flattenSubString(operation: str, sub: str):
            l = len(sub)
            i = 0
            while True:
                i = operation.find(sub, i)
                if i != -1 and operation[i+15:i+2*l+2] == sub:
                    closer = operation.find(')', i)
                    operation = operation[:i-1]+operation[i+l+1:closer]+operation[closer+1:]
                    i = 0
                else:
                    break
            return operation
        
        lValue, lType = Builder.buildFromNodeType(node.left)
        rValue, rType = Builder.buildFromNodeType(node.right)
        
        if lType in NUMBER_TYPES and rType in NUMBER_TYPES:
            return flattenNumberBinOp(f"({Builder.buildFromNode(node.op)} {lValue} {rValue})"), int if lType == int and rType == int else float
        elif lType == str and rType == str:
            if (operant := Builder.buildFromNode(node.op)) != '+':
                raise TypeError(f"unsupported operand type(s) for {operant}: '{lType}' and '{rType}'")
            return flattenSubString(f"(string-append {lValue} {rValue})", 'string-append'), str

        raise TypeError(f"unsupported operand type(s) for {Builder.buildFromNode(node.op)}: '{lType}' and '{rType}'")
    
    @staticmethod
    def Add(node: Add) -> str:
        return "+"

    @staticmethod
    def Sub(node: Sub) -> str:
        return "-"
    
    @staticmethod
    def Mult(node: Mult) -> str:
        return "*"
    
    @staticmethod
    def Div(node: Div) -> str:
        return "/"
    
    @staticmethod
    def Name(node: Name) -> Tuple[str, type]:
        ret = node.id, Builder.getStateKey(node.id)
        
        #? Check if we should resolve as a literal if
        if Builder.getStateKeyLocal('__resolveAsIf__'):
            return IfLiteralResolver.resolve(*ret)
        
        return ret
    
    @staticmethod
    def Assign(node: Assign) -> str:
        ret = ""
        value, vType = Builder.buildFromNodeType(node.value)
        
        for target in node.targets:
            
            if isinstance(target, Subscript):
                name, nType = Builder.buildFromNodeType(target.value)
        
                class AssignSubscriptResolver():
                    @staticmethod
                    def error(name: str, nType: type, slice: Any):
                        raise TypeError(f"value of type {nType} can not be subscripted")
                    
                    @staticmethod
                    def TList(name: str, nType: type, slice: Union[Index, Slice]) -> str:
                        if isinstance(slice, Index):
                            index = Builder.buildFromNode(slice)
                            try:
                                index, indexT = Builder.buildFromNodeType(slice)
                                
                                if indexT is int and isinstance(index, int):
                                    if index < 0:
                                        index = f"(- (gvector-count {name}) {-index})"
                                elif indexT is int and isinstance(index, str):
                                    index = f"(if (< {index} 0) (- (gvector-count {name}) (- {index})) {index})"
                                else:
                                    raise ValueError()
                        
                            except ValueError:
                                raise TypeError(f"instance of type {type(index)} can not be used to index into a list")
                            
                            if not Typer.isTypeCompatible(vType, nType.contained):
                                raise TypeError(f"element of type {vType} can not be appended to list containing type {nType.contained}")
                            
                            return f"(safe-gvector-set! {name} {index} {value})"
                        elif isinstance(slice, Slice):
                            raise NotImplementedError("Advanced slicing is not yet implemented for lists")
                        else:
                            raise TypeError(f"type {type(slice)} can not be used to slice a list")
                
                types: Dict[str, Callable[[Call], str]] = {
                    Typer.TList: AssignSubscriptResolver.TList
                }
                
                return types.get(type(nType), AssignSubscriptResolver.error)(name, nType, target.slice)
            else:
                if Builder.inStateLocal(target.id):
                    if Builder.config['TYPES_STRICT']:
                        #? Strict mode
                        #? Allow automatic conversion between compatible types that dont cause data loss
                        sType = Builder.getStateKeyLocal(target.id)
                        if not Typer.isTypeCompatible(vType, sType):
                            raise TypeError(f"Type {sType} and {vType} are incompatible for '{target.id}'")
                        
                        if sType is None and vType is not None:
                            if Builder.getStateKeyLocal('__definitionsClaim__'):
                                warn("TypeWarning", "Can not assure type correctness for retyped variable in a control structure", Builder.currentNode)
                            
                            #? We merge the types here to avoid int->float->int shenanigans
                            Builder.setStateKey(target.id, Typer.mergeTypes(sType, vType))
                    else:
                        #? Unstrict mode
                        Builder.setStateKey(target.id, vType)
                        
                    ret += f"(set! {target.id} {value})"
                else:
                    if Typer.isRestrictedType(vType):
                        raise TypeError(f"restricted type {vType} may only be used in an annotated assign")
                    
                    Builder.setStateKey(target.id, vType)
                    if Builder.getStateKeyLocal('__assignSkipValue__'):
                        #? Some component doesnt want us to include the value
                        ret += f"(define {target.id} void)"
                    else:
                        ret += f"(define {target.id} {value})"
        
        return ret
    
    @staticmethod
    def UnaryOp(node: UnaryOp) -> Tuple[str, type]:
        ret = None
        
        with TempState('__resolveAsIf__', False):
            value, vType = Builder.buildFromNodeType(node.operand)
        
        if vType in NUMBER_TYPES:
            if Builder.buildFromNode(node.op) == "+":
                ret = value, vType
            elif Builder.buildFromNode(node.op) == "-":
                if isinstance(node.operand, Constant):
                    ret = f"-{value}", vType
                else:
                    ret = f"(- {value})", vType
        elif vType == bool:
            if Builder.buildFromNode(node.op) == "not":
                ret = f"(not {value})", vType
            
        
        #? Check if we should resolve as a literal if
        if Builder.getStateKeyLocal('__resolveAsIf__'):
            if ret is not None:
                return IfLiteralResolver.resolve(*ret)
            elif Builder.buildFromNode(node.op) == "not":
                return f"(not {IfLiteralResolver.resolve(value, vType)[0]})"
        
        if ret is None:
            raise TypeError(f"unaryOperation '{node.op}' can not be applied to type {vType}'")
        
        return ret
    
    @staticmethod
    def UAdd(node: UAdd) -> str:
        return "+"
    
    @staticmethod
    def USub(node: USub) -> str:
        return "-"
    
    @staticmethod
    def Not(node: Not) -> str:
        return "not"
    
    @staticmethod
    def Expr(node: Expr) -> Tuple[str, type]:
        return Builder.buildFromNodeType(node.value)
    
    @staticmethod
    def Call(node: Call) -> Tuple[str, type]:
        class CallResolver():
            #* FUNCTIONS
            @staticmethod
            def normal(node: Call) -> Tuple[str, type]:
                #* Type lookup
                fName = Builder.buildFromNode(node.func)
                fType: Typer.TFunction = Builder.getStateKey(fName)
                
                #? Check argument length matches
                fArgsDef = len(fType.args)
                fArgsKey = len(fType.kwArgs)
                fArgs    = fArgsDef + fArgsKey
                nArgsDef = len(node.args)
                nArgsKey = len(node.keywords)
                nArgs = nArgsDef + nArgsKey
                if (fType.vararg and nArgsDef < fArgsDef) or (not fType.vararg and fArgsDef != nArgsDef):
                    raise TypeError(f"{fName} takes {fArgsDef} positional arguments but you provided {nArgs}")
                
                if not (nArgsKey <= fArgsKey):
                    raise TypeError(f"{fName} takes {fArgsKey} keyword arguments but you provided {nArgsKey}")
                
                #* Parse arguments
                #? Default args
                argListDef: List[Tuple[str, type]] = []
                for arg in node.args:
                    argListDef.append(Builder.buildFromNodeType(arg))
                
                # Check default argument types match
                args = ""
                for i in range(len(fType.args)):
                    if not Typer.isTypeCompatible(argListDef[i][1], fType.args[i]):
                        raise TypeError(f"type {argListDef[i][1]} can not be applied to argument of type {fType.args[i]}")
                
                for arg in argListDef:
                    if args != "": args += " "
                    args += arg[0]
                
                #? Keyword args
                def getKeywordName(argument: str) -> str:
                    return argument.split(" ")[0][2:]
                
                #Tuple[kwName, kwCode, kwType]
                argListKey: List[Tuple[str, str, type]] = []
                for arg in node.keywords:
                    value, vType = Builder.buildFromNodeType(arg)
                    argListKey.append((getKeywordName(value), value, vType))
                
                # Check keyword argument types match
                for i in argListKey:
                    if i[0] not in fType.kwArgs:
                        raise TypeError(f"'{i[0]}' is an invalid keyword argument for {fName}")
                    if not Typer.isTypeCompatible(i[2], fType.kwArgs[i[0]]):
                        raise TypeError(f"type {i[2]} can not be applied to argument of type {fType.kwArgs[i[0]]}")
                    if args != "": args += " "
                    args += i[1]
                
                if args == "":
                    return f"({fName})", fType.ret
                    
                return f"({fName} {args})", fType.ret
            
            @staticmethod
            def print(node: Call) -> Tuple[str, type]:
                Builder.buildFlags['PRINT'] = True
                node.func.id = "PRINT"
                return CallResolver.normal(node)
            
            @staticmethod
            def range(node: Call) -> Tuple[str, type]:
                #? This func is set to accept varArgs for easier build in typing -> Check args
                if not 0 < len(node.args) < 4:
                    raise TypeError(f"builtin range takes 1 to 3 arguments, {len(node.args)} provided")
                elif any([not Typer.isTypeCompatible(Typer.deduceTypeFromNode(x), int) for x in node.args]):
                    raise TypeError(f"builtin range takes 1 to 3 integers")
                return CallResolver.normal(node)

            @staticmethod
            def input(node: Call) -> Tuple[str, type]:
                Builder.buildFlags['INPUT'] = True
                
                if not len(node.args) < 2:
                    raise TypeError(f"builtin input takes 0 to 1 arguments, {len(node.args)} provided")
                elif any([not Typer.isTypeCompatible(Typer.deduceTypeFromNode(x), str) for x in node.args]):
                    raise TypeError(f"builtin input takes 0 to 1 strings")
                
                if not node.args:
                    node.args.append(Constant(value="", kind=None))
                
                return CallResolver.normal(node)
    
            @staticmethod
            def len(node: Call) -> Tuple[str, type]:
                class lenResolver():
                    @staticmethod
                    def error(value: str, vType: type) -> str:
                        raise TypeError(f"object of type '{vType}' has no len()")
                    
                    @staticmethod
                    def str(value: str, vType: type) -> str:
                        return f"(string-length {value})"
                    
                    @staticmethod
                    def TList(value: str, vType: type) -> str:
                        return f"(gvector-count {value})"
                
                
                if not (lArgs := len(node.args)) == 1:
                    raise TypeError(f"builtin len takes 1 argument, {lArgs} provided")
                
                value, vType = Builder.buildFromNodeType(node.args[0])
                
                if isinstance(vType, Typer.T):
                    vType = type(vType)
                
                switcher: Dict[type, Callable[[str, type], str]] = {
                    str         : lenResolver.str,
                    Typer.TList : lenResolver.TList
                }
                
                return switcher.get(vType, lenResolver.error)(value, vType), int
                
            #* ATTRIBUTES

            @staticmethod
            def TList(node: Call, name: str, nType: Typer.TList, attr: str) -> Tuple[str, type]:
                def error(node: Call, name: str, nType: Typer.TList):
                    raise AttributeError(f"no such attribute function on type list")
                
                def append(node: Call, name: str, nType: Typer.TList) -> Tuple[str, type]:
                    if not (args := len(node.args)) == 1:
                        raise ValueError(f"append on list takes 1 type-compatible argument, {args} provided")
                    
                    value, vType = Builder.buildFromNodeType(node.args[0])
                    if not Typer.isTypeCompatible(vType, nType.contained):
                        raise TypeError(f"element of type {vType} can not be appended to list containing type {nType.contained}")
                    
                    return f"(gvector-add! {name} {value})", Typer.Null()
                
                def pop(node: Call, name: str, nType: Typer.TList) -> Tuple[str, type]:
                    if not (args := len(node.args)) == 1:
                        raise ValueError(f"pop on list takes 1 positional argument, {args} provided")
                    
                    try:
                        index, indexT = Builder.buildFromNodeType(node.args[0])
                        
                        if indexT is int and isinstance(index, int):
                            if index < 0:
                                index = f"(- (gvector-count {name}) {-index})"
                        elif indexT is int and isinstance(index, str):
                            index = f"(if (< {index} 0) (- (gvector-count {name}) (- {index})) {index})"
                        else:
                            raise ValueError()
                        
                    except ValueError:
                        raise TypeError(f"instance of type {type(index)} can not be used to index into a list")
                    
                    return f"(gvector-pop! {name} {index})", nType.contained
                
                def insert(node: Call, name: str, nType: Typer.TList) -> Tuple[str, type]:
                    if not (args := len(node.args)) == 2:
                        raise ValueError(f"insert on list takes 2 positional arguments, {args} provided")
                    
                    try:
                        index, indexT = Builder.buildFromNodeType(node.args[0])
                        
                        if indexT is int and isinstance(index, int):
                            if index < 0:
                                index = f"(- (gvector-count {name}) {-index})"
                        elif indexT is int and isinstance(index, str):
                            index = f"(if (< {index} 0) (- (gvector-count {name}) (- {index})) {index})"
                        else:
                            raise ValueError()
                        
                    except ValueError:
                        raise TypeError(f"instance of type {type(index)} can not be used to index into a list")
                    
                    
                    value, vType = Builder.buildFromNodeType(node.args[1])
                    if not Typer.isTypeCompatible(vType, nType.contained):
                        raise TypeError(f"element of type {vType} can not be inserted into a list containing type {nType.contained}")
                    
                    return f"(gvector-insert! {name} {index} {value})", Typer.Null()
                
                # def count(node: Call, name: str, nType: Typer.TList) -> Tuple[str, type]:
                #     if not (args := len(node.args)) == 0:
                #         raise ValueError(f"count on list takes no positional argument, {args} provided")
                    
                #     return f"(gvector-count {name})", int
                
                attributes: Dict[str, Callable[[Call], Tuple[str, type]]] = {
                    'append' : append,
                    'pop'    : pop,
                    'insert' : insert,
                    # 'count'  : count
                }
                
                return attributes.get(attr, error)(node, name, nType)

            #* TYPE-CONVERTERS
            
            # 'int'   : Typer.TFunction([Typer.TUnion([int, float, str, bool])],       kwArgs=[], vararg=False, ret=int),
            # 'float' : Typer.TFunction([Typer.TUnion([float, int, str, bool])],         kwArgs=[], vararg=False, ret=float),
            # 'str'   : Typer.TFunction([Typer.TUnion([str, int, float, bool])], kwArgs=[], vararg=False, ret=str),
            # 'bool'  : Typer.TFunction([Typer.TUnion([bool, int, float, str])],  kwArgs=[], vararg=False, ret=bool)
            
            @staticmethod
            def int(node: Call) -> Tuple[str, type]:
                Builder.buildFlags['TO_INT'] = True
                accepted = [float, str, bool]
                if not (lArgs := len(node.args)) == 1:
                    raise TypeError(f"builtin typeConverter int takes 1 arguments, {lArgs} provided")
                
                argV, argT = Builder.buildFromNodeType(node.args[0])
                if argT not in accepted:
                    raise TypeError(f"builtin typeConverter int takes {accepted}, {argT} provided")
                
                return f"(int {argV})", int

            @staticmethod
            def float(node: Call) -> Tuple[str, type]:
                Builder.buildFlags['TO_FLOAT'] = True
                accepted = [float, int, str, bool]
                if not (lArgs := len(node.args)) == 1:
                    raise TypeError(f"builtin typeConverter float takes 1 arguments, {lArgs} provided")
                
                argV, argT = Builder.buildFromNodeType(node.args[0])
                if argT not in accepted:
                    raise TypeError(f"builtin typeConverter float takes {accepted}, {argT} provided")
                
                return f"(float {argV})", float
            
            @staticmethod
            def str(node: Call) -> Tuple[str, type]:
                Builder.buildFlags['TO_STR'] = True
                accepted = [str, int, float, bool]
                if not (lArgs := len(node.args)) == 1:
                    raise TypeError(f"builtin typeConverter str takes 1 arguments, {lArgs} provided")
                
                argV, argT = Builder.buildFromNodeType(node.args[0])
                if argT not in accepted:
                    raise TypeError(f"builtin typeConverter str takes {accepted}, {argT} provided")
                
                return f"(str {argV})", str
            
            @staticmethod
            def bool(node: Call) -> Tuple[str, type]:
                Builder.buildFlags['TO_BOOL'] = True
                accepted = [bool, int, float, str]
                if not (lArgs := len(node.args)) == 1:
                    raise TypeError(f"builtin typeConverter bool takes 1 arguments, {lArgs} provided")
                
                argV, argT = Builder.buildFromNodeType(node.args[0])
                if argT not in accepted:
                    raise TypeError(f"builtin typeConverter bool takes {accepted}, {argT} provided")
                
                return f"(bool {argV})", bool
        
        ret = None
        with TempState('__resolveAsIf__', False):
            if not isinstance(node.func, Attribute):
                #? Normal call
                specials: Dict[str, Callable[[Call], Tuple[str, type]]] = {
                    'print' : CallResolver.print,
                    'range' : CallResolver.range,
                    'input' : CallResolver.input,
                    'len'   : CallResolver.len,
                    'int'   : CallResolver.int,
                    'float' : CallResolver.float,
                    'str'   : CallResolver.str,
                    'bool'  : CallResolver.bool,
                }
                
                ret = specials.get(Builder.buildFromNode(node.func), CallResolver.normal)(node)
            else:
                #? Attributes
                def error(node: Call, name: str, nType: type, attr: str):
                    raise TypeError(f"object of type {nType} does not have any attribute functions")
                
                def fetchInfoFromAttribute(node: Attribute) -> Tuple[str, type, str]:
                    """Get basic info from Attribute

                    Arguments:
                        node {Attribute} -- Attribute to analyze

                    Returns:
                        Tuple[str, type, str] -- VariableName, VariableType, AttributeCallName
                    """
                    if not isinstance(node.value, Name):
                        raise TypeError(f"node of type {type(node.value)} may not use attributes")
                    
                    name, nType = Builder.buildFromNodeType(node.value)
                    return name, nType, node.attr

                name, nType, attr = fetchInfoFromAttribute(node.func)
                
                types: Dict[str, Callable[[Call], Tuple[str, type]]] = {
                    Typer.TList: CallResolver.TList,
                }
                
                ret = types.get(type(nType), error)(node, name, nType, attr)
        
        #? Check if we should resolve as a literal if
        if Builder.getStateKeyLocal('__resolveAsIf__'):
            return IfLiteralResolver.resolve(*ret)
        
        return ret
            
    @staticmethod
    def keyword(node: Keyword) -> Tuple[str, type]:
        value, vType = Builder.buildFromNodeType(node.value)
        return f"#:{node.arg} {value}", vType

    @staticmethod
    def If(node: If) -> str:
        def handleAssign(node: Assign) -> str:
            with TempState('__assignSkipValue__', True):
                possibleDefine = Builder.buildFromNode(node)
            if not (len(possibleDefine) >= 5 and possibleDefine[:5] == "(set!") and not (len(possibleDefine) >= 18 and possibleDefine[:18] == "(safe-gvector-set!"):
                Builder.setStateKey(
                    '__definitions__',
                    [*Builder.getStateKeyLocal('__definitions__'), possibleDefine]
                    )
                return Builder.buildFromNode(node)
            
            return possibleDefine
        
        paths: List[str] = []
        body = ""
        
        #* Check if hierarchy
        rootDef = False
        #? Try to aquire root(if/loop) claim
        if not Builder.getStateKeyLocal('__definitionsClaim__'):
            rootDef = True
            Builder.setStateKey('__definitionsClaim__', True)
        
        with TempState('__innerBody__', True):
            for elem in node.body:
                #? Move possible definitions before rootDef in current scope
                if isinstance(elem, Assign) or isinstance(elem, AnnAssign):
                    body += handleAssign(elem)
                    continue
                
                body += Builder.buildFromNode(elem)
        
        if len(body) == 0:
            raise IndentationError("expected an indented block")
        
        with TempState('__resolveAsIf__', True):
            paths.append(f"({Builder.buildFromNode(node.test)} {body})")
        
        if node.orelse:
            if isinstance(node.orelse[0], If):
                with TempState('__innerBody__', False):
                    paths.append(Builder.buildFromNode(node.orelse[0]))
            else:
                body = ""
                with TempState('__innerBody__', True):
                    for elem in node.orelse:
                        #? Move possible definitions before rootDef in current scope
                        if isinstance(elem, Assign) or isinstance(elem, AnnAssign):
                            body += handleAssign(elem)
                            continue
                        
                        body += Builder.buildFromNode(elem)
                paths.append(f"(else {body})")
                
        
        if not rootDef:
            if not Builder.getStateKey('__innerBody__'):
                return SEPERATOR.join(paths)
            else:
                return f"(cond {' '.join(paths)})"
        else:
            Builder.setStateKey('__if__', False)
            
            defs = Builder.getStateKeyLocal('__definitions__')
            Builder.setStateKey('__definitions__', [])
            Builder.setStateKey('__definitionsClaim__', False)
            
            return f"{SEPERATOR.join(defs)}{SEPERATOR if len(defs) > 0 else ''}(cond {' '.join(paths)})"
    
    @staticmethod
    def Compare(node: Compare) -> Tuple[str, type]:
        with TempState('__resolveAsIf__', False):
            def determineOp(op: str, type1: type, type2: type) -> str:
                if op in ["==", "!="]: return op
                
                #? Numbers
                if type1 in NUMBER_TYPES and type2 in NUMBER_TYPES:
                    return op
                #? Strings
                if type1 == str and type2 == str:
                    return f"string{op}?"
                
                raise TypeError(f"can not compare instances of types {type1} and {type2}")
            
            fLeftV, fLeftT   = Builder.buildFromNodeType(node.left)
            fRightV, fRightT = Builder.buildFromNodeType(node.comparators[0])
            fOp = determineOp(Builder.buildFromNode(node.ops[0]), fLeftT, fRightT)
            ret = f"({fOp} {fLeftV} {fRightV})"
            if len(node.ops) == 1:
                return ret, bool

            #? Statements like: a < b > c < d -> a < b && b > c && c < d
            # We compile them into a flattend and
            for i in range(1, len(node.ops)):
                leftE, rightE, opE = node.comparators[i-1], node.comparators[i], Builder.buildFromNode(node.ops[i])
                leftV, leftT   = Builder.buildFromNodeType(leftE)
                rightV, rightT = Builder.buildFromNodeType(rightE)
                op = determineOp(opE, leftT, rightT)
                ret += f"({op} {leftV} {rightV})"
                
        ret = f"(and {ret})"
        return ret, bool
        
    @staticmethod
    def BoolOp(node: BoolOp) -> Tuple[str, type]:
        return f"({Builder.buildFromNode(node.op)} {' '.join([Builder.buildFromNode(x) for x in node.values])})", bool
        
    @staticmethod
    def Or(node: Or) -> Tuple[str, type]:
        return "or", bool

    @staticmethod
    def And(node: And) -> Tuple[str, type]:
        return "and", bool
    
    @staticmethod
    def Eq(node: Eq) -> str:
        Builder.buildFlags['EQUAL'] = True
        return "=="

    @staticmethod
    def NotEq(node: NotEq) -> str:
        Builder.buildFlags['NOT_EQUAL'] = True
        return "!="
    
    @staticmethod
    def Lt(node: Lt) -> str:
        return "<"
    
    @staticmethod
    def LtE(node: LtE) -> str:
        return "<="
    
    @staticmethod
    def Gt(node: Gt) -> str:
        return ">"
    
    @staticmethod
    def GtE(node: GtE) -> str:
        return ">="

    @staticmethod
    def List(node: List) -> Tuple[str, type]:
        Builder.buildFlags['GROWABLE_VECTOR'] = True
        
        ret = None
        
        containingT = Typer.TPending()
        elements = []
        
        with TempState('__resolveAsIf__', False):
            for entry in node.elts:
                value, vType = Builder.buildFromNodeType(entry)
                elements.append(value)
                containingT = Typer.mergeTypes(containingT, vType)

            if not elements:
                ret = "(gvector)", Typer.TList(containingT)
            else:
                ret = f"(gvector {' '.join(elements)})", Typer.TList(containingT)
        
        #? Check if we should resolve as a literal if
        if Builder.getStateKeyLocal('__resolveAsIf__'):
            return IfLiteralResolver.resolve(*ret)
        
        return ret
    
    @staticmethod
    def AnnAssign(node: AnnAssign) -> str:
        name = node.target.id
        
        if not node.value:
            raise ValueError(f"variable '{name}' must be initialized")
        
        value, vType = Builder.buildFromNodeType(node.value)
        aType = Typer.deduceTypeFromNode(node)
        if not Typer.isTypeCompatible(vType, aType):
            raise TypeError(f"can not assign value of type {vType} to variable with type annotation of {aType}")
        
        if Builder.inStateLocal(name):
            if Builder.config['TYPES_STRICT']:
                #? Strict mode
                raise TypeError(f"Can not redefine variable type")
            else:
                #? Unstrict mode
                if Builder.getStateKeyLocal('__definitionsClaim__'):
                    warn("TypeWarning", "Can not assure type correctness for retyped variable in a control structure", Builder.currentNode)
                
                Builder.setStateKey(name, aType)
                
            return f"(set! {name} {value})"
        else:
            Builder.setStateKey(name, aType)
            if Builder.getStateKeyLocal('__assignSkipValue__'):
                #? Some component doesnt want us to include the value
                return f"(define {name} void)"
            else:
                return f"(define {name} {value})"
    
    @staticmethod
    def Subscript(node: Subscript) -> Tuple[str, type]:
        with TempState('__resolveAsIf__', False):
            name, nType = Builder.buildFromNodeType(node.value)
        
        class SubscriptResolver():
            @staticmethod
            def error(name: str, nType: type, slice: Any):
                raise TypeError(f"value of type {nType} can not be subscripted")
            
            @staticmethod
            def TList(name: str, nType: type, slice: Union[Index, Slice]) -> Tuple[str, type]:
                if isinstance(slice, Index):
                    try:
                        index, indexT = Builder.buildFromNodeType(slice)
                        
                        if indexT is int and isinstance(index, int):
                            if index < 0:
                                index = f"(- (gvector-count {name}) {-index})"
                        elif indexT is int and isinstance(index, str):
                            index = f"(if (< {index} 0) (- (gvector-count {name}) (- {index})) {index})"
                        else:
                            raise ValueError()
                        
                    except ValueError:
                        raise TypeError(f"instance of type {type(index)} can not be used to index into a list")
                    
                    return f"(gvector-access {name} {index})", nType.contained
                elif isinstance(slice, Slice):
                    raise NotImplementedError("Advanced slicing is not yet implemented for lists")
                else:
                    raise TypeError(f"type {type(slice)} can not be used to slice a list")
        
        types: Dict[str, Callable[[Call], Tuple[str, type]]] = {
            Typer.TList: SubscriptResolver.TList
        }
        
        with TempState('__resolveAsIf__', False):
            ret = types.get(type(nType), SubscriptResolver.error)(name, nType, node.slice)
        
        #? Check if we should resolve as a literal if
        if Builder.getStateKeyLocal('__resolveAsIf__'):
            return IfLiteralResolver.resolve(*ret)
        
        return ret
    
    @staticmethod
    def Index(node: Index) -> Tuple[str, int]:
        if isinstance(node.value, Name) or isinstance(node.value, Constant) or isinstance(node.value, UnaryOp) or isinstance(node.value, BinOp):
            return Builder.buildFromNodeType(node.value)
        else:
            raise TypeError(f"value of type {type(node.value)} can not be used as an index")
    
    #TODO implement advanced slicing
    # @staticmethod
    # def Slice(node: Slice) -> str:          
    #     pass
    
    @staticmethod
    def For(node: For) -> str:
        def handleAssign(node: Assign) -> str:
            with TempState('__assignSkipValue__', True):
                possibleDefine = Builder.buildFromNode(node)
            if not (len(possibleDefine) >= 5 and possibleDefine[:5] == "(set!") and not (len(possibleDefine) >= 18 and possibleDefine[:18] == "(safe-gvector-set!"):
                Builder.setStateKey(
                '__definitions__',
                [*Builder.getStateKeyLocal('__definitions__'), possibleDefine]
                )
                return Builder.buildFromNode(node)
            
            return possibleDefine
        
        #* Handle iter typing
        iterc, itercType = Builder.buildFromNodeType(node.iter)
        if not isinstance(itercType, Typer.Iterable):
            raise TypeError(f"can not iterate over instance of {itercType}")
        
        targetType = itercType.iterType
        if not isinstance(itercType, Typer.TList):
            raise NotImplementedError(f"iterable of type {itercType} is currently not supported in for loops")
        
        if isinstance(itercType, Typer.TList):
            if not itercType.native:
                iterc = f"(gvector->list {iterc})"
        
        #* Determine target
        target = None
        if isinstance(node.target, Name):
            target = node.target.id
            if Builder.inState(target):
                if Builder.config['TYPES_STRICT']:
                    #? Strict mode
                    if not Typer.isTypeCompatible((sType := Builder.getStateKeyLocal(target)), targetType):
                        raise TypeError(f"Type {sType} and {vType} are incompatible")
                else:
                    Builder.setStateKey(target, targetType)
            else:
                Builder.setStateKey(target, targetType)
                Builder.setStateKey(
                    '__definitions__',
                    [*Builder.getStateKeyLocal('__definitions__'), f"(define {target} void)"]
                    )       
        else:
            raise NotImplementedError("multiple targets are currently not supported in for loops")
        
        body = f"(set! {target} __i__)"
        
        #* Check for hierarchy
        rootDef = False
        #? Try to aquire root(if/loop) claim
        if not Builder.getStateKeyLocal('__definitionsClaim__'):
            rootDef = True
            Builder.setStateKey('__definitionsClaim__', True)
        
        with TempState('__innerBody__', True):
            for elem in node.body:
                #? Move possible definitions before rootDef in current scope
                if isinstance(elem, Assign) or isinstance(elem, AnnAssign):
                    body += handleAssign(elem)
                    continue
                
                body += Builder.buildFromNode(elem)
        
        if len(body) == 0:
            raise IndentationError("expected an indented block")
        
        if node.orelse:
            raise NotImplementedError("'else' syntax is not supported in conjunction with for loops")
        
        
        ret = f"(for-each (lambda (__i__) {body}) {iterc})"
        if not rootDef:
                return ret
        else:
            defs = Builder.getStateKeyLocal('__definitions__')
            Builder.setStateKey('__definitions__', [])
            Builder.setStateKey('__definitionsClaim__', False)
            
            return f"{SEPERATOR.join(defs)}{SEPERATOR if len(defs) > 0 else ''}{ret}"
    
    @staticmethod
    def ImportFrom(node: ImportFrom) -> str:
        if not node.module in IGNORED_IMPORTS:
            return _Builder.error(node)
        
        return ""

class Builder():
    Interpreter = Callable[[AST], str]
    switcher: Dict[type, Callable] = {
        FunctionDef : _Builder.FunctionDef,
        Constant    : _Builder.Constant,
        Return      : _Builder.Return,
        BinOp       : _Builder.BinOp,
        Add         : _Builder.Add,
        Sub         : _Builder.Sub,
        Mult        : _Builder.Mult,
        Div         : _Builder.Div,
        Name        : _Builder.Name,
        Assign      : _Builder.Assign,
        UnaryOp     : _Builder.UnaryOp,
        UAdd        : _Builder.UAdd,
        USub        : _Builder.USub,
        Not         : _Builder.Not,
        Expr        : _Builder.Expr,
        Call        : _Builder.Call,
        If          : _Builder.If,
        Compare     : _Builder.Compare,
        BoolOp      : _Builder.BoolOp,
        Or          : _Builder.Or,
        And         : _Builder.And,
        Eq          : _Builder.Eq,
        NotEq       : _Builder.NotEq,
        Lt          : _Builder.Lt,
        LtE         : _Builder.LtE,
        Gt          : _Builder.Gt,
        GtE         : _Builder.GtE,
        List        : _Builder.List,
        AnnAssign   : _Builder.AnnAssign,
        Subscript   : _Builder.Subscript,
        Index       : _Builder.Index,
        For         : _Builder.For,
        ImportFrom  : _Builder.ImportFrom,
        keyword     : _Builder.keyword
    }
    
    buildFlags = {
        'PRINT'           : False, # Include PRINT function
        'EQUAL'           : False, # Include == function
        'NOT_EQUAL'       : False, # Include != function
        'INPUT'           : False, # Include input function
        'GROWABLE_VECTOR' : False, # Include growableVectors (std)
        'TO_INT'          : False, # Include to int converter
        'TO_FLOAT'        : False, # Include to float converter
        'TO_STR'          : False, # Include to str converter
        'TO_BOOL'         : False, # Include to bool converter
    }
    
    config = {
        'TYPES_STRICT' : True,
        'DEBUG'        : False
    }
    
    defaultWidenedState = {}
    
    #? For default state see `Builder.initState()`
    stateHistory: List[Dict[str, Any]] = [{}]
    
    currentNode: AST = None
    
    @staticmethod
    def buildFromNode(node: AST) -> str:
        """Build sourceCode from a AST node

        Arguments:
            node {AST} -- Node to compile

        Returns:
            str -- Compiled sourceCode
        """
        #* Switch of all Nodes supported
        ret = Builder._buildFromNode(node)
        if isinstance(ret, tuple):
            return ret[0]
        
        return ret
    
    @staticmethod
    def buildFromNodeType(node: AST) -> Tuple[str, Any]:
        """Build sourceCode from a AST node with type information

        Arguments:
            node {AST} -- Node to compile

        Returns:
            str -- Compiled sourceCode
            Any -- Type of compiled object (for internal use)
        """
        #* Switch of all Nodes supported
        ret = Builder._buildFromNode(node)
        if isinstance(ret, tuple):
            return ret
        
        return ret, Typer.Null()
    
    @staticmethod
    def _buildFromNode(node: AST) -> Tuple[str, Any]:
        """Internally used to unify error handling `DO NOT USE EXTERNALLY`

        Raises:
            ConversionException -- Exception caught in transpilation
            
        Returns:
            str -- Compiled sourceCode
            Any -- Type of compiled object (for internal use)
        """
        Builder.currentNode = node
        
        if Builder.config['DEBUG']:
            return Builder.switcher.get(type(node), _Builder.error)(node)
        
        try:
            return Builder.switcher.get(type(node), _Builder.error)(node)
        except Exception as e:
            throw(e, node)
    
    @staticmethod
    def initState() -> None:
        """Init the root state to avoid foreward declaration issues
        """
        defaultRootExclusiveState = {
            'bool'  : bool,
            'int'   : int,
            'float' : float,
            'str'   : str,
            'list'  : list,
            'print' : Typer.TFunction([Any], kwArgs=[], vararg=True, ret=None), #? This is a dummy that will be transpiled to 'PRINT'
            'PRINT' : Typer.TFunction([Any], kwArgs=[], vararg=True, ret=None),
            'input' : Typer.TFunction([str], kwArgs=[], vararg=False, ret=str),
            'range' : Typer.TFunction([int], kwArgs=[], vararg=True, ret=Typer.TList(int, native=True)), #? We set this to vararg as we specifically check this case
            'len'   : Typer.TFunction([Typer.TUnion([str, Typer.TList])], kwArgs=[], vararg=False, ret=int)
            #? No primitive types should be shadowed by their corresponding caster functionTypes! This is just help for the developer
            # 'int'   : Typer.TFunction([Typer.TUnion([float, str, bool])],       kwArgs=[], vararg=False, ret=int),
            # 'float' : Typer.TFunction([Typer.TUnion([int, str, bool])],         kwArgs=[], vararg=False, ret=float),
            # 'str'   : Typer.TFunction([Typer.TUnion([int, float, bool, list])], kwArgs=[], vararg=False, ret=str),
            # 'bool'  : Typer.TFunction([Typer.TUnion([int, float, str, list])],  kwArgs=[], vararg=False, ret=bool)
        }
        Builder.defaultWidenedState = {
            '__if__'              : False, #? Flag for transpiler if in an active if statement
            '__innerBody__'       : False, #? Flag for transpiler if currently in an if body
            '__definitionsClaim__': False, #? Flag for transpiler to communicate root(if/loop) lock
            '__definitions__'     : [],    #? Used to store local definitions to make them persistent on lvl of root(if/loop)
            '__assignSkipValue__' : False, #? Flag for transpiler to not include value in assignment
            '__resolveAsIf__'     : False, #? Flag for transpiler to resolve constant and name as their basic testCase
            '__didReturn__'       : False, #? Flag for transpiler to indicate that a function has a return
        }
        
        Builder.setState({**defaultRootExclusiveState, **Builder.defaultWidenedState})
    
    @staticmethod
    def getState() -> Dict[str, Any]:
        """Get the current compilation State

        Returns:
            Dict[str, Any] -- State
        """
        return Builder.stateHistory[-1]
    
    @staticmethod
    def getStateKey(key: str) -> Any:
        """Get a specific element from the nearest scope

        Arguments:
            key {str} -- Key of element to get

        Raises:
            ValueError: Key not found

        Returns:
            Any -- Element found
        """
        for state in reversed(Builder.stateHistory):
            if key in state:
                return state[key]
        raise KeyError(f"key {key} not in state")

    @staticmethod
    def getStateKeyLocal(key: str) -> Any:
        """Get a specific element from the current compilation State

        Arguments:
            key {str} -- Key of element to get

        Raises:
            ValueError: Key not found

        Returns:
            Any -- Element found
        """
        return Builder.stateHistory[-1][key]
    
    @staticmethod
    def inState(key: str) -> bool:
        """Check if a key is present in the nearest scope

        Arguments:
            key {str} -- Key to check

        Returns:
            bool -- Key in State
        """
        for state in reversed(Builder.stateHistory):
            if key in state:
                return True
        return False
    
    @staticmethod
    def inStateLocal(key: str) -> bool:
        """Check if a key is present in current compilation State

        Arguments:
            key {str} -- Key to check

        Returns:
            bool -- Key in State
        """
        return key in Builder.stateHistory[-1]

    @staticmethod
    def widenState() -> None:
        """Widen the compilation State on new scope
        """
        Builder.stateHistory.append(Builder.defaultWidenedState)
    
    @staticmethod
    def popState() -> Dict[str, Any]:
        """Pop the compilation State on scope exit

        Raises:
            ValueError: Trying to pop root State

        Returns:
            Dict[str, Any] -- Poped State
        """
        if len(Builder.stateHistory) == 1:
            raise ValueError("Can not pop root State")
        
        return Builder.stateHistory.pop()
    
    @staticmethod
    def setStateKey(key: str, value: Any) -> None:
        """Set a key in the compilation State in the current scope

        Arguments:
            key   {str} -- Key of element
            value {Any} -- Value of element
        """
        Builder.stateHistory[-1][key] = value
    
    @staticmethod
    def setStateKeyPropagate(key: str, value: Any) -> None:
        """Set a key in the compilation State in the current AND parent scope

        Arguments:
            key   {str} -- Key of element
            value {Any} -- Value of element
        """
        Builder.stateHistory[-1][key] = value
        Builder.stateHistory[-2][key] = value
    
    @staticmethod
    def setState(state: Dict[str, Any]) -> None:
        """Set the whole compilation State of the current scope

        Arguments:
            state {Dict[str, Any]} -- Compilation State
        """
        Builder.stateHistory[-1] = state

    @staticmethod
    def removeStateKeyLocal(key: str) -> None:
        """Remove a key from the current compilation State

        Arguments:
            key {str} -- Key to remove
        """
        del Builder.stateHistory[-1][key]


class _Typer():
    literals: Dict[str, type] = {
        'bool' : bool,
        'int'  : int,
        'float': float,
        'str'  : str,
        'list' : list
    }
    
    @staticmethod
    def error(node: AST) -> None:
        raise TypeError(f"Type of node {node} can not be deduced")
    
    
    @staticmethod
    def _literalName(node: str) -> type:
        return _Typer.literals.get(node, _Typer.error)
    
    @staticmethod
    def Constant(node: Constant) -> type:
        return type(node.value)
    
    @staticmethod
    def Name(node: Name) -> type:
        return Builder.getStateKey(node.id)
        
    @staticmethod
    def arg(node: arg) -> type:
        return _Typer._literalAnnotation(node.annotation)
    
    @staticmethod
    def _literalSubscript(node: Subscript) -> type:
        class LiteralSubscriptResolver():
            @staticmethod
            def error(node: Subscript) -> type:
                raise TypeError(f"subscript-type {node.value.id} is not supported")
            
            @staticmethod
            def normal(node: Subscript) -> type:
                if Builder.inState(node.value.id):
                    if isinstance((listT := Builder.getStateKey(node.value.id)), Typer.TList):
                        return listT.contained
                    
                return _Typer.LiteralSubscriptResolver.error(node)
            
            @staticmethod
            def List(node: Subscript) -> type:
                return Typer.TList(_Typer._literalAnnotation(node.slice.value))
        
        specials: Dict[str, Callable[[Call], type]] = {
            'List': LiteralSubscriptResolver.List,
        }
        
        return specials.get(node.value.id, LiteralSubscriptResolver.normal)(node)

    @staticmethod
    def _literalAnnotation(node: AST) -> type:
        if isinstance(node, Name):
            return _Typer._literalName(node.id)
        elif isinstance(node, Subscript):   
            return _Typer._literalSubscript(node)
        else:
            raise TypeError(f"node of type {type(node)} is not supported for arg annotations")
    
    @staticmethod
    def AnnAssign(node: AnnAssign) -> type:
        return _Typer._literalAnnotation(node.annotation)

    @staticmethod
    def Subscript(node: Subscript) -> type:
        return _Typer._literalSubscript(node)

    @staticmethod
    def Call(node: Call):
        if isinstance(node.func, Name) or isinstance(node.func, Attribute):
            _, rType = Builder.buildFromNodeType(node)
            return rType

        return _Typer.error(node)

    @staticmethod
    def NoneType(node: None) -> type:
        return None

class Typer():
    
    class T():
        def __repr__(self):
            return str(f"<{self.type}: {self.__dict__}>")
        
        def __eq__(self, value: Typer.T):
                return isinstance(value, Typer.T) and self.__dict__ == value.__dict__
    
    class Null(T):
        type = "Null"
        
        def __repr__(self):
            return "NULL"
    
    class Iterable():
        type = "Iterable"
        
        def __init__(self, iterType: type) -> None:
            """BaseClass of all iterables

            Arguments:
                iterType {type} -- Type of objects returned on iteration
            """
            self.iterType = iterType
    
    class TFunction(T):
        type = "TFunction"
        
        def __init__(self, args: List[type], kwArgs: Dict[str, type], vararg: bool, ret: type):
            self.args   = args
            self.kwArgs = kwArgs
            self.vararg = vararg
            self.ret    = ret
    
    class TList(Iterable, T):
        type = "TList"

        def __init__(self, contained: type, native: bool=False):
            super(Typer.TList, self).__init__(contained)
            self.contained = contained
            self.native    = native
        
        def __repr__(self):
            return str(f"<{self.type}: {self.contained}>")
    
    class TUnion(T):
        type = "TUnion"

        def __init__(self, anyOf: List[type]):
            self.anyOf = anyOf
        
        def __repr__(self):
            return str(f"<{self.type}: {self.anyOf}>")
    
    class TOptional(T):
        type = "TOptional"

        def __init__(self, optOf: type):
            self.optOf = optOf
        
        def __repr__(self):
            return str(f"<{self.type}: {self.optOf}>")
    
    class TPending(T):
        type = "TPending"
        
        def __repr__(self):
            return str(f"<{self.type}...>")
    
    switcher: Dict[type, Callable] = {
        Constant   : _Typer.Constant,
        Name       : _Typer.Name,
        AnnAssign  : _Typer.AnnAssign,
        Subscript  : _Typer.Subscript,
        Call       : _Typer.Call,
        type(None) : _Typer.NoneType,
        arg        : _Typer.arg
    }
    
    restricted: List[type] = [list, dict, TList]
    
    @staticmethod
    def deduceTypeFromNode(node: AST) -> type:
        return Typer.switcher.get(type(node), _Typer.error)(node)
    
    @staticmethod
    def isTypeCompatible(type1: type, type2: type) -> bool:
        """Check if two types are compatible

        Arguments:
            type1 {type} -- Type to be applied
            type2 {type} -- Type to be applied to

        Returns:
            bool -- Types are compatible
        """
        #? Types are equal
        if type1 == type2:
            return True
        
        #? One or both types are Any
        if type1 == Any or type2 == Any:
            return True
        
        #? One or both types are None
        if type1 is None:
            warn("TypeWarning", "Can not assure type correctness for None", Builder.currentNode)
            return True
        elif type2 is None:
            return True
        
        #? TUnion
        if isinstance(type1, Typer.TUnion):
            if all([Typer.isTypeCompatible(x, type2) for x in type1.anyOf]):
                return True
            
            return False
        elif isinstance(type2, Typer.TUnion):
            if any([Typer.isTypeCompatible(type1, x) for x in type2.anyOf]):
                return True
            
            return False
        
        #? TOptional
        if isinstance(type1, Typer.TOptional):
            if isinstance(type2, Typer.TOptional) and Typer.isTypeCompatible(type1.optOf, type2.optOf):
                return True
            
            return False
        elif isinstance(type2, Typer.TOptional):
            if Typer.isTypeCompatible(type1, type2.optOf):
                return True
            
            return False
        
        #? TList
        if isinstance(type1, Typer.TList):
            if isinstance(type2, Typer.TList) and Typer.isTypeCompatible(type1.contained, type2.contained):
                return True
            
            return False
        elif isinstance(type2, Typer.TList):
            return False
        
        #? TPending
        if isinstance(type1, Typer.TPending):
            if not isinstance(type2, Typer.TPending):
                return True
            
            return False
        elif isinstance(type2, Typer.TPending):
            if not isinstance(type1, Typer.TPending):
                return True
            
            return False
        
        #? Number types (reject data loss from float->int)
        if type1 == int and type2 == float:
            return True
        
        return False

    @staticmethod
    def isRestrictedType(test: type) -> bool:
        """Check if a type is restricted and can only be assigned in an AnnAssign

        Arguments:
            test {type} -- Type to check

        Returns:
            bool -- Type restricted
        """
        return test in Typer.restricted or type(test) in Typer.restricted
     
    @staticmethod
    def mergeTypes(type1: type, type2: type) -> type:
        """Merge two types into one and avoid data loss

        Arguments:
            type1 {type} -- Left type of the merge (original type)
            type2 {type} -- Right type of the merge (new type)

        Returns:
            type -- Merged type
        """
        if type1 == type2:
            return type1
        
        mergers = [type1, type2]
        if int in mergers and float in mergers:
            return float
        
        if isinstance(type1, Typer.TPending):
            return type2
        
        if type1 is None:
            return type2
        elif type2 is None:
            return type1
        
        raise TypeError(f"can not merge types {type1} and {type2}")


class IfLiteralResolver():
    @staticmethod
    def error(value: str):
        raise TypeError(f"can not use instance '{value}' in a literal if")
    
    @staticmethod
    def bool(value: str) -> Tuple[str, type]:
        return value, bool
    
    @staticmethod
    def int(value: str) -> Tuple[str, type]:
        return f"(!= {value} 0)", bool
    
    @staticmethod
    def float(value: str) -> Tuple[str, type]:
        return f"(!= {value} 0)", bool
    
    @staticmethod
    def str(value: str) -> Tuple[str, type]:
        return f'(!= {value} "")', bool
    
    @staticmethod
    def NoneType(value: str) -> Tuple[str, type]:
        return "#f", bool
    
    @staticmethod
    def TList(value: str) -> Tuple[str, type]:
        return f"(!= (gvector-count {value}) 0)", bool
    
    @staticmethod
    def TFunction(value: str) -> Tuple[str, type]:
        raise TypeError("can not use instance of type TFunction in a literal if")
    
    @staticmethod
    def resolve(value: str, vType: type) -> Tuple[str, type]:
        switcher: Dict[type, Callable] = {
            bool            : IfLiteralResolver.bool,
            int             : IfLiteralResolver.int,
            float           : IfLiteralResolver.float,
            str             : IfLiteralResolver.str,
            None            : IfLiteralResolver.NoneType,
            Typer.TList     : IfLiteralResolver.TList,
            Typer.TFunction : IfLiteralResolver.TFunction,
        }
        
        Builder.buildFromNode(NotEq()) #? Let _Builder.NotEq handle buildFlags to not spread functionality even more
        
        if isinstance(vType, Typer.T):
            return switcher.get(type(vType), IfLiteralResolver.error)(value)
        
        return switcher.get(vType, IfLiteralResolver.error)(value)
