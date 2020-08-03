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
class extraC():
    PRINT = '(define (PRINT . args) (for-each (lambda (x) (display x) (display " ")) args)(newline))'
    
    EQUAL = '(define (== a b) (if (and (number? a) (number? b)) (= a b) (equal? a b)))'

    NOT_EQUAL = '(define (!= a b) (if (and (number? a) (number? b)) (not (= a b)) (not (equal? a b))))'
    
    INPUT = '(define (input prompt) (display prompt)(read-line))'
    
    GROWABLE_VECTOR = """
(require data/gvector)
(define (safe-gvector-set! vec i elm) (if (< i (gvector-count vec)) (gvector-set! vec i elm) (raise "IndexError: list assignment index out of range" #t)))
(define (gvector-pop! vec i) (define ret (gvector-ref vec i)) (gvector-remove! vec i)ret)
(define (gvector-access vec i) (if (>= i 0) (gvector-ref vec i) (gvector-ref vec (+ (gvector-count vec) i))))
""".strip()

    TO_INT = '(define (int x)(cond ((number? x) (exact-floor x)) ((string? x) (exact-floor (string->number x))) ((boolean? x) (if x 1 0))))'
    
    TO_FLOAT = '(define (float x)(cond ((number? x) (exact->inexact x)) ((string? x) (exact->inexact (string->number x))) ((boolean? x) (if x 1.0 0.0))))'
    
    TO_STR = '(define (str x)(cond ((number? x) (number->string x)) ((string? x) x) ((boolean? x) (if x "True" "False"))))'
    
    TO_BOOL = '(define (bool x)(cond ((number? x) (!= x 0)) ((string? x) (!= x "")) ((boolean? x) x)))'

class FlagRequirements():
    requirements = {
        'PRINT'           : set(),
        'EQUAL'           : set(),
        'NOT_EQUAL'       : set(),
        'INPUT'           : set(),
        'GROWABLE_VECTOR' : set(),
        'TO_INT'          : set(),
        'TO_FLOAT'        : set(),
        'TO_STR'          : set(),
        'TO_BOOL'         : set(['NOT_EQUAL']),
    }

class Arts():
    dancing = r"""  ____   __   __ ____      ____   _   _  U _____ u  __  __   _____    ____        _      _   _    ____     ____              _     U _____ u   ____     
U|  _"\ u\ \ / // __"| uU /"___| |'| |'| \| ___"|/U|' \/ '|u|_ " _|U |  _"\ u U  /"\  u | \ |"|  / __"| uU|  _"\ u  ___     |"|    \| ___"|/U |  _"\ u  
\| |_) |/ \ V /<\___ \/ \| | u  /| |_| |\ |  _|"  \| |\/| |/  | |   \| |_) |/  \/ _ \/ <|  \| |><\___ \/ \| |_) |/ |_"_|  U | | u   |  _|"   \| |_) |/  
 |  __/  U_|"|_uu___) |  | |/__ U|  _  |u | |___   | |  | |  /| |\   |  _ <    / ___ \ U| |\  |u u___) |  |  __/    | |    \| |/__  | |___    |  _ <    
 |_|       |_|  |____/>>  \____| |_| |_|  |_____|  |_|  |_| u |_|U   |_| \_\  /_/   \_\ |_| \_|  |____/>> |_|     U/| |\u   |_____| |_____|   |_| \_\   
 ||>>_ .-,//|(_  )(  (__)_// \\  //   \\  <<   >> <<,-,,-.  _// \\_  //   \\_  \\    >> ||   \\,-.)(  (__)||>>_.-,_|___|_,-.//  \\  <<   >>   //   \\_  
(__)__) \_) (__)(__)    (__)(__)(_") ("_)(__) (__) (./  \.)(__) (__)(__)  (__)(__)  (__)(_")  (_/(__)    (__)__)\_)-' '-(_/(_")("_)(__) (__) (__)  (__)"""
