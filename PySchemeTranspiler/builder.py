from __future__ import annotations
from typing import Dict, List, Callable, Any

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
    Assign
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
        
        argsLen     = len(node.args.args)
        defaultsLen = len(node.args.defaults)
        for i in range(argsLen):
            if args != "": args += " "
            
            if (default := -(argsLen-defaultsLen-i)) >= 0:
                #? Argument with default
                args += f"#:{node.args.args[i].arg} [{node.args.args[i].arg} {Builder.buildFromNode(node.args.defaults[default])}]"
            else:
                #? Normal argument
                args += node.args.args[i].arg
        
        #? Check for vararg
        if node.args.vararg is not None:
            args += f" . {node.args.vararg.arg}"
        
        #* Body
        body = ""
        for i in node.body:
            body += Builder.buildFromNode(i)
        
        Builder.popState()
        return f'(define ({name} {args}) {body})'

    @staticmethod
    def Constant(node: Constant) -> str:
        value = node.value
        
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, int):
            return str(value)
        else:
            _Builder.error(node)
    
    @staticmethod
    def Return(node: Return) -> str:
        return Builder.buildFromNode(node.value)
    
    @staticmethod
    def BinOp(node: BinOp) -> str:
        def flattenBinOp(operation: str) -> str:
            ops = ['+', '-', '*', '/']
            for op in ops:
                i = 0
                terminator = len(operation)-1
                while True:
                    i = operation.find(op, i)
                    if i != -1 and operation[i+3] == op:
                        closer = operation.find(')', i)
                        operation = operation[:i-1]+operation[i+2:closer]+operation[closer+1:]
                        terminator = len(operation)-1
                        i = 0
                    else:
                        break
            
            return operation
        
        return flattenBinOp(f"({Builder.buildFromNode(node.op)} {Builder.buildFromNode(node.left)} {Builder.buildFromNode(node.right)})")
    
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
        return node.id
    
    @staticmethod
    def Assign(node: Assign) -> str:
        ret = ""
        for target in node.targets:
            if Builder.inState(target.id):
                ret += f"(set! {target.id} {Builder.buildFromNode(node.value)})"
            else:
                Builder.setStateKey(target.id, 'DEFINED')
                ret += f"(define {target.id} {Builder.buildFromNode(node.value)})"
        
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
        return Builder.switcher.get(type(node), _Builder.error)(node)
    
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