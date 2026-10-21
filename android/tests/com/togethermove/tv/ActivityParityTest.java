package com.togethermove.tv;

import java.io.BufferedReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Host runner for the shared synthetic landmark CSV. Outputs only policy-event
 * timestamps; it neither loads a pose model nor accesses a camera or decoder.
 */
public final class ActivityParityTest {
    private static final String HEADER = "case,ms,lsX,lsY,lsScore,rsX,rsY,rsScore,lwX,lwY,lwScore,rwX,rwY,rwScore,lhX,lhY,lhScore,rhX,rhY,rhScore";

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("one synthetic CSV path required");
        Map<String, ActivityMachine> machines = new LinkedHashMap<>();
        Map<String, List<Long>> events = new LinkedHashMap<>();
        try (BufferedReader reader = Files.newBufferedReader(Path.of(args[0]), StandardCharsets.UTF_8)) {
            if (!HEADER.equals(reader.readLine())) throw new IllegalArgumentException("unexpected activity CSV header");
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isEmpty()) continue;
                String[] values = line.split(",", -1);
                if (values.length != 20 || !values[0].matches("[a-z0-9-]+"))
                    throw new IllegalArgumentException("invalid synthetic activity row");
                String name = values[0];
                long ms = Long.parseLong(values[1]);
                ActivityMachine machine = machines.computeIfAbsent(name, ignored -> new ActivityMachine());
                List<Long> timestamps = events.computeIfAbsent(name, ignored -> new ArrayList<>());
                PoseGestureMachine.Observation observation = new PoseGestureMachine.Observation(
                        point(values, 2), point(values, 5), point(values, 8), point(values, 11),
                        1.0, point(values, 14), point(values, 17));
                PoseGestureMachine.Event event = machine.update(observation, ms);
                if (event != null) {
                    if (!"activity".equals(event.gesture)) throw new AssertionError("unexpected gesture");
                    timestamps.add(ms);
                }
            }
        }
        for (Map.Entry<String, List<Long>> entry : events.entrySet()) {
            StringBuilder output = new StringBuilder(entry.getKey()).append('|');
            for (int i = 0; i < entry.getValue().size(); i++) {
                if (i > 0) output.append(',');
                output.append(entry.getValue().get(i));
            }
            System.out.println(output);
        }
    }

    private static PoseGestureMachine.Point point(String[] values, int offset) {
        return new PoseGestureMachine.Point(Double.parseDouble(values[offset]),
                Double.parseDouble(values[offset + 1]), Double.parseDouble(values[offset + 2]));
    }
}
