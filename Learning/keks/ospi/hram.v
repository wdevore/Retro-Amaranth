/*
 * HRAM
 * Copyright (c) 2021 Lone Dynamics Corporation. All rights reserved.
 *
 * Verilog module for APSxxxXXN DDR Octal SPI PSRAM.
 *
 * TODO: support X16 mode
 *
 */

module hram (
	input [31:0] addr,
	input [31:0] wdata,
	output reg [31:0] rdata,
	output reg ready,
	input valid,
	input [3:0] wstrb,
	input clk,
	input resetn,
	inout [15:0] adq,
	inout [1:0] dqs,
	output reg ck,
	output reg ce,
	output reg [3:0] state
);

	reg [15:0] adq_oe;
	reg [15:0] adq_do;
	wire [15:0] adq_di;

	reg [1:0] dqs_oe;
	reg [1:0] dqs_do;
	wire [1:0] dqs_di;

	reg [2:0] dqs_c;

	wire write = (wstrb != 0);

`ifdef TESTBENCH

   assign adq = adq_oe ? adq_do : 1'bz;
   assign adq_di = adq;

   assign dqs = dqs_oe ? dqs_do : 1'bz;
   assign dqs_di = dqs;

`else

	SB_IO #(
		.PIN_TYPE(6'b1010_01),
		.PULLUP(1'b0)
	) hram_adq_io [15:0] (
		.PACKAGE_PIN(adq),
		.OUTPUT_ENABLE(adq_oe),
		.D_OUT_0(adq_do),
		.D_IN_0(adq_di)
	);

	SB_IO #(
		.PIN_TYPE(6'b1010_01),
		.PULLUP(1'b0)
	) hram_dqs_io [1:0] (
		.PACKAGE_PIN(dqs),
		.OUTPUT_ENABLE(dqs_oe),
		.D_OUT_0(dqs_do),
		.D_IN_0(dqs_di)
	);

`endif

	localparam [3:0]
		STATE_IDLE			= 4'd0,
		STATE_RESET			= 4'd1,
		STATE_INIT			= 4'd2,
		STATE_START			= 4'd3,
		STATE_CMD			= 4'd4,
		STATE_ADDR			= 4'd5,
		STATE_WAIT			= 4'd6,
		STATE_XFER			= 4'd7,
		STATE_END			= 4'd8,
		STATE_WAIT_DQS_LOW		= 4'd9;

	reg [31:0] buffer;
	reg [5:0] xfer_edges;
	reg [1:0] xfer_ctr;
	reg xfer_rdy;
	reg[1:0] wait_ctr;

	always @(posedge clk) begin

		if (!resetn) begin

			ce <= 1;
			ck <= 0;

			adq_oe = 16'hffff;
			adq_do = 16'h0000;
			dqs_oe = 2'b00;

			xfer_edges <= 0;
			ready <= 0;

			state <= STATE_RESET;

		end else if (valid && !ready && state == STATE_IDLE) begin

			state <= STATE_INIT;
			xfer_edges <= 0;

		end else if (!valid && ready) begin

			ready <= 0;

		end else if (xfer_edges) begin

			if (state == STATE_END) begin
				if (wstrb[3] && xfer_edges == 4) dqs_do <= 2'b00;
				else if (wstrb[2] && xfer_edges == 3) dqs_do <= 2'b00;
				else if (wstrb[1] && xfer_edges == 2) dqs_do <= 2'b00;
				else if (wstrb[0] && xfer_edges == 1) dqs_do <= 2'b00;
				else dqs_do <= 2'b11;
			end

			if (xfer_ctr == 0) begin
				// Write
				adq_do[7:0] <= buffer[31:24];
				buffer <= {buffer, 8'h00};
			end

			if (xfer_ctr == 1) begin

				if (ck) begin
					ck <= 0;
				end else begin
					ck <= 1;
				end

				xfer_edges <= xfer_edges - 1;
				xfer_ctr <= 0;

			end else begin
				xfer_ctr <= xfer_ctr + 1;
			end

		end else case (state)

			STATE_IDLE: begin
				ce <= 1;
			end

			STATE_RESET: begin
				ck <= 0;
				buffer <= 32'hffffffff;
				xfer_edges <= 8;
				xfer_ctr <= 0;
				ce <= 0;
				state <= STATE_IDLE;
			end

			STATE_INIT: begin
				ck <= 0;
				adq_oe = 16'hffff;
				dqs_oe = 2'b00;
				state <= STATE_START;
			end

			STATE_START: begin
				ce <= 0;
				state <= STATE_CMD;
			end

			STATE_CMD: begin
				if (write)
					buffer <= 32'h80000000;
				else
					buffer <= 32'h00000000;
				xfer_edges <= 2;
				xfer_ctr <= 0;
				state <= STATE_ADDR;
			end

			STATE_ADDR: begin
				buffer <= { 6'b0, addr[25:0] };
				xfer_edges <= 4;
				xfer_ctr <= 0;
				if (write) 
					state <= STATE_WAIT;
				else begin
					state <= STATE_WAIT_DQS_LOW;
					wait_ctr <= 0;
				end
				dqs_c <= 0;
				xfer_rdy <= 0;
			end

			STATE_WAIT_DQS_LOW: begin
				if (ck) ck <= 0; else ck <= 1;
				wait_ctr <= wait_ctr + 1;
				if (wait_ctr == 2)
					state <= STATE_WAIT;
			end

			STATE_WAIT: begin
				if (write) begin
					adq_oe <= 16'hffff;
					dqs_oe = 2'b11;
					xfer_edges <= 8;
					state <= STATE_XFER;
				end else begin
					adq_oe <= 16'h0000;
					xfer_edges <= 0;

					if (dqs_di[0] || xfer_rdy) begin

						xfer_rdy <= 1;

						if (xfer_ctr == 0) begin
							buffer <= {buffer, adq_di[7:0]};
							if (dqs_c == 3) state <= STATE_END;
							dqs_c <= dqs_c + 1;	
						end

					end
				
					if (xfer_ctr == 1) begin
						if (ck) ck <= 0; else ck <= 1;
						xfer_ctr <= 0;
					end else begin
						xfer_ctr <= xfer_ctr + 1;
					end
				end
			end

			STATE_XFER: begin
				if (write) begin
					buffer <= wdata;
				end
				xfer_edges <= 4;
				state <= STATE_END;
			end

			STATE_END: begin
				rdata <= buffer;
				ready <= 1;
				state <= STATE_IDLE;
			end

		endcase

	end

endmodule

            // # with m.If(~self.reset):
            // #     # Global reset is 4 clock cycles with CS active 
            // #     m.d.sync += [
            // #         ospi.cs.eq(0),      # Enable chip
            // #         spi_clk.eq(0),      # Start clock low

            // #         # -------------------------------
            // #         # 1 = output buffer driver enabled
            // #         # 0 = buffer output high-Z
            // #         # -------------------------------
            // #         # addr/data OE PIN enabled (driving)
            // #         ospi.adq.oe.eq(0xFFFF),
            // #         # strobe/mask OE PIN disabled (not driving)
            // #         ospi.dqsdm.oe.eq(0b00),

            // #         # Data out zeroes
            // #         ospi.d.o.eq(0x0000),

            // #         xfer_edges.eq(0),       # No edges to count until xfer starts
            // #         self.ready.eq(0),       # Device/Data isn't ready
            // #     ]
            // #     m.next = "RESET"

            // # with m.Elif(self.valid & ~self.ready & fsm.ongoing("IDLE")):
            // #     m.d.sync += xfer_edges.eq(0) # No edges to count
            // #     m.next = "INIT"

            // # with m.Elif(~self.valid & self.ready):
            // #     m.d.sync += self.ready.eq(0) # Data isn't valid yet

            // # with m.Elif(xfer_edges):
            // #     with m.If(fsm.ongoing("END")):
            // #         # Set dqs to 00 only at certain transfer edges.
            // #         with m.If(self.wr_strb[3] & xfer_edges == 4):
            // #             m.d.sync += ospi.dqsdm.o.eq(0b00)
            // #         with m.Elif(self.wr_strb[2] & xfer_edges == 3):
            // #             m.d.sync += ospi.dqsdm.o.eq(0b00)
            // #         with m.Elif(self.wr_strb[1] & xfer_edges == 2):
            // #             m.d.sync += ospi.dqsdm.o.eq(0b00)
            // #         with m.Elif(self.wr_strb[0] & xfer_edges == 1):
            // #             m.d.sync += ospi.dqsdm.o.eq(0b00)
            // #         with m.Else():
            // #             m.d.sync += ospi.dqsdm.o.eq(0b11)

            // #     with m.If(xfer_ctr == 0):
            // #         m.d.sync += [
            // #             # Assign buffer to data output
            // #             ospi.adq.o[0:8].eq(buffer[24:32]),
            // #             buffer.eq(Cat(0x00, buffer)),
            // #         ]

            // #     with m.If(xfer_ctr == 1):
            // #         # Toggle clock
            // #         spi_clk.eq(~spi_clk),

            // #         m.d.sync += [
            // #             # Decrement transfer edge count
            // #             xfer_edges.eq(xfer_edges - 1),
            // #             # Reset transfer count
            // #             xfer_ctr.eq(0),
            // #         ]
                
            // #     with m.Else():
            // #         # Count transfers
            // #         m.d.sync += xfer_ctr.eq(xfer_ctr + 1)
