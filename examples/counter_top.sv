module pulse_divider #(
    parameter int unsigned WIDTH = 4
) (
    input  logic             clk_i,
    input  logic             rst_ni,
    input  logic             enable_i,
    output logic [WIDTH-1:0] count_o,
    output logic             pulse_o
);
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            count_o <= '0;
        end else if (enable_i) begin
            count_o <= count_o + 1'b1;
        end
    end

    assign pulse_o = &count_o;
endmodule

module counter_top (
    input  logic       clk_i,
    input  logic       rst_ni,
    input  logic       run_i,
    output logic [3:0] count_o,
    output logic       active_o
);
    logic terminal_count;

    pulse_divider #(
        .WIDTH(4)
    ) divider_i (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .enable_i(run_i),
        .count_o(count_o),
        .pulse_o(terminal_count)
    );

    assign active_o = run_i & ~terminal_count;
endmodule
