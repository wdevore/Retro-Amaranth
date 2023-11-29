module sysctl #()
(
   	output SRAM_A0, SRAM_A1, SRAM_A2, SRAM_A3,
		SRAM_A4, SRAM_A5, SRAM_A6, SRAM_A7,
		SRAM_A8, SRAM_A9, SRAM_A10, SRAM_A11,
		SRAM_A12, SRAM_A13, SRAM_A14, SRAM_A15,
		SRAM_A16, SRAM_A17,

	inout SRAM0_D0, SRAM0_D1, SRAM0_D2, SRAM0_D3,
		SRAM0_D4, SRAM0_D5, SRAM0_D6, SRAM0_D7,
		SRAM0_D8, SRAM0_D9, SRAM0_D10, SRAM0_D11,
		SRAM0_D12, SRAM0_D13, SRAM0_D14, SRAM0_D15,

	inout SRAM1_D0, SRAM1_D1, SRAM1_D2, SRAM1_D3,
		SRAM1_D4, SRAM1_D5, SRAM1_D6, SRAM1_D7,
		SRAM1_D8, SRAM1_D9, SRAM1_D10, SRAM1_D11,
		SRAM1_D12, SRAM1_D13, SRAM1_D14, SRAM1_D15,

	output SRAM0_CE, SRAM0_WE, SRAM0_OE, SRAM0_LB, SRAM0_UB,
	output SRAM1_CE, SRAM1_WE, SRAM1_OE, SRAM1_LB, SRAM1_UB,
);

   reg [2:0] sram_state;
   reg sram0_wrlb, sram0_wrub;
   reg sram1_wrlb, sram1_wrub;
   reg [17:0] sram_addr;
   reg [31:0] sram_dout;
   wire [31:0] sram_din;

	wire sram_write = (sram0_wrlb || sram0_wrub || sram1_wrlb || sram1_wrub);

	SB_IO #(
		.PIN_TYPE(6'b 1010_01),
		.PULLUP(1'b 0)
	) sram_io [31:0] (
		.PACKAGE_PIN({ SRAM1_D15, SRAM1_D14, SRAM1_D13, SRAM1_D12, SRAM1_D11,
			SRAM1_D10, SRAM1_D9, SRAM1_D8, SRAM1_D7, SRAM1_D6, SRAM1_D5, SRAM1_D4,
			SRAM1_D3, SRAM1_D2, SRAM1_D1, SRAM1_D0,
			SRAM0_D15, SRAM0_D14, SRAM0_D13, SRAM0_D12, SRAM0_D11,
			SRAM0_D10, SRAM0_D9, SRAM0_D8, SRAM0_D7, SRAM0_D6, SRAM0_D5, SRAM0_D4,
			SRAM0_D3, SRAM0_D2, SRAM0_D1, SRAM0_D0 }),
		.OUTPUT_ENABLE(sram_write),
		.D_OUT_0(sram_dout),
		.D_IN_0(sram_din)
	);

	assign { SRAM_A17, SRAM_A16, SRAM_A15, SRAM_A14, SRAM_A13, SRAM_A12,
		SRAM_A11, SRAM_A10, SRAM_A9, SRAM_A8, SRAM_A7, SRAM_A6, SRAM_A5,
		SRAM_A4, SRAM_A3, SRAM_A2, SRAM_A1, SRAM_A0 } = sram_addr;

	assign SRAM0_CE = 0;
	assign SRAM0_WE = !(sram0_wrlb || sram0_wrub);
	assign SRAM0_OE = sram_write;
	assign SRAM0_LB = (sram0_wrlb || sram0_wrub) ? !sram0_wrlb : 0;
	assign SRAM0_UB = (sram0_wrlb || sram0_wrub) ? !sram0_wrub : 0;

	assign SRAM1_CE = 0;
	assign SRAM1_WE = !(sram1_wrlb || sram1_wrub);
	assign SRAM1_OE = sram_write;
	assign SRAM1_LB = (sram1_wrlb || sram1_wrub) ? !sram1_wrlb : 0;
	assign SRAM1_UB = (sram1_wrlb || sram1_wrub) ? !sram1_wrub : 0;

	always @(posedge clk) begin
		mem_ready <= 0;

		sram0_wrlb <= 0;
		sram0_wrub <= 0;
		sram1_wrlb <= 0;
		sram1_wrub <= 0;

		if (!resetn) begin
			sram_state <= 0;
        end
        else if (mem_valid && !mem_ready) begin
            (* parallel_case *)
            case (1)
                (((mem_addr & 32'hf000_0000) == 32'h2000_0000)): begin
                    if (mem_wstrb) begin
                        if (sram_state == 0) begin
                            sram_addr <= (mem_addr & 32'h0fff_ffff) >> 2;
                            sram_dout <= mem_wdata;
                            sram1_wrub <= mem_wstrb[3];
                            sram1_wrlb <= mem_wstrb[2];
                            sram0_wrub <= mem_wstrb[1];
                            sram0_wrlb <= mem_wstrb[0];
                            sram_state <= 1;
                        end else if (sram_state == 1) begin
                            mem_ready <= 1;
                            sram_state <= 0;
                        end
                    end else begin

                        if (sram_state == 0) begin
                            sram_addr <= (mem_addr & 32'h0fff_ffff) >> 2;
                            sram_state <= 1;
                        end else if (sram_state == 1) begin
                            mem_rdata <= sram_din;
                            mem_ready <= 1;
                            sram_state <= 0;
                        end
                    end
                end
            endcase
        end
    end
endmodule
