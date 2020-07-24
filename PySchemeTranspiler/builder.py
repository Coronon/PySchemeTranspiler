from __future__ import annotations
from typing import Dict, List, Tuple, Callable, Any

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
    arg
    )

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
                #Todo: Add type compatibility checker to avoid spreading these all over the code
                if (
                    aType != argT
                    and not (aType == float and argT == int)
                    ):
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
            #! We dont support more than one return at the moment
            if isinstance(i, Return):
                break
        
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
    def Name(node: Name) -> str:
        return node.id, Builder.getStateKey(node.id)
    
    @staticmethod
    def Assign(node: Assign) -> str:
        ret = ""
        for target in node.targets:
            value, vType = Builder.buildFromNodeType(node.value)
            
            if Builder.inStateLocal(target.id):
                if Builder.config['TYPES_STRICT']:
                    #? Strict mode
                    if (sType := Builder.getStateKeyLocal(target.id)) != vType:
                        if not (sType == int and vType == float): 
                            raise TypeError(f"Type {sType} and {vType} are incompatible for '{target.id}'")
                        #? Allow automatic conversion from int->float but NOT float->int (data loss)
                        Builder.setStateKey(target.id, float)
                else:
                    #? Unstrict mode
                    Builder.setStateKey(target.id, vType)
                    
                ret += f"(set! {target.id} {value})"
            else:
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
                    if (
                        argListDef[i][1] != fType.args[i] 
                        and (fType.args[i] != Any and argListDef[i][1] != Any)
                        and not (fType.args[i] == float and argListDef[i][1] == int)):
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
                    if (
                        i[2] != fType.kwArgs[i[0]]
                        and (fType.kwArgs[i[0]] != Any and i[2]  != Any)
                        and not (fType.kwArgs[i[0]] == float and i[2]  == int)):
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
        
        specials: Dict[str, Callable[[Call], Tuple[str, type]]] = {
            'print': CallResolver.print
        }
        
        return specials.get(Builder.buildFromNode(node.func), CallResolver.normal)(node)

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
            if isinstance(elem, Assign):
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
                    if isinstance(elem, Assign):
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
        keyword     : _Builder.keyword
    }
    
    buildFlags = {
        'PRINT'     : False, # Include PRINT function
        'NOT_EQUAL' : False  # Include != function
    }
    
    config = {
        'TYPES_STRICT' : True
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
        ret = Builder.switcher.get(type(node), _Builder.error)(node)
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
        ret = Builder.switcher.get(type(node), _Builder.error)(node)
        if isinstance(ret, tuple):
            return ret
        
        return ret, Typer.Null()
    
    @staticmethod
    def initState() -> None:
        """Init the root state to avoid foreward declaration issues
        """
        defaultRootExclusiveState = {
            'bool' : bool,
            'int'  : int,
            'float': float,
            'str'  : str,
            'list' : list,
            'print': Typer.TFunction([Any], kwArgs=[], vararg=True, ret=None), #? This is a dummy that will be transpiled to 'PRINT'
            'PRINT': Typer.TFunction([Any], kwArgs=[], vararg=True, ret=None)
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
    def error(node: AST):
        raise TypeError(f"Type of node {node} can not be deduced")
    
    
    @staticmethod
    def _literlName(node: str):
        return _Typer.literals.get(node, _Typer.error)
    
    @staticmethod
    def Constant(node: Constant):
        return type(node.value)
    
    @staticmethod
    def Name(node: Name):
        return Builder.getStateKey(node.id)
        
    @staticmethod
    def arg(node: arg):
        return _Typer._literlName(node.annotation.id)


class Typer():
    
    class T():
        def __repr__(self):
            return str(self.__dict__)
    
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
    
    switcher: Dict[type, Callable] = {
        Constant : _Typer.Constant,
        Name     : _Typer.Name,
        arg      : _Typer.arg
    }
    
    @staticmethod
    def deduceTypeFromNode(node: AST):
        return Typer.switcher.get(type(node), _Typer.error)(node)
