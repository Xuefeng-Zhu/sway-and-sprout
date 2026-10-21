package com.togethermove.tv;

/** Config validation only; no Android, decoder, model or media. */
public final class NativeVideoCaseTest {
    private static int assertions;

    public static void main(String[] args) {
        String[] historical = {"clear", "frontal", "nearface", "right-negative", "both-up-negative",
                "natural-original", "natural-mirror", "left-natural", "right-short",
                "independent-both-press", "independent-both-stretch", "independent-cross-stretch"};
        for (String name : historical) for (String model : new String[]{"int8", "float16", "thunder"}) {
            String asset = "verification/" + name + (model.equals("int8") ? "" : "." + model) + ".json";
            check(asset.equals(NativeVideoCase.configAsset(name, model)), "historical config unchanged: " + asset);
            check(model.equals(NativeVideoCase.modelId(asset)), "historical model preserved: " + asset);
            check(!NativeVideoCase.isSynthetic(asset), "historical input never relabeled synthetic");
        }
        String synthetic = "verification/synthetic-throughput.float16.json";
        check(synthetic.equals(NativeVideoCase.configAsset("synthetic-throughput", "float16")), "explicit synthetic config");
        check("float16".equals(NativeVideoCase.modelId(synthetic)), "synthetic model is pinned float16");
        check(NativeVideoCase.isSynthetic(synthetic), "synthetic provenance identified");
        for (String name : new String[]{null, "", "unknown", "../clear", "verification/clear", "clear.json", "file:///clear", "https://example.com/clear"}) {
            rejected(() -> NativeVideoCase.configAsset(name, "int8"), "non-case input rejected");
        }
        for (String model : new String[]{null, "", "INT8", "unknown", "../int8"}) {
            rejected(() -> NativeVideoCase.configAsset("clear", model), "unknown model rejected");
        }
        for (String model : new String[]{"int8", "thunder"}) {
            rejected(() -> NativeVideoCase.configAsset("synthetic-throughput", model), "synthetic cannot select alternate model");
            rejectedConfig(() -> NativeVideoCase.modelId("verification/synthetic-throughput." + model + ".json"), "synthetic alternate config rejected");
        }
        for (String asset : new String[]{null, "", "clear.json", "verification/clear.int8.json", "verification/clear/../clear.json",
                "verification/clear.json/extra", "verification/Clear.json", "verification/clear.json?x=1",
                "verification/clear.json\n", "verification/%63lear.json", "verification/clear\\.json",
                "verification/unknown.json", "verification/synthetic-throughput.json", "file:///verification/clear.json", "https://example.com/verification/clear.json"}) {
            rejectedConfig(() -> NativeVideoCase.modelId(asset), "nonexact config rejected");
            rejectedConfig(() -> NativeVideoCase.isSynthetic(asset), "provenance cannot accept an invalid config");
        }
        System.out.println("NativeVideoCaseTest: " + assertions + " assertions passed (strings only; no media)");
    }

    private static void rejected(Runnable action, String message) {
        boolean rejected = false;
        try { action.run(); } catch (IllegalArgumentException expected) { rejected = true; }
        check(rejected, message);
    }
    private static void rejectedConfig(Runnable action, String message) {
        boolean rejected = false;
        try { action.run(); } catch (IllegalArgumentException expected) {
            rejected = true;
            check("config_asset_not_allowed".equals(expected.getMessage()), "stable config error code");
        }
        check(rejected, message);
    }
    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message);
    }
}
