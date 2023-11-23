# *******************************************************************/
# FemtoRV32, a collection of minimalistic RISC-V RV32 cores.
# 
# This version: The "Intermissum", with full interrupt support.
#              A single VERILOG file, compact & understandable code.
# 
# Instruction set: RV32IM + CSR + MRET
# 
# Parameters:
#  Reset address can be defined using RESET_ADDR (default is 0).
# 
# The ADDR_WIDTH parameter lets you define the width of the internal
# address bus (and address computation logic).
# 
# Bruno Levy, Matthias Koch, 2020-2021
# Amaranth port: Will Cleveland
# *******************************************************************/
from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Signal, \
    Module, \
    Array, \
    Cat, C, Const, \
    Repl, \
    Mux, \
    ClockSignal

class Intermission(Elaboratable):

    def __init__(self):
        self.mem_addr  = Signal(32)   # Address
        self.mem_wdata = Signal(32)  # Data to write
        self.mem_wmask = Signal(4)   # Write mask for the each byte of a word Active (high)
        self.mem_rdata = Signal(32)  # Input for both data and instr
        self.mem_rstrb = Signal()    # Active (high) to initiate memory read
        self.mem_rbusy = Signal()    # Active (high) if memory is busy reading value
        self.mem_wbusy = Signal()    # Active (high) if memory is busy writing value
        # self.mem_access = Signal()   # Active (high) for data access

    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        R_ALU_Opcode  = Const(0b0110011)
        I_ALU_Opcode  = Const(0b0010011)
        I_LD_Opcode   = Const(0b0000011)
        S_ST_Opcode   = Const(0b0100011)
        B_BRA_Opcode  = Const(0b1100011)
        J_JAL_Opcode  = Const(0b1101111)
        I_JALR_Opcode = Const(0b1100111)
        U_LUI_Opcode  = Const(0b0110111)
        U_AUI_Opcode  = Const(0b0010111)
        I_SYS_Opcode  = Const(0b1110011)

        # Memory
        mem_rdata = self.mem_rdata

        # Extend a signal with a sign bit repeated n times
        def SignExtend(signal, sign, n):
            return Cat(signal, Repl(sign, n))

        # ***************************************************************************/
        # Instruction decoding.
        # ***************************************************************************/
        # Extracts rd,rs1,rs2,funct3,imm and opcode from instruction.
        # Reference: Table page 104 of:
        # https://content.riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf

        # Current instruction
        instr = Signal(32, reset=R_ALU_Opcode.value)

        # Destination register
        rdId = instr[7:12]

        funct3 = instr[12:15]
        funct7 = instr[25:32]

        # Immediate format decoders
        # The five imm formats, see RiscV reference (link above), Fig. 2.4 p. 12
        # MSBs of S,B,J(imms) not used by addr adder.
        Uimm = Signal(32)
        Iimm = Signal(32)
        Simm = Signal(32)
        Bimm = Signal(32)
        Jimm = Signal(32)
        m.d.comb += [
            # NOTE Between verilog and Amaranth everything is reversed, both
            # Contination and bits. For example, Uimm in verilog is:
            # {    instr[31],   instr[30:12], {12{1'b0}}}
            # But below is reversed and Python is exclusive meaning the
            # higher index is not counted, so to get "31" you specify "32".
            Uimm.eq(Cat(Repl(0, 12), instr[12:32])),
            Iimm.eq(Cat(instr[20:31], Repl(instr[31], 21))),
            Simm.eq(Cat(instr[7:12], instr[25:31], Repl(instr[31], 21))),
            Bimm.eq(Cat(0, instr[8:12], instr[25:31], instr[7], Repl(instr[31], 20))),
            Jimm.eq(Cat(0, instr[21:31], instr[20], instr[12:20], Repl(instr[31], 12)))
        ]

        # Opcode decoder
        # It is nice to have these as actual signals for simulation
        isALUreg = Signal()
        isALUimm = Signal()
        isBranch = Signal()
        isJALR   = Signal()
        isJAL    = Signal()
        isAUIPC  = Signal()
        isLUI    = Signal()
        isLoad   = Signal()
        isStore  = Signal()
        isSystem = Signal()
        isCSR    = Signal()

        isALU  = Signal()
        isLoadStore  = Signal()

        # The ALU function, decoded in 1-hot form (doing so reduces LUT count)
        funct3Is = Signal(8)

        m.d.comb += [
            funct3Is.eq(0b00000001 << funct3),
            isALUreg.eq(instr[0:7] == R_ALU_Opcode.value),
            isALUimm.eq(instr[0:7] == I_ALU_Opcode.value),
            isBranch.eq(instr[0:7] == B_BRA_Opcode.value),
            isJALR.eq(instr[0:7]   == I_JALR_Opcode.value),
            isJAL.eq(instr[0:7]    == J_JAL_Opcode.value),
            isAUIPC.eq(instr[0:7]  == U_AUI_Opcode.value),
            isLUI.eq(instr[0:7]    == U_LUI_Opcode.value),
            isLoad.eq(instr[0:7]   == I_LD_Opcode.value),
            isStore.eq(instr[0:7]  == S_ST_Opcode.value),
            isSystem.eq(instr[0:7] == I_SYS_Opcode.value),
            isCSR.eq(isSystem & (instr[12:15] != 0)),

            isALU.eq(isALUimm | isALUreg),
            isLoadStore.eq(isLoad | isStore)
        ]

        # // @audit !!! mem_access is a weak concept !!!
        # assign mem_access = isLoadStore | state[FETCH_INSTR_bit];         // Is memory data access

        # ***************************************************************************/
        # The register file.
        # ***************************************************************************/
        regs = Array([Signal(32, name="x"+str(x)) for x in range(32)])
        rs1 = Signal(32)
        rs2 = Signal(32)

        # Register addresses decoder
        rs1Id = instr[15:20]
        rs2Id = instr[20:25]

        takeBranch = Signal(32)

        aluIn1 = Signal.like(rs1)   # Mimick the shape of rs1
        aluIn2 = Signal.like(rs2)

        aluMinus = Signal(33)
        aluPlus = Signal.like(aluIn1)


        #***************************************************************************/
        # Program counter and branch target computation.
        #***************************************************************************/
        pc = Signal(32)
        
        # Next program counter is either next intstruction or depends on
        # jump target
        pcPlusImm = pc + Mux(instr[3], Jimm[0:32],
                         Mux(instr[4], Uimm[0:32],
                                       Bimm[0:32]))
        pcPlus4 = pc + 4

        nextPc = Mux(((isBranch & takeBranch) | isJAL), pcPlusImm,
                 Mux(isJALR,                            Cat(C(0, 1), aluPlus[1:32]),
                                                        pcPlus4))

        #***************************************************************************/
        # LOAD/STORE
        #***************************************************************************/
        loadStoreAddr = Signal(32)
        m.d.comb += loadStoreAddr.eq(rs1 + Mux(isStore, Simm, Iimm))

        isByteAccess = Signal()
        isHalfwordAccess = Signal()
        loadHalfword = Signal(16)
        loadByte = Signal(8)
        loadSign = Signal()
        loadData = Signal(32)

        m.d.comb += [
            isByteAccess.eq(funct3[0:2] == C(0,2)),       # 2'b00
            isHalfwordAccess.eq(funct3[0:2] == C(1,2)),   # 2'b01
            
            loadHalfword.eq(Mux(loadStoreAddr[1], mem_rdata[16:32],
                                                  mem_rdata[0:16])),
            loadByte.eq(Mux(loadStoreAddr[0], loadHalfword[8:16],
                                              loadHalfword[0:8])),
            loadSign.eq(~funct3[2] & Mux(isByteAccess, loadByte[7], loadHalfword[15])),
            loadData.eq(Mux(isByteAccess,     SignExtend(loadByte, loadSign, 24),
                        Mux(isHalfwordAccess, SignExtend(loadHalfword, loadSign, 16),
                                              mem_rdata)))
        ]

        # Store
        m.d.comb += [
            self.mem_wdata[ 0: 8].eq(rs2[0:8]),
            self.mem_wdata[ 8:16].eq(
                Mux(loadStoreAddr[0], rs2[0:8], rs2[8:16])),
            self.mem_wdata[16:24].eq(
                Mux(loadStoreAddr[1], rs2[0:8], rs2[16:24])),
            self.mem_wdata[24:32].eq(
                Mux(loadStoreAddr[0], rs2[0:8],
                    Mux(loadStoreAddr[1], rs2[8:16], rs2[24:32])))
        ]

        #***************************************************************************/
        # The ALU
        #***************************************************************************/
        aluOut = Signal(32)
        shamt = Signal(5)

        m.d.comb += [
            aluIn1.eq(rs1),
            aluIn2.eq(Mux((isALUreg | isBranch), rs2, Iimm)),
            shamt.eq(Mux(isALUreg, rs2[0:5], instr[20:25]))
        ]

        m.d.comb += [
            aluMinus.eq(Cat(aluIn1, C(0,1)) - Cat(aluIn2, C(0,1))),
            aluPlus.eq(aluIn1 + aluIn2)
        ]

        EQ = aluMinus[0:32] == 0
        LTU = aluMinus[32]
        LT = Mux((aluIn1[31] ^ aluIn2[31]), aluIn1[31], aluMinus[32])

        # m.d.comb += [
        #     aluOut.eq(Mux(funct3Is[0], Mux(funct7[5] & instr[5], (aluIn1 - aluIn2), aluPlus),
        #               Mux(funct3Is[1], aluIn1 << shamt,
        #               Mux(funct3Is[2], Cat(LT, Repl(0, 31)),    # Signed (a < b)
        #               Mux(funct3Is[3], Cat(LTU, Repl(0, 31)),   # Unsigned (a < b)
        #               Mux(funct3Is[4], aluIn1 ^ aluIn2,
        #               #                                   arithmetic right shift           logical right shift
        #               Mux(funct3Is[5], Mux(funct7[5], (aluIn1.as_signed() >> shamt), (aluIn1.as_unsigned() >> shamt)),
        #               #                                   funct3Is[7]
        #               Mux(funct3Is[6], aluIn1 | aluIn2, aluIn1 & aluIn2))))))))
        # ]

        # NOTE See Amaranth's pmux example that show what appears to be
        #      a one-hot example using "--1" and a switch statement.
        with m.Switch(funct3Is) as alu:
            with m.Case("-------1"):
                m.d.comb += aluOut.eq(Mux(funct7[5] & instr[5], (aluIn1 - aluIn2), aluPlus))
            with m.Case("------1-"):
                m.d.comb += aluOut.eq(aluIn1 << shamt)
            with m.Case("-----1--"):  # Signed (a < b)
                m.d.comb += aluOut.eq(Cat(LT, Repl(0, 31)))
            with m.Case("----1---"):  # Unsigned (a < b)
                m.d.comb += aluOut.eq(Cat(LTU, Repl(0, 31)))
            with m.Case("---1----"):
                m.d.comb += aluOut.eq(aluIn1 ^ aluIn2)
            with m.Case("--1-----"):
                m.d.comb += aluOut.eq(Mux(funct7[5],
                    (aluIn1.as_signed() >> shamt),     # arithmetic right shift
                    (aluIn1.as_unsigned() >> shamt)))  # logical right shift
            with m.Case("-1------"):
                m.d.comb += aluOut.eq(aluIn1 | aluIn2)
            with m.Case("1-------"):
                m.d.comb += aluOut.eq(aluIn1 & aluIn2)

        # with m.Switch(funct3) as alu:
        #     with m.Case(0b000):
        #         m.d.comb += aluOut.eq(Mux(funct7[5] & instr[5], (aluIn1 - aluIn2), aluPlus))
        #     with m.Case(0b001):
        #         m.d.comb += aluOut.eq(aluIn1 << shamt)
        #     with m.Case(0b010): # Signed (a < b)
        #         m.d.comb += aluOut.eq(Cat(LT, Repl(0, 31)))
        #     with m.Case(0b011): # Unsigned (a < b)
        #         m.d.comb += aluOut.eq(Cat(LTU, Repl(0, 31)))
        #     with m.Case(0b100):
        #         m.d.comb += aluOut.eq(aluIn1 ^ aluIn2)
        #     with m.Case(0b101):
        #         m.d.comb += aluOut.eq(Mux(funct7[5],
        #             (aluIn1.as_signed() >> shamt),     # arithmetic right shift
        #             (aluIn1.as_unsigned() >> shamt)))  # logical right shift
        #     with m.Case(0b110):
        #         m.d.comb += aluOut.eq(aluIn1 | aluIn2)
        #     with m.Case(0b111):
        #         m.d.comb += aluOut.eq(aluIn1 & aluIn2)

        # Femto calls this "predicate" for conditional branches
        m.d.comb += [
            takeBranch.eq(Mux(funct3Is[0], EQ,      # BEQ
                          Mux(funct3Is[1], ~EQ,     # BNE
                          Mux(funct3Is[4], LT,      # BLT
                          Mux(funct3Is[5], ~LT,     # BGE
                          Mux(funct3Is[6], LTU,     # BLTU
                          Mux(funct3Is[7], ~LTU,    # BGEU
                          0)))))))
        ]

        with m.Switch(funct3) as alu_branch:
            with m.Case(0b000):
                m.d.comb += takeBranch.eq(EQ)
            with m.Case(0b001):
                m.d.comb += takeBranch.eq(~EQ)
            with m.Case(0b100):
                m.d.comb += takeBranch.eq(LT)
            with m.Case(0b101):
                m.d.comb += takeBranch.eq(~LT)
            with m.Case(0b110):
                m.d.comb += takeBranch.eq(LTU)
            with m.Case(0b111):
                m.d.comb += takeBranch.eq(~LTU)
            with m.Case("---"):
                m.d.comb += takeBranch.eq(0)

        # @audit Main state machine
        with m.FSM(reset="FETCH_INSTR") as fsm:
            self.fsm = fsm
            with m.State("FETCH_INSTR"):
                m.next = "WAIT_INSTR"
            with m.State("WAIT_INSTR"):
                m.d.sync += instr.eq(mem_rdata)
                m.next = ("FETCH_REGS")
            with m.State("FETCH_REGS"):
                m.d.sync += [
                    rs1.eq(regs[rs1Id]),
                    rs2.eq(regs[rs2Id])
                ]
                m.next = "EXECUTE"
            with m.State("EXECUTE"):
                with m.If(~isSystem):
                    m.d.sync += pc.eq(nextPc)
                    
                with m.If(isLoad):
                    m.next = "LOAD"
                with m.Elif(isStore):
                    m.next = "STORE"
                with m.Else():
                    m.next = "FETCH_INSTR"
            with m.State("LOAD"):
                m.next = "WAIT_DATA"
            with m.State("WAIT_DATA"):
                m.next = "FETCH_INSTR"
            with m.State("STORE"):
                m.next = "FETCH_INSTR"

        # Register writeback
        writeBackData = Signal.like(rs1)
        writeBackEn = Signal()
        m.d.comb += [
            writeBackData.eq(Mux(isSystem, 0,        # @audit TODO Add CSR_read
                            Mux(isLUI, Uimm,
                            Mux(isAUIPC, pcPlusImm,
                            Mux((isJAL | isJALR), pcPlus4,
                            Mux(isLoad, loadData, aluOut)))))), # ALUreg, ALUimm
            # NOTE The ~isLoad term that prevents writing to rd during EXECUTE can be
            # removed from the condition, since rd will be overwritten right
            # after during the WAIT_DATA.
            # It is there to have something easier to understand with simulations.
            # ~() & ~isLoad)
            # NOTE I added FETCH_INSTR so that the signal is held past the rising
            # edge of the fetch_instr state. Without it, the Enable signal falls
            # at the rising edge which I think violate hold times
            # NOTE it interfers with the Jal instruction writing to ra register.
            # So it was removed.
            writeBackEn.eq((fsm.ongoing("EXECUTE") & ~(isBranch | isStore))
                        | fsm.ongoing("WAIT_DATA"))
            # writeBackEn.eq(((fsm.ongoing("EXECUTE") | fsm.ongoing("FETCH_INSTR")) & ~(isBranch | isStore))
            #             | fsm.ongoing("WAIT_DATA"))
        ]

        # x0 is always Zero
        with m.If(writeBackEn & (rdId != 0)):
            m.d.sync += regs[rdId].eq(writeBackData)

        store_wmask = Signal(4)
        m.d.comb += store_wmask.eq(
                Mux(isByteAccess,
                    Mux(loadStoreAddr[1],
                        Mux(loadStoreAddr[0], 0b1000, 0b0100),
                        Mux(loadStoreAddr[0], 0b0010, 0b0001)),
                    Mux(isHalfwordAccess,
                        Mux(loadStoreAddr[1], 0b1100, 0b0011),
                        0b1111)
                    )
                )

        m.d.comb += [
            aluMinus.eq(Cat(~aluIn1, C(0,1)) + Cat(aluIn2, C(0,1)) + 1)
        ]

        m.d.comb += [
            self.mem_addr.eq(Mux(fsm.ongoing("WAIT_INSTR") | fsm.ongoing("FETCH_INSTR"), pc,
                             Mux(isLoadStore, loadStoreAddr, 0))),
            self.mem_rstrb.eq(fsm.ongoing("EXECUTE") & isLoad | fsm.ongoing("FETCH_INSTR")),
            # self.mem_wmask.eq(Repl(fsm.ongoing("STORE"), 4) & store_wmask),
            self.mem_wmask.eq(Repl(isStore, 4) & store_wmask),
        ]

        return m

