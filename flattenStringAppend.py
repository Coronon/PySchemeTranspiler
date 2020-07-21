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

print(flattenSubString('(define (add a b) (define c (string-append (string-append (string-append (string-append (string-append "Hello" " friend") ",") " my") " name is") " Rubin"))(define e "hallo")c)', 'string-append'))