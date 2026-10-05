import { describe, expect, it } from "vitest";
import { nextActions } from "./ticketActions";

const targets = (status: Parameters<typeof nextActions>[0], staff: boolean) =>
  nextActions(status, staff).map((a) => a.to);

describe("nextActions", () => {
  it("lets staff start work on an open ticket, but not requesters", () => {
    expect(targets("open", true)).toEqual(["in_progress"]);
    expect(targets("open", false)).toEqual([]);
  });

  it("lets only staff resolve a ticket that is in progress", () => {
    expect(targets("in_progress", true)).toEqual(["resolved"]);
    expect(targets("in_progress", false)).toEqual([]);
  });

  it("lets everyone close or reopen a resolved ticket", () => {
    expect(targets("resolved", true)).toEqual(["closed", "in_progress"]);
    expect(targets("resolved", false)).toEqual(["closed", "in_progress"]);
  });

  it("offers nothing on a closed ticket", () => {
    expect(targets("closed", true)).toEqual([]);
    expect(targets("closed", false)).toEqual([]);
  });
});