# Unmodified (0)
#    Number of wires:               1275
#    Number of wire bits:           6608
#    Number of public wires:        1275
#    Number of public wire bits:    6608
#    Number of memories:               0
#    Number of memory bits:            0
#    Number of processes:              0
#    Number of cells:               4310
#      SB_CARRY                      212
#      SB_DFF                         41
#      SB_DFFE                        45
#      SB_DFFESR                    1157
#      SB_GB_IO                        1
#      SB_IO                           3
#      SB_LUT4                      2849
#      SB_RAM40_4K                     2

# ---------------------------------------------------
# Modification (1)
# Mofifying alu case 0b000 saved 37 cells
# From:
# m.d.comb += aluOut.eq(Mux(funct7[5] & instr[5], (aluIn1 - aluIn2), (aluIn1 + aluIn2)))
# To:
# m.d.comb += aluOut.eq(Mux(funct7[5] & instr[5], aluMinus[0:32], aluPlus))

#    Number of wires:               1250
#    Number of wire bits:           6492
#    Number of public wires:        1250
#    Number of public wire bits:    6492
#    Number of memories:               0
#    Number of memory bits:            0
#    Number of processes:              0
#    Number of cells:               4273
#      SB_CARRY                      212
#      SB_DFF                         41
#      SB_DFFE                        45
#      SB_DFFESR                    1157
#      SB_GB_IO                        1
#      SB_IO                           3
#      SB_LUT4                      2812
#      SB_RAM40_4K                     2

