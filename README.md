Isle
====

Isle is a scripting language inspired by Ruby, Lua, Python and Déjà Vu.

Requirements
------------

* Python 3.3+
* pyparsing 2.0.3+

Usage
-----

    python3 -m isle yourfile.isl

Tell me about the language
--------------------------

### Datatypes

* `nil`, the only falsy value
* Integers
* Strings: `"like this"`, `"""like this (can have internal newlines"""`,

        <<<identifier
        or like this
        this is a here-doc, starting
        with <<< and an identification string
        and ending in the identification string,
        followed by >>>
        identifier>>>
    They are all different ways of writing the same thing (except here-docs
    doesn't do escaped character or interpolation)
* Functions: `do 42 end`
* Symbols: `:like_this`, `:'or like this'`. The latter way of writing is
  useful if the symbol isn't a valid identifier, like `:'+'`.
* Tables: `("one", "two", three="four", ["five"]="six")`. This is pretty
  much exactly taken from how tables work in Lua. Kind of like a
  combination of Python's list and dict.

### Fun facts
* All functions take one argument, which is a table literal, and return a
  single value, which can be anything. The argument will actually be used as
  the local environment in a function call! `(do puts(value) end)(value=42)`
  prints `42`.
* Tables can override binary and unary operators by having the corresponding
  symbol as a key in themselves: `('+'=do 7 end) + 1 == 7`. You can use any
  of the existing operators, and you can define your own binary operators!
* Any value can be used as a table key, but ints and symbols are special:
  they get their own syntax in table literals (`([1] = :x, [:q] = 7)` is the
  same as `(:x, q = 7)`), and value access (`a[:foo]` is the same as `a.foo`,
  and `a[1]` is the same as `a.$1`, and they are used to access the
  environment: `foo` for the key `:foo` and `$1` for the key `1`.
* Non-positive integer names are special: `$0` is the current function, `$-1`
  is the current environment, `$-2` is the environment of the directly
  enclosing function, `$-3` the environment of the function enclosing that
  one, etc.
* The standard library contains a function called `apply`, which takes a
  function and a table, which will be used as the environment. This can be
  used to simulate classes.
* `'()'` is similar to `__call__` and `__call` in Python and Lua
  respectively.
* String interpolation is really useful: `lie = "I am {myage() - 7} y/o"`.
  No formatting options are available, strings will be inserted as-is and
  other values are inserted equivalent to how they would be show with
  `show()`.
* Supported string escapes are `\\`, `\n`, `\r`, `\t`, `\"` and finally
  `\hexdigits;` for Unicode code points. All other appearances of `\` will
  stripped from the string.
