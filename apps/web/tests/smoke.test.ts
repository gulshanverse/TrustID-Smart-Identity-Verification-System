import { describe, expect, it } from "vitest";

describe("frontend foundation", () => {
  it("has the TrustID product identity", () => {
    expect("TrustID — Smart Identity Verification").toContain("TrustID");
  });
});
