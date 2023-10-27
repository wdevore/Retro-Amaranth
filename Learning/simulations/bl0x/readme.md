bl0x's tutorials: https://github.com/bl0x/learn-fpga-amaranth/tree/main

# Python path
Before compiling make sure you run ```source ./pypath.sh``` before running any of the projects

pypath.sh =
```sh
echo Augmenting python path with: $(pwd)
export PYTHONPATH="$(pwd)":$PYTHONPATH
```