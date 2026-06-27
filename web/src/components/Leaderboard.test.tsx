import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Leaderboard } from "./Leaderboard";

vi.mock("../api", () => ({
  getLeaderboard: vi.fn().mockResolvedValue([
    { rank: 1, name: "Ada", avg: 90, best: 95, games: 3 },
    { rank: 2, name: "Bo", avg: 80, best: 85, games: 2 },
    { rank: 3, name: "Cy", avg: 70, best: 75, games: 1 },
    { rank: 4, name: "Di", avg: 60, best: 65, games: 1 },
  ]),
}));

describe("Leaderboard", () => {
  it("renders players ranked, with gold/silver/bronze medals for the top three", async () => {
    render(<Leaderboard />);

    // names appear once the fetch resolves
    expect(await screen.findByText("Ada")).toBeInTheDocument();
    expect(screen.getByText("Bo")).toBeInTheDocument();

    // medals for ranks 1-3, numeric rank for 4th
    expect(screen.getByText("🥇")).toBeInTheDocument();
    expect(screen.getByText("🥈")).toBeInTheDocument();
    expect(screen.getByText("🥉")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();

    // average score shown
    expect(screen.getByText("90")).toBeInTheDocument();
  });
});
