
# PySchemeTranspiler

*This transpiler is only working in Python version 3.8.\* due to changes in the AST module from 3.9 onwards*

PYST is a transpiler between python and Scheme(Racket) source code. It tries to mimic the behavior of CPython and makes simple builtin functions available to the user. It works solely with the Python builtin AST module and does not have any dependencies. 

### Work in Progress
There might still be special edge cases not documented that can cause faulty transpilation. If you come across such a case, please submit the code that did not transpile correctly as an issue here on GitHub or email me privately.

#### [Roadmap/Todos](https://github.com/Coronon/PySchemeTranspiler/issues/10)

## Supported features

### Language features
 - Variables
 - Constants
 - Arithmetic
 - Custom Functions
 - Builtins (*print*, *input*, *range*, *len*; Type converters: *int*, *float*, *str*, *bool*)
 - Types: int, float, str, bool, None, List[{Type}] (Indexing + append, pop and insert), Tuple[{Type, ...}]
 - If, elif, else (also nested) (comparators eg. `!=` `==` `>=` and `in` (for List and Tuple) but not `is` or `is not`)
 - MultiAssign swapping (`seq[n - 1], seq[n] = seq[n], seq[n - 1]`)
 - Augmented assignment (`a += 17`)
 - If expressions (`var = a if b else c`)
  - `__name__ == '__main__'` -> will always be true
 - For (also nested)
 - Assert

### Typing system
PYST has a fully fledged typing system and matches types at transpile-time. While most types can dynamically be deduced `lists` still need to be annotated in the standard python way, for example: `myList: List[int] = [1,2,3]`. This restriction is necessary because PYST can not infer a type for an empty list. Type annotations are always checked. To create a pending type you may assign a variable to *None*: `var = None`. This will make the type pending and allow later assigning of a different value. After a type is determined it may not be changed but can be set to None again. None can act as a `nullptr` value as in C++ to create optional returns. The variable which has a type but is set to a value of `None` may still be used like one with a value of its own type, any runtime errors may be avoided by the user (a None check for example: `if var != None:`).

#### Reserved names
To avoid undefined behavior during transpilation, you should avoid reassigning the special names: int, float, str, bool, list, print, input, range, len, deepcopy and \__{anything}__

### Error and warning system
PYST tries to make errors as transparent as possible. If a transpilation error is encountered, a clear message explaining it and the exact place it occurred will be presented to the user. For example the following code will result in a transpilation error:

```python
def willError(arg1: List[int]) -> int:
	return arg1[17]

my_list: List[float] = [1,2,3]

print(willError(my_list))
```

    [TypeError] type <TList: <class 'float'>> can not be applied to argument of type <TList: <class 'int'>>
    6>6:  print(willError(my_list))
                ^
### Caveats
#### Multiple returns
Please ensure all paths in all functions return at least `None` (PYST will implicitly add this return if missing). Multiple return statements in functions must be written so that they are the last executed entity in their function, for example with an if statement:
```python
def testFunc(something: int) -> int:
  if something:
    return something
  else:
    return None # This could also be a plain 'return'
```
Note that the else is mandatory here as the first return would fall through to the `None` return otherwise.
PYST will intentionally fail when an incorrect usage of `return` could lead to unexpected behavior.

## Usage

    usage: pystranspile [-h] [-version] -input INPUT -output OUTPUT
    
    Transpile simple Python to Scheme(Racket).
    
    optional arguments:
      -h, --help      show this help message and exit
      -version        display the current version
      -input INPUT    path to file that should be transpiled
      -output OUTPUT  path to file the transpiled code should be saved in
    
    Copyright (C) 2021 Rubin Raithel
You may abbreviate the above mentioned flags to `-i`, `-o` and `-v`.
PYST is installed as a globally available script and does therefore not require the `python3` prefix but can still be invoked with it by typing `python3 -m pyschemetranspiler`.

## Installation
PYST is currently not available on the PyPi and can therefore only be installed through a local clone of this repo and the command `pip install .` which will make the `pystranspile` command globally available.

## License
PYST is currently licensed under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html) license.

Copyright (C) 2021 Rubin Raithel
