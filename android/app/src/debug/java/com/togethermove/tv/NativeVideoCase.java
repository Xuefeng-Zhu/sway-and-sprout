package com.togethermove.tv;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/** Exact debug fixture/config names. Never accepts a path or URI supplied by a caller. */
final class NativeVideoCase {
    private static final Set<String> HISTORICAL = new HashSet<>(Arrays.asList(
            "clear", "frontal", "nearface", "right-negative", "both-up-negative",
            "natural-original", "natural-mirror", "left-natural", "right-short",
            "independent-both-press", "independent-both-stretch", "independent-cross-stretch"));
    private static final String SYNTHETIC = "synthetic-throughput";

    private NativeVideoCase() {}

    static String configAsset(String caseName, String model) {
        if (!HISTORICAL.contains(caseName == null ? "" : caseName) && !SYNTHETIC.equals(caseName)) {
            throw new IllegalArgumentException("Unknown native verification fixture");
        }
        if (!("int8".equals(model) || "float16".equals(model) || "thunder".equals(model))) {
            throw new IllegalArgumentException("Unknown native verification model");
        }
        if (SYNTHETIC.equals(caseName) && !"float16".equals(model)) {
            throw new IllegalArgumentException("Synthetic throughput requires float16");
        }
        return "verification/" + caseName + ("int8".equals(model) ? "" : "." + model) + ".json";
    }

    static String modelId(String configAsset) {
        if (configAsset == null || !configAsset.startsWith("verification/") || !configAsset.endsWith(".json")) {
            throw new IllegalArgumentException("config_asset_not_allowed");
        }
        String name = configAsset.substring("verification/".length(), configAsset.length() - ".json".length());
        String model = "int8";
        for (String candidate : new String[]{"float16", "thunder"}) {
            String suffix = "." + candidate;
            if (name.endsWith(suffix)) {
                model = candidate;
                name = name.substring(0, name.length() - suffix.length());
                break;
            }
        }
        try {
            if (!configAsset(name, model).equals(configAsset)) {
                throw new IllegalArgumentException("config_asset_not_allowed");
            }
        } catch (IllegalArgumentException error) {
            throw new IllegalArgumentException("config_asset_not_allowed");
        }
        return model;
    }

    static boolean isSynthetic(String configAsset) {
        modelId(configAsset);
        return "verification/synthetic-throughput.float16.json".equals(configAsset);
    }
}
