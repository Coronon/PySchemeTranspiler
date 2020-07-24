class extraC():
    PRINT = '(define (PRINT . args) (for-each (lambda (x) (display x) (display " ")) args)(newline))'

    NOT_EQUAL = "(define (!= a b) (not (equal? a b)))"