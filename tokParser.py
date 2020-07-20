from __future__ import annotations

from typing import Any, Optional, List, Dict, Tuple, Union
from ply.lex import LexToken
from copy import deepcopy

class Constraint():
    
    def __init__(self,
                 cType:                 str,
                 storage:               Optional[str]=None,
                 uses:                  int=1,
                 requiredUses:          bool=False,
                 inifiniteUses:         bool=False,
                 optaionalRequiredUses: bool=False,
                 multi:                 Optional[Tuple[Constraint]]=None
                 ):
        self.type    = cType
        self.storage = storage
        self.uses    = uses
        self.multi   = multi if multi else False
        
        if multi:
            self.multiPointer  = 0
            self.multiFresh     = True
            self.multiUsed      = False
            self.multiCache     = []
            self.multiCachedRet = None
            self.multiTInvalid  = 0
        
        if (requiredUses and inifiniteUses) or (requiredUses and optaionalRequiredUses) or (inifiniteUses and optaionalRequiredUses):
            raise ValueError("Constraint can only be of one 'Uses' type")
        
        self.requiredUses          = requiredUses
        self.inifiniteUses         = inifiniteUses
        self.optaionalRequiredUses = optaionalRequiredUses
        
        if optaionalRequiredUses:
            self.optCounter = 0
        
        self.backup = deepcopy(self.__dict__)
    
    def reset(self) -> None:
        """Reset to initial state
        """
        self.__dict__ = self.backup
        self.backup   = deepcopy(self.__dict__)
    
    def satisfied(self) -> bool:
        """Check if the constraint is satisfied before moving on to the next one

        Returns:
            bool -- Constraint satisfied
        """
        if self.requiredUses:
            return self.uses == 0
        if self.inifiniteUses:
            return True
        if self.optaionalRequiredUses:
            return (self.optCounter == self.uses or self.optCounter == 0)
    
    def checkToken(self, token: LexToken, ret: Dict) -> Tuple[bool, bool, Dict, List[LexToken]]:
        """Check if token is valid

        Arguments:
            token      {LexToken}       -- Token to check
            ret        {Dict}           -- `parseToDict` storage for recursive constraints

        Returns:
            Tuple[bool, bool, Dict, List[LexToken]] -- Tuple(T->thisConstraint, thisFailAllowed, parseToDictStorage, TsToReInsertIntoIterator)
        """
        if not self.multi:
            ownToken = token.type == self.type
            
            if self.requiredUses:
                if self.uses == 0:
                    return False, True, ret, []
                if ownToken: self.uses -= 1
                
                if ownToken:
                    ret = self.addToStorage(ret, token)
                    
                return ownToken, False, ret, []
            
            if self.inifiniteUses:
                if ownToken:
                    ret = self.addToStorage(ret, token)
                    
                return ownToken, True, ret, []
            
            if self.optaionalRequiredUses:
                if self.optCounter == self.uses:
                    return False, True, ret, []
                if ownToken: 
                    self.optCounter += 1
                    ret = self.addToStorage(ret, token)
                    
                if self.optCounter == 0:
                    return ownToken, True, ret, []
                
                return ownToken, False, ret, []
        
        #*MULTI
        else:
            self.multiTInvalid = 0
            if (self.requiredUses and self.uses == 0) or (self.optaionalRequiredUses and self.optCounter == self.uses):
                return False, True, ret, []
            
            if self.inifiniteUses or (self.optaionalRequiredUses and self.optCounter == 0):
                self.multiCache.append(token)
            
            stack = []
            
            while True:
                if len(stack) > 0:
                    token = stack.pop(0)
                
                if self.inifiniteUses or (self.optaionalRequiredUses and self.optCounter == 0):
                    if self.multiFresh:
                        self.multiCachedRet = deepcopy(ret)
                        
                
                valid, thisFailAllowed, ret, appendix = self.multi[self.multiPointer].checkToken(token, ret)
                self.multiFresh = False
                
                if appendix:
                    stack = appendix

                if not valid:
                    self.multiTInvalid += 1
                    if not thisFailAllowed:
                        if self.requiredUses:
                            if stack:
                                stack.insert(0, token)
                                raise SyntaxError(stack)
                            
                            if self.uses == 0:
                                return False, True, ret, []
                            
                            return False, False, ret, []
                        
                        if self.inifiniteUses:
                            return False, True, self.multiCachedRet, self.multiCache
                        
                        if self.optaionalRequiredUses:
                            if self.optCounter == 0:
                                return False, True, self.multiCachedRet, self.multiCache
                            elif self.optCounter == self.uses:
                                return False, True, ret, []
                            
                            if stack:
                                stack.insert(0, token)
                                raise SyntaxError(stack)
                            
                            return False, False, ret, []
                        
                        raise Exception("SHOULD NEVER TRIGGER!")
                        
                    self.multiPointer += 1
                    
                    if self.multiPointer == len(self.multi):
                        if self.multiTInvalid == len(self.multi):
                            if self.inifiniteUses:
                                return False, True, self.multiCachedRet, self.multiCache
                            if self.optaionalRequiredUses:
                                if self.optCounter == 0:
                                    return False, True, self.multiCachedRet, self.multiCache
                                return False, False, self.multiCachedRet, []
                            if self.requiredUses:
                                if self.uses == 0:
                                    return False, True, self.multiCachedRet, self.multiCache
                                return False, False, self.multiCachedRet, []
                        
                        self.multiPointer = 0
                        self.multiFresh   = True
                        self.multiCache.clear()
                        
                        for c in self.multi:
                            c.reset()
                        
                        if self.requiredUses:
                            self.uses -= 1
                        
                        if self.optaionalRequiredUses:
                            if self.multiUsed == True:
                                self.optCounter += 1
                                self.multiUsed = False
                                
                else:
                    self.multiUsed = True
                    
                    if stack:
                        continue
                    
                    return True, False, ret, []
            
                
    def addToStorage(self, ret: Dict, token: LexToken) -> dict:
        if self.storage is not None:
            if self.storage not in ret:
                ret[self.storage] = []
            ret[self.storage].append(token.value)
        
        return ret
        

