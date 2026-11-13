import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { failedAttempts, joinNames, parseSourceRun } from "./source-health";

describe("parseSourceRun", () => {
  it("reads board status and ignores record payloads", () => {
    const run = parseSourceRun(
      {
        sources: [
          { source: "remotive", ok: true, error: null, records: [{ id: 1 }] },
          { source: "remoteok", ok: false, error: "TimeoutError: timed out" },
          { source: "arbeitnow", ok: true, error: null },
          { source: "other", ok: false, error: "nope" },
        ],
      },
      "2026-11-12",
    );
    assert.deepEqual(failedAttempts(run!), [
      {
        source: "remoteok",
        name: "Remote OK",
        ok: false,
        error: "TimeoutError: timed out",
      },
    ]);
  });

  it("treats a missing board as failed", () => {
    const run = parseSourceRun(
      {
        sources: [
          { source: "remotive", ok: true, error: null },
          { source: "arbeitnow", ok: false, error: "   HTTPError:  503  " },
        ],
      },
      "2026-11-12",
    );
    const failed = failedAttempts(run!);
    assert.deepEqual(
      failed.map((attempt) => attempt.source),
      ["arbeitnow", "remoteok"],
    );
    assert.equal(failed[0]?.error, "HTTPError: 503");
    assert.equal(failed[1]?.error, null);
  });

  it("returns null for a document that is not a snapshot", () => {
    assert.equal(parseSourceRun({ postings: [] }, "2026-11-12"), null);
    assert.equal(parseSourceRun({ sources: [] }, "2026-11-12"), null);
    assert.equal(parseSourceRun(null, "2026-11-12"), null);
  });

  it("clips a long error", () => {
    const run = parseSourceRun(
      { sources: [{ source: "remotive", ok: false, error: "x".repeat(400) }] },
      "2026-11-12",
    );
    const error = failedAttempts(run!)[0]?.error ?? "";
    assert.equal(error.length, 160);
    assert.equal(error.endsWith("…"), true);
  });
});

describe("joinNames", () => {
  it("joins one, two, and three names", () => {
    assert.equal(joinNames(["Remotive"]), "Remotive");
    assert.equal(joinNames(["Remotive", "Remote OK"]), "Remotive and Remote OK");
    assert.equal(joinNames(["Remotive", "Remote OK", "Arbeitnow"]), "Remotive, Remote OK, and Arbeitnow");
  });
});
