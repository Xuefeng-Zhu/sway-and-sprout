package com.togethermove.tv;

public final class ReplayReferenceProfileTest {
    public static void main(String[] args) {
        check(ReplayReferenceProfile.parse(null) == ReplayReferenceProfile.SAMPLED, "default retains reference checks");
        check(ReplayReferenceProfile.parse("sampled") == ReplayReferenceProfile.SAMPLED, "explicit sampled");
        check(ReplayReferenceProfile.parse("off") == ReplayReferenceProfile.OFF, "explicit benchmark off");
        int checks = 0;
        for (int index = 0; index < 136; index++) {
            boolean expected = index < 3 || index % 30 == 0 || index == 135;
            check(ReplayReferenceProfile.SAMPLED.checkFrame(index, 136) == expected, "historical sampling retained");
            check(!ReplayReferenceProfile.OFF.checkFrame(index, 136), "off omits only reference work");
            if (ReplayReferenceProfile.SAMPLED.checkFrame(index, 136)) checks++;
        }
        check(checks == 8, "136-frame sample count");
        int shortChecks = 0;
        for (int index = 0; index < 20; index++) if (ReplayReferenceProfile.SAMPLED.checkFrame(index, 20)) shortChecks++;
        check(shortChecks == 4, "20-frame sample count retained");
        for (String invalid : new String[]{"", "false", "OFF", "none", " off", "off "}) {
            try { ReplayReferenceProfile.parse(invalid); throw new AssertionError("unknown profile accepted"); }
            catch (IllegalArgumentException expected) {}
        }
        for (int[] invalid : new int[][]{{-1,20},{20,20},{0,0}}) {
            try { ReplayReferenceProfile.SAMPLED.checkFrame(invalid[0],invalid[1]); throw new AssertionError("invalid frame accepted"); }
            catch (IllegalArgumentException expected) {}
        }
        System.out.println("ReplayReferenceProfileTest passed");
    }
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
}
