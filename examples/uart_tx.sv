module baud_tick #(
    parameter int unsigned DIVISOR = 8,
    localparam int unsigned COUNTER_WIDTH = (DIVISOR <= 1) ? 1 : $clog2(DIVISOR)
) (
    input  logic clk_i,
    input  logic rst_ni,
    input  logic enable_i,
    output logic tick_o
);
    localparam logic [COUNTER_WIDTH-1:0] LAST_COUNT =
        COUNTER_WIDTH'(DIVISOR - 1);

    logic [COUNTER_WIDTH-1:0] count_q;

    assign tick_o = enable_i && (count_q == LAST_COUNT);

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            count_q <= '0;
        end else if (!enable_i || tick_o) begin
            count_q <= '0;
        end else begin
            count_q <= count_q + 1'b1;
        end
    end
endmodule


module uart_tx #(
    parameter int unsigned CLOCKS_PER_BIT = 8
) (
    input  logic       clk_i,
    input  logic       rst_ni,
    input  logic [7:0] data_i,
    input  logic       valid_i,
    output logic       ready_o,
    output logic       tx_o,
    output logic       busy_o
);
    typedef enum logic {
        IDLE,
        SEND
    } state_t;

    state_t state_q, state_d;
    logic [9:0] frame_q, frame_d;
    logic [3:0] bit_index_q, bit_index_d;
    logic baud_enable;
    logic baud_tick_o;

    baud_tick #(
        .DIVISOR(CLOCKS_PER_BIT)
    ) baud_tick_i (
        .clk_i,
        .rst_ni,
        .enable_i(baud_enable),
        .tick_o(baud_tick_o)
    );

    always_comb begin
        state_d = state_q;
        frame_d = frame_q;
        bit_index_d = bit_index_q;
        ready_o = 1'b0;
        busy_o = 1'b0;
        tx_o = 1'b1;
        baud_enable = 1'b0;

        case (state_q)
            IDLE: begin
                ready_o = 1'b1;
                if (valid_i) begin
                    frame_d = {1'b1, data_i, 1'b0};
                    bit_index_d = '0;
                    state_d = SEND;
                end
            end

            SEND: begin
                busy_o = 1'b1;
                baud_enable = 1'b1;
                tx_o = frame_q[0];
                if (baud_tick_o) begin
                    if (bit_index_q == 4'd9) begin
                        state_d = IDLE;
                    end else begin
                        frame_d = {1'b1, frame_q[9:1]};
                        bit_index_d = bit_index_q + 1'b1;
                    end
                end
            end

            default: state_d = IDLE;
        endcase
    end

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state_q <= IDLE;
            frame_q <= '1;
            bit_index_q <= '0;
        end else begin
            state_q <= state_d;
            frame_q <= frame_d;
            bit_index_q <= bit_index_d;
        end
    end
endmodule