# ---------------------------------------------------
# Modification (2)
# Mofifying alu case 0b010 and 0b011 saved 154 cells
# From:
# m.d.comb += aluOut.eq(aluIn1.as_signed() < aluIn2.as_signed())
# To:
# m.d.comb += aluOut.eq(Cat(LT, Repl(0, 31)))
# -- And 0b011 --
# From:
# m.d.comb += aluOut.eq(aluIn1 < aluIn2)
# To:
# m.d.comb += aluOut.eq(Cat(LTU, Repl(0, 31)))

#    Number of wires:               1189
#    Number of wire bits:           6161
#    Number of public wires:        1189
#    Number of public wire bits:    6161
#    Number of memories:               0
#    Number of memory bits:            0
#    Number of processes:              0
#    Number of cells:               4119
#      SB_CARRY                      148
#      SB_DFF                         41
#      SB_DFFE                        45
#      SB_DFFESR                    1157
#      SB_GB_IO                        1
#      SB_IO                           3
#      SB_LUT4                      2722
#      SB_RAM40_4K                     2


# ---------------------------------------------------
# Modification (3)
# This modification was to fix a subtract issue. This doesn't
# seem to perform subtract correctly:
# aluMinus.eq(Cat(~aluIn1, C(0,1)) + Cat(aluIn2, C(0,1)) + 1),
# So I switched back to an actual subtract curcuit which resulted
# in an increase of 108 cells:
# aluMinus.eq(Cat(aluIn1, C(0,1)) - Cat(aluIn2, C(0,1))),

#    Number of wires:               1273
#    Number of wire bits:           6538
#    Number of public wires:        1273
#    Number of public wire bits:    6538
#    Number of memories:               0
#    Number of memory bits:            0
#    Number of processes:              0
#    Number of cells:               4227
#      SB_CARRY                      179
#      SB_DFF                         39
#      SB_DFFE                        45
#      SB_DFFESR                    1157
#      SB_GB_IO                        1
#      SB_IO                           3
#      SB_LUT4                      2801
#      SB_RAM40_4K                     2

# ---------------------------------------------------
# Modification (4)
# Replacing Switch(s) with one-hot(s)
# caused a gain of 26 cells Not good!

#    Number of wires:               1282
#    Number of wire bits:           6564
#    Number of public wires:        1282
#    Number of public wire bits:    6564
#    Number of memories:               0
#    Number of memory bits:            0
#    Number of processes:              0
#    Number of cells:               4285
#      SB_CARRY                      179
#      SB_DFF                         40
#      SB_DFFE                        45
#      SB_DFFESR                    1157
#      SB_GB_IO                        1
#      SB_IO                           3
#      SB_LUT4                      2858
#      SB_RAM40_4K                     2
