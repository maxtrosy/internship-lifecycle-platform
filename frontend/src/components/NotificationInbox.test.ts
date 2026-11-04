import { describe, expect, it } from "vitest";
import { notificationTitle } from "./NotificationInbox";

describe("notification labels", () => {
  it("keeps notification copy factual and category based", () => {
    expect(notificationTitle("PLACEMENT_CLOSED")).toBe("La práctica fue cerrada");
    expect(notificationTitle("EVALUATION_SUBMITTED")).toBe("Se registró una evaluación narrativa");
    expect(notificationTitle("MESSAGE_RECEIVED")).toBe("Hay un nuevo mensaje en una conversación de práctica");
  });
});
