https://machdyne.com/product/keks-game-console/

https://github.com/machdyne/keks

# Blinky
This is your basic blinky example. It execises the new KeksPlatform board definition file *machdyne_keks.py*.

# Sram
This test Keks' sram chips. There are two 16bit banks that form 32bit word.

There is no module for the SRAM, but you can see how it's accessed by Zucker here:

https://github.com/machdyne/zucker/blob/main/rtl/sysctl_pico.v#L792

and here:

https://github.com/machdyne/zucker/blob/main/rtl/sysctl_pico.v#L1595

# sram_mem_exercise
This runs a basic memory cycle test over a single bank. The Keks has two banks for a total of 512KB or 128K words. You select which bank by uncommenting a RAM_BANK.

# sram_basic_working.py (WORKING)
This is lower level and most simply write/read sequence. It doesn't use combinatorial circuit, just sequencial.

# sram_write_two_addrs.py (WORKING)
This writes to address 0 and 1, then reads them back. It doesn't use combinatorial circuit, just sequencial. WE wasn't being held long enough which was causing succesive write errors.

# sram_write_combinatorial.py (NOT WORKING)
This attempts to use the verilog example approach. It doesn't work at the moment.