def interpretConstraint(constrain: Tuple[Union[str, Tuple], int, Optional[str]]) -> Constraint:
    multi   = isinstance(constrain[0], tuple)
    storage = constrain[2]
    
    requiredUses          = False
    inifiniteUses         = False
    optaionalRequiredUses = False
    uses = constrain[1]
    if uses == 0:
        inifiniteUses = True
    elif uses > 0:
        requiredUses = True
    elif uses < 0:
        optaionalRequiredUses = True
        uses *= -1

    if multi:
        return Constraint("MULTI",
                          storage=storage,
                          uses=uses,
                          requiredUses=requiredUses,
                          inifiniteUses=inifiniteUses,
                          optaionalRequiredUses=optaionalRequiredUses,
                          multi=[interpretConstraint(cons) for cons in constrain[0]]
                          )
    else:
        return Constraint(constrain[0],
                          storage=storage,
                          uses=uses,
                          requiredUses=requiredUses,
                          inifiniteUses=inifiniteUses,
                          optaionalRequiredUses=optaionalRequiredUses,
                          multi=None
                          )

def parseToDict(stack: List[LexToken], parseConstraint: Tuple) -> Dict:
    "def print(a, b, c):"
    ret = {}
    
    constraints = [interpretConstraint(constraint) for constraint in parseConstraint]

    
    constraint = constraints.pop(0)
    tok = stack.pop(0)
    while True:
        valid, thisFailAllowed, ret, appendix = constraint.checkToken(tok, ret)
        
        if appendix:
            stack.insert(0, tok)
            stack = appendix + stack
            tok = stack.pop(0)
            constraint = constraints.pop(0)
            continue
        
        if valid:
            if len(stack) == 0:
                break
            
            tok = stack.pop(0)
            continue  
        else:
            if not thisFailAllowed:
                print("FAILED", ret)
                raise SyntaxError(tok)
            
            if len(constraints) == 0:
                raise SyntaxError(tok)
            
            constraint = constraints.pop(0)
            continue
    
    for c in constraints:
        if not c.satisfied():
            raise SyntaxError(c)
    
    return ret
