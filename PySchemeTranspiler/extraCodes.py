class extraC():
    PRINT = '(define (PRINT . args) (for-each (lambda (x) (display x) (display " ")) args)(newline))'

    NOT_EQUAL = '(define (!= a b) (not (equal? a b)))'
    
    INPUT = '(define (input prompt) (display prompt)(read-line))'
    
    GROWABLE_VECTOR = """
(require data/gvector)
(define (safe-gvector-set! vec i elm) (if (< i (gvector-count vec)) (gvector-set! vec i elm) (raise "IndexError: list assignment index out of range" #t)))
(define (gvector-pop! vec i) (define ret (gvector-ref r i)) (gvector-remove! vec i)ret)
""".strip()

class FlagRequirements():
    requirements = {
        'PRINT'           : set(),
        'NOT_EQUAL'       : set(),
        'INPUT'           : set(),
        'GROWABLE_VECTOR' : set()
    }

class Arts():
    dancing = r"""  ____   __   __ ____      ____   _   _  U _____ u  __  __   _____    ____        _      _   _    ____     ____              _     U _____ u   ____     
U|  _"\ u\ \ / // __"| uU /"___| |'| |'| \| ___"|/U|' \/ '|u|_ " _|U |  _"\ u U  /"\  u | \ |"|  / __"| uU|  _"\ u  ___     |"|    \| ___"|/U |  _"\ u  
\| |_) |/ \ V /<\___ \/ \| | u  /| |_| |\ |  _|"  \| |\/| |/  | |   \| |_) |/  \/ _ \/ <|  \| |><\___ \/ \| |_) |/ |_"_|  U | | u   |  _|"   \| |_) |/  
 |  __/  U_|"|_uu___) |  | |/__ U|  _  |u | |___   | |  | |  /| |\   |  _ <    / ___ \ U| |\  |u u___) |  |  __/    | |    \| |/__  | |___    |  _ <    
 |_|       |_|  |____/>>  \____| |_| |_|  |_____|  |_|  |_| u |_|U   |_| \_\  /_/   \_\ |_| \_|  |____/>> |_|     U/| |\u   |_____| |_____|   |_| \_\   
 ||>>_ .-,//|(_  )(  (__)_// \\  //   \\  <<   >> <<,-,,-.  _// \\_  //   \\_  \\    >> ||   \\,-.)(  (__)||>>_.-,_|___|_,-.//  \\  <<   >>   //   \\_  
(__)__) \_) (__)(__)    (__)(__)(_") ("_)(__) (__) (./  \.)(__) (__)(__)  (__)(__)  (__)(_")  (_/(__)    (__)__)\_)-' '-(_/(_")("_)(__) (__) (__)  (__)"""