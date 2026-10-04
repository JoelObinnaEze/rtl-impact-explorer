module phase_timer #(
    parameter int unsigned WIDTH = 8
) (
    input  logic             clk_i,
    input  logic             rst_ni,
    input  logic             start_i,
    input  logic             enable_i,
    input  logic [WIDTH-1:0] duration_i,
    output logic             expired_o,
    output logic [WIDTH-1:0] remaining_o
);
    logic [WIDTH-1:0] remaining_q;

    assign remaining_o = remaining_q;
    assign expired_o = enable_i && (remaining_q == '0);

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            remaining_q <= duration_i;
        end else if (start_i) begin
            remaining_q <= duration_i;
        end else if (enable_i && !expired_o) begin
            remaining_q <= remaining_q - 1'b1;
        end
    end
endmodule


module traffic_light_controller #(
    parameter logic [7:0] GREEN_TICKS = 8'd12,
    parameter logic [7:0] YELLOW_TICKS = 8'd3,
    parameter logic [7:0] RED_TICKS = 8'd5,
    parameter logic [7:0] WALK_TICKS = 8'd6
) (
    input  logic       clk_i,
    input  logic       rst_ni,
    input  logic       enable_i,
    input  logic       pedestrian_request_i,
    output logic       red_o,
    output logic       yellow_o,
    output logic       green_o,
    output logic       walk_o,
    output logic [7:0] ticks_remaining_o
);
    typedef enum logic [1:0] {
        GREEN,
        YELLOW,
        RED,
        WALK
    } phase_t;

    phase_t phase_q, phase_d;
    logic pedestrian_pending_q, pedestrian_pending_d;
    logic timer_start;
    logic timer_expired;
    logic [7:0] next_duration;

    phase_timer #(
        .WIDTH(8)
    ) phase_timer_i (
        .clk_i,
        .rst_ni,
        .start_i(timer_start),
        .enable_i,
        .duration_i(next_duration),
        .expired_o(timer_expired),
        .remaining_o(ticks_remaining_o)
    );

    always_comb begin
        phase_d = phase_q;
        pedestrian_pending_d = pedestrian_pending_q | pedestrian_request_i;
        red_o = 1'b0;
        yellow_o = 1'b0;
        green_o = 1'b0;
        walk_o = 1'b0;

        case (phase_q)
            GREEN: begin
                green_o = 1'b1;
                if (timer_expired) phase_d = YELLOW;
            end
            YELLOW: begin
                yellow_o = 1'b1;
                if (timer_expired) phase_d = RED;
            end
            RED: begin
                red_o = 1'b1;
                if (timer_expired) begin
                    phase_d = pedestrian_pending_d ? WALK : GREEN;
                    if (pedestrian_pending_d) pedestrian_pending_d = 1'b0;
                end
            end
            WALK: begin
                red_o = 1'b1;
                walk_o = 1'b1;
                if (timer_expired) phase_d = GREEN;
            end
            default: phase_d = GREEN;
        endcase

        case (phase_d)
            GREEN:   next_duration = GREEN_TICKS;
            YELLOW:  next_duration = YELLOW_TICKS;
            RED:     next_duration = RED_TICKS;
            WALK:    next_duration = WALK_TICKS;
            default: next_duration = GREEN_TICKS;
        endcase

        timer_start = (phase_d != phase_q);
    end

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            phase_q <= GREEN;
            pedestrian_pending_q <= 1'b0;
        end else if (enable_i) begin
            phase_q <= phase_d;
            pedestrian_pending_q <= pedestrian_pending_d;
        end
    end
endmodule
