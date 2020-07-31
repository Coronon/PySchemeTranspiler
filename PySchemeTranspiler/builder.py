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
    arg
    )

from .exceptions import throw

NUMBER_TYPES = [int, float]
SEPERATOR = '\n'

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
        body = ""
        for i in node.body:
            body += Builder.buildFromNode(i)
        
        Builder.popState()
        return f'(define ({name} {args}) {body})'

    @staticmethod
    def Constant(node: Constant) -> Tuple[str]:
        value = node.value
        
        if isinstance(value, str):
            return f'"{value}"', str
        #? This has to be before int as bool is a subclass of int
        elif isinstance(value, bool):
            boolSwitcher: Dict[bool, str] = {
                True  : "#t",
                False : "#f"
            }
            return boolSwitcher[value], bool
        elif isinstance(value, int):
            return str(value), int
        elif isinstance(value, float):
            return str(value), float
        else:
            _Builder.error(node)
    
    @staticmethod
    def Return(node: Return) -> str:
        return Builder.buildFromNode(node.value)
    
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
        return node.id, Builder.getStateKey(node.id)
    
    @staticmethod
    def Assign(node: Assign) -> str:
        ret = ""
        for target in node.targets:
            value, vType = Builder.buildFromNodeType(node.value)
            
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
                                index = int(Builder.buildFromNode(slice))
                                
                                if index < 0:
                                    index = f"(- (length r) {-index})"
                                
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
                        if not Typer.isTypeCompatible((sType := Builder.getStateKeyLocal(target.id)), vType):
                            raise TypeError(f"Type {sType} and {vType} are incompatible for '{target.id}'")
                        #? Allow automatic conversion between compatible types that dont cause data loss
                        Builder.setStateKey(target.id, vType)
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
        value, vType = Builder.buildFromNodeType(node.operand)

        if vType not in NUMBER_TYPES:
            raise TypeError(f"unaryOperation '{node.op}' can not be applied to type {vType}'")
        if Builder.buildFromNode(node.op) == "+":
            return value, vType
        elif Builder.buildFromNode(node.op) == "-":
            if isinstance(node.operand, Constant):
                return f"-{value}", vType
            
            return f"(- {value})", vType
        
        raise TypeError(f"unaryOperation '{node.op}' can not be applied to type {vType}'")
    
    @staticmethod
    def UAdd(node: UAdd) -> str:
        return "+"
    
    @staticmethod
    def USub(node: USub) -> str:
        return "-"
    
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

            #* ATTRIBUTES

            @staticmethod
            def TList(node: Call, name: str, nType: Typer.TList, attr: str) -> Tuple[str, type]:
                def error(node: Call, name: str, nType: Typer.TList):
                    raise AttributeError(f"no such attribute function on type list")
                
                def append(node: Call, name: str, nType: Typer.TList) -> Tuple[str, type]:
                    if not 0 < (args := len(node.args)) < 2:
                        raise ValueError(f"append on list takes 1 type-compatible argument, {args} provided")
                    
                    value, vType = Builder.buildFromNodeType(node.args[0])
                    if not Typer.isTypeCompatible(vType, nType.contained):
                        raise TypeError(f"element of type {vType} can not be appended to list containing type {nType.contained}")
                    
                    return f"(gvector-add! {name} {value})"
                
                attributes: Dict[str, Callable[[Call], Tuple[str, type]]] = {
                    'append': append,
                }
                
                return attributes.get(attr, error)(node, name, nType)
        
        if not isinstance(node.func, Attribute):
            specials: Dict[str, Callable[[Call], Tuple[str, type]]] = {
                'print': CallResolver.print,
                'range': CallResolver.range,
                'input': CallResolver.input
            }
            
            return specials.get(Builder.buildFromNode(node.func), CallResolver.normal)(node)
        else:
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
            
            return types.get(type(nType), error)(node, name, nType, attr)
            
    @staticmethod
    def keyword(node: Keyword) -> Tuple[str, type]:
        value, vType = Builder.buildFromNodeType(node.value)
        return f"#:{node.arg} {value}", vType

    @staticmethod
    def If(node: If) -> str:
        def handleAssign(node: Assign) -> str:
            oldState = Builder.getStateKeyLocal('__assignSkipValue__')
            Builder.setStateKey('__assignSkipValue__', True)
            possibleDefine = Builder.buildFromNode(elem)
            Builder.setStateKey('__assignSkipValue__', oldState)
            if possibleDefine[:5] != "(set!":
                Builder.setStateKey(
                '__ifDefinitions__',
                [*Builder.getStateKeyLocal('__ifDefinitions__'), possibleDefine]
                )
                return Builder.buildFromNode(elem)
            
            return possibleDefine
        
        paths: List[str] = []
        body = ""
        
        #* Check if hierarchy
        rootIf = False
        if not Builder.getStateKeyLocal('__if__'):
            #? Root if
            rootIf = True
            Builder.setStateKey('__if__', True)
        
        oldIfBody = Builder.getStateKey('__ifBody__')
        Builder.setStateKey('__ifBody__', True)
        for elem in node.body:
            #? Move possible definitions before rootIf in current scope
            if isinstance(elem, Assign) or isinstance(elem, AnnAssign):
                handleAssign(elem)
            
            body += Builder.buildFromNode(elem)
        Builder.setStateKey('__ifBody__', oldIfBody)
        
        if len(body) == 0:
            raise IndentationError("expected an indented block")
        
        paths.append(f"({Builder.buildFromNode(node.test)} {body})")
        
        if node.orelse:
            if isinstance(node.orelse[0], If):
                oldIfBody = Builder.getStateKey('__ifBody__')
                Builder.setStateKey('__ifBody__', False)
                paths.append(Builder.buildFromNode(node.orelse[0]))
                Builder.setStateKey('__ifBody__', oldIfBody)
            else:
                body = ""
                oldIfBody = Builder.getStateKey('__ifBody__')
                Builder.setStateKey('__ifBody__', True)
                for elem in node.orelse:
                    #? Move possible definitions before rootIf in current scope
                    if isinstance(elem, Assign) or isinstance(elem, AnnAssign):
                        handleAssign(elem)
                    
                    body += Builder.buildFromNode(elem)
                Builder.setStateKey('__ifBody__', oldIfBody)
                paths.append(f"(else {body})")
                
                
        
        if not rootIf:
            if not Builder.getStateKey('__ifBody__'):
                return SEPERATOR.join(paths)
            else:
                return f"(cond {' '.join(paths)})"
        else:
            Builder.setStateKey('__if__', False)
            
            defs = Builder.getStateKeyLocal('__ifDefinitions__')
            Builder.setStateKey('__ifDefinitions__', [])
            
            return f"{SEPERATOR.join(defs)}{SEPERATOR if len(defs) > 0 else ''}(cond {' '.join(paths)})"
    
    @staticmethod
    def Compare(node: Compare) -> Tuple[str, type]:
        def determineOp(op: str, type1: type, type2: type) -> str:
            if op == "==":
                return "equal?"
            if op == "!=":
                return "!="
            
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
        containingT = Typer.TPending()
        elements = []
        for entry in node.elts:
            value, vType = Builder.buildFromNodeType(entry)
            elements.append(value)
            containingT = Typer.mergeTypes(containingT, vType)

        if not elements:
            return "(gvector)", Typer.TList(containingT)
        
        return f"(gvector {' '.join(elements)})", Typer.TList(containingT)
    
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
                if not Typer.isTypeCompatible((sType := Builder.getStateKeyLocal(name)), aType):
                    raise TypeError(f"Type {sType} and {aType} are incompatible for '{name}'")
                #? Allow automatic conversion between compatible types that dont cause data loss
                Builder.setStateKey(name, aType)
            else:
                #? Unstrict mode
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
        name, nType = Builder.buildFromNodeType(node.value)
        
        class SubscriptResolver():
            @staticmethod
            def error(name: str, nType: type, slice: Any):
                raise TypeError(f"value of type {nType} can not be subscripted")
            
            @staticmethod
            def TList(name: str, nType: type, slice: Union[Index, Slice]) -> Tuple[str, type]:
                if isinstance(slice, Index):
                    index = Builder.buildFromNode(slice)
                    try:
                        index = int(Builder.buildFromNode(slice))
                        
                        if index < 0:
                            index = f"(- (gvector-count r) {-index})"
                        
                    except ValueError:
                        raise TypeError(f"instance of type {type(index)} can not be used to index into a list")
                    
                    return f"(gvector-ref {name} {index})", nType.contained
                elif isinstance(slice, Slice):
                    raise NotImplementedError("Advanced slicing is not yet implemented for lists")
                else:
                    raise TypeError(f"type {type(slice)} can not be used to slice a list")
        
        types: Dict[str, Callable[[Call], Tuple[str, type]]] = {
            Typer.TList: SubscriptResolver.TList
        }
        
        return types.get(type(nType), SubscriptResolver.error)(name, nType, node.slice)
    
    @staticmethod
    def Index(node: Index) -> str:
        if isinstance(node.value, Name) or isinstance(node.value, Constant) or isinstance(node.value, UnaryOp):
            return Builder.buildFromNode(node.value)
        else:
            raise TypeError(f"value of type {type(node.value)} can not be used as an index")
    
    #TODO implement advanced slicing
    # @staticmethod
    # def Slice(node: Slice) -> str:          
    #     pass
    
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
        keyword     : _Builder.keyword
    }
    
    buildFlags = {
        'PRINT'           : False, # Include PRINT function
        'NOT_EQUAL'       : False, # Include != function
        'INPUT'           : False, # Include input function
        'GROWABLE_VECTOR' : False, # Include growableVectors (std)
    }
    
    config = {
        'TYPES_STRICT' : True,
        'DEBUG'        : False
    }
    
    defaultWidenedState = {}
    
    #? For default state see `Builder.initState()`
    stateHistory: List[Dict[str, Any]] = [{}]
    
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
            #? All primitive types are shadowed by their corresponding caster functionTypes!
            # 'bool'  : bool,
            # 'int'   : int,
            # 'float' : float,
            # 'str'   : str,
            # 'list'  : list,
            'print' : Typer.TFunction([Any], kwArgs=[], vararg=True, ret=None), #? This is a dummy that will be transpiled to 'PRINT'
            'PRINT' : Typer.TFunction([Any], kwArgs=[], vararg=True, ret=None),
            'input' : Typer.TFunction([str], kwArgs=[], vararg=False, ret=str),
            'range' : Typer.TFunction([int], kwArgs=[], vararg=True, ret=Typer.TList(int)), #? We set this to vararg as we specifically check this case
            'int'   : Typer.TFunction([Typer.TUnion([float, str, bool])],       kwArgs=[], vararg=False, ret=int),
            'float' : Typer.TFunction([Typer.TUnion([int, str, bool])],         kwArgs=[], vararg=False, ret=float),
            'str'   : Typer.TFunction([Typer.TUnion([int, float, bool, list])], kwArgs=[], vararg=False, ret=str),
            'bool'  : Typer.TFunction([Typer.TUnion([int, float, str, list])],  kwArgs=[], vararg=False, ret=bool)
        }
        Builder.defaultWidenedState = {
            '__if__'              : False, #? Flag for transpiler if in an active if statement
            '__ifBody__'          : False, #? Flag for tramspiler if currently in an if body
            '__ifDefinitions__'   : [],    #? Used to store local definitions to make them persistent on lvl of rootif
            '__assignSkipValue__' : False  #? Flag for transpiler to not include value in assignment
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
            def List(node: Subscript) -> type:
                return Typer.TList(_Typer._literalAnnotation(node.slice.value))
        
        specials: Dict[str, Callable[[Call], type]] = {
            'List': LiteralSubscriptResolver.List,
        }
        
        return specials.get(node.value.id, LiteralSubscriptResolver.error)(node)

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
    
    class TFunction(T):
        type = "TFunction"
        
        def __init__(self, args: List[type], kwArgs: Dict[str, type], vararg: bool, ret: type):
            self.args   = args
            self.kwArgs = kwArgs
            self.vararg = vararg
            self.ret    = ret
    
    class TList(T):
        type = "TList"

        def __init__(self, contained: type):
            self.contained = contained
        
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
        Constant  : _Typer.Constant,
        Name      : _Typer.Name,
        AnnAssign : _Typer.AnnAssign,
        arg       : _Typer.arg
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
        
        raise TypeError(f"can not merge types {type1} and {type2}")
         