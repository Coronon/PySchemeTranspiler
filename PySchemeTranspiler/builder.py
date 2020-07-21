from __future__ import annotations
from typing import Dict, List, Tuple, Callable, Any

from copy import deepcopy

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
    arg
    )

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
        argTypes = []
        
        argsLen     = len(node.args.args)
        defaultsLen = len(node.args.defaults)
        for i in range(argsLen):
            if args != "": args += " "
            
            if (default := -(argsLen-defaultsLen-i)) >= 0:
                #? Argument with default
                args += f"#:{node.args.args[i].arg} [{node.args.args[i].arg} {Builder.buildFromNode(node.args.defaults[default])}]"
                
                aType = Typer.deduceTypeFromNode(node.args.args[i])
                argTypes.append(aType)
                Builder.setStateKey(node.args.args[i].arg, aType)
            else:
                #? Normal argument
                args += node.args.args[i].arg
                
                aType = Typer.deduceTypeFromNode(node.args.args[i])
                argTypes.append(aType)
                Builder.setStateKey(node.args.args[i].arg, aType)
        
        #? Check for vararg
        if node.args.vararg is not None:
            args += f" . {node.args.vararg.arg}"
            argTypes.append(list)
        
        #* Add self to state
        retType = Typer.deduceTypeFromNode(node.returns)
        Builder.setStateKey(name, Typer.TFunction(argTypes, retType)) #! ADD to one innter state
        
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
        numberTypes = [int, float]
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
        
        if lType in numberTypes and rType in numberTypes:
            return flattenNumberBinOp(f"({Builder.buildFromNode(node.op)} {lValue} {rValue})"), int if lType == int and rType == int else float
        elif lType == str and rType == str:
            if (operant := Builder.buildFromNode(node.op)) != '+':
                raise TypeError(f"unsupported operand type(s) for {operant}: '{lType}' and '{rType}'")
            return flattenSubString(f"(string-append {lValue} {rValue})", 'string-append'), str
        else:
            raise TypeError(f"unsupported operand type(s) for {operant}: '{lType}' and '{rType}'")
    
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
            
            if Builder.inState(target.id):
                #! Strict mode
                if (sType := Builder.getStateKey(target.id)) != vType:
                    raise TypeError(f"Type {sType} and {vType} are incompatible for '{target.id}'")
                #! Unstrict mode
                # Builder.setStateKey(target.id, vType)
                    
                ret += f"(set! {target.id} {value})"
            else:
                Builder.setStateKey(target.id, vType)
                ret += f"(define {target.id} {value})"
        
        return ret
    

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
        Assign      : _Builder.Assign
    }
    
    buildFlags = {
        'PRINT': False, #Include PRINT function
    }
    
    stateHistory: List[Dict[str, Any]] = [{
        'bool' : bool,
        'int'  : int,
        'str'  : str,
        'list' : list
    }]
    
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
    def getState() -> Dict[str, Any]:
        """Get the current compilation State

        Returns:
            Dict[str, Any] -- State
        """
        return Builder.stateHistory[-1]
    
    @staticmethod
    def getStateKey(key: str) -> Any:
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
        Builder.stateHistory.append(deepcopy(Builder.getState()))
    
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
        pass
    
    class TFunction(T):
        type = "TFunction"
        
        def __init__(self, args: List[type], ret: type):
            self.args = args
            self.ret  = ret
    
    switcher: Dict[type, Callable] = {
        Constant : _Typer.Constant,
        Name     : _Typer.Name,
        arg      : _Typer.arg
    }
    
    @staticmethod
    def deduceTypeFromNode(node: AST):
        return Typer.switcher.get(type(node), _Typer.error)(node)