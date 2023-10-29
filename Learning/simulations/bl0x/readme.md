bl0x's tutorials: https://github.com/bl0x/learn-fpga-amaranth/tree/main

# Python path on Shell
Before compiling make sure you run ```source ./pypath.sh``` before running any of the projects

pypath.sh =
```sh
echo Augmenting python path with: $(pwd)
export PYTHONPATH="$(pwd)":$PYTHONPATH
```

## VSCode
You also add a *.env* file in the same directory are the workspace file, for example, my workspace file is *fpga.code-workspace* and it is located in */media/xxx/Nihongo*. So you create a *.env* there with your **PYTHONPATH** defined:

```
PYTHONPATH="/media/xxx/Nihongo/Hardware/amaranth-boards:/media/xxx/Nihongo/Hardware/Retro-Amaranth/Learning/simulations/bl0x"
```

Describe in: https://code.visualstudio.com/docs/python/environments#_environment-variable-definitions-file

## Makefile
A typical Makefile would be:
```makefile
CODE = bench.py

PYTHON = python

ROOTPATH = /media/iposthuman/Nihongo/Hardware/

# These paths are for building in a shell. VSCode uses .env file to specify paths.
PATHS := ${ROOTPATH}amaranth-boards
PATHS := ${PATHS}:${ROOTPATH}/Retro-Amaranth/Learning/simulations/bl0x

.PHONY: all

# Runs simulation
simulate: ${BENCH}
	@echo "##### Working..."
	@PYTHONPATH=${PATHS} ${PYTHON} ${CODE}
```

# DomainRenamer
https://freenode.irclog.whitequark.org/nmigen/2021-04-21#:~:text=DomainRenamer%20with%20the%20name%20of%20the%20new,the%20module%2C%20usually%20you'd%20pass%20a%20domain

usually though, the preference is to always use sync in a module, and use **DomainRenamer** when you instantiate the module to move it into whichever clock domain you want

typically a module only cares about clock domains besides comb and sync if it's either your top-level module or is doing some clock-domain crossing

so usually you'd just use sync in the module implementation, and use **DomainRenamer** with the name of the new domain when you instantiate it, but if you are doing CDC inside the module, usually you'd pass a domain name string in and the module would use m.d[name] to put statements in the right domain

or example if you look at SyncFIFO in the nmigen lib, it's always in "sync", but you could use **DomainRenamer** to put it somewhere else; however **PulseSynchronizer** has an i_domain and o_domain argument, so you can tell it which domains you're synchronizing between

so definitely "just use sync in generic modules, then rename later"

m = **EnableInserter**({"pclk": self.i_pclk, "nclk": self.i_nclk})(m)

m = **DomainRenamer**({"pclk": "sync", "nclk": "sync"})(m)

and then you use m.d.pclk/m.d.nclk everywhere

the ```DomainRenamer("blah")(SomeElaboratable())``` renames the sync domain of the elaboratable to *blah*

then you can just do ```m.d.comb += ClockSignal("blah").eq(something_else)``` to control the clock signal of the new *blah* domain

all signals in *Amaranth* are plumed to the module reset signal so the whole lot comes up in a known state when you put power to it

---
https://libera.irclog.whitequark.org/amaranth-lang/2022-01-28

you can use a **DomainRenamer** to change a module's clocks around though when you instantiate it

usually i'd just use a named clock domain in my submodule and it's up to the final design to instantiate it correctly, or just use sync and expect the higher level modules to use **DomainRenamer** to do the right thing

generating a /2 clock using a FF is sort of frowned upon, ideally you'd either run the logic half the time (check out **EnableInserter**) or use dedicated FPGA resources to generate a lower freq clock

the FF output might not be glitch free, and generally you don't want to drive downstream FF clocks with data output from another FF, in terms of how the fpga is wired up, aiui

**EnableInserter** is one cute amaranth way to help with that, but you can express it in normal logic too, maybe you can think of it as wrapping the entire submodule's sync logic in "with m.If(enable):" and so if you toggle enable every cycle, the sync logic only runs every other cycle.
**i think a big use case for EnableInserter is using it to wrap a submodule that didn't come with an enable, but you'd like one.**

there's an example in examples/basic/ctr_en.py, literally wrapped with m.If in the mean time, given EnableInserter is afaik undocumented

so, there are two: **EnableInserter** and **ResetInserter** - both work the same fundamental way but on creating a clock enable signal and a submodule-specific reset signal respectively

for example:
```python
m.submodules.pic = pic = ResetInserter(reset)(EnableInserter(busy_n)(PIC16()))
```
reset and busy_n are two otherwise ordinary Signal()s. PIC16() is an **Elaboratable**

**ResetInserter** by default adds a reset for the sync domain